<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useKlineData } from "./useKlineData"
import { PRESETS, createIndicator } from "./indicators"

/**
 * 独立 K 线图组件
 * - 自身通过 useKlineData 请求并管理 K 线数据（共享 store + 60s 自动刷新）
 * - 叠加指标（MA / BOLL 等）通过 indicators 注册表渲染，新增指标无需改动本组件
 * - dataZoom：固定展示 N 条，支持拖动平移 + 滚轮缩放 + 底部滑条（类似 ECharts）
 * - 悬停十字光标查看 OHLC 与指标数值
 */
const props = defineProps({
    codeId: { type: String, required: true },
  interval: { type: String, default: '15m' },
})

// ==================== K 线数据（自身请求） ====================
// 图表内部自行管理当前级别（可被工具栏切换），props.interval 仅作为初始值
const currentInterval = ref(props.interval || '15m')
const { kline, intervals, loading, loadingEarlier, error, startAutoRefresh, stop, bind, loadEarlier } =
    useKlineData(() => props.codeId, () => currentInterval.value)
bind()

// ==================== 工具栏：级别选择 ====================
// interval 值 -> 中文标签
const INTERVAL_LABELS = {
    '1s': '1秒', '10s': '10秒', '1m': '1分', '5m': '5分', '15m': '15分', '30m': '30分',
    '1h': '1时', '4h': '4时', '8h': '8时', '1d': '1日', '7d': '7日', '30d': '30日',
}
function intervalLabel(v) {
    return INTERVAL_LABELS[v] || v
}

// 常用级别快捷按钮（仅展示后端支持的那些）
const QUICK_INTERVALS = ['1m', '15m', '1h', '4h', '1d']
const quickIntervals = computed(() =>
    QUICK_INTERVALS.filter(v => intervals.value.includes(v))
)

// 「更多」下拉：后端返回的全部级别
const moreOptions = computed(() => intervals.value)
const showMore = ref(false)
const showIndicators = ref(false)

function selectInterval(v) {
    if (v === currentInterval.value) { closePanels(); return }
    currentInterval.value = v
    closePanels()
}
function closePanels() {
    showMore.value = false
    showIndicators.value = false
}
// 点击面板外部时关闭下拉
function onDocClick() {
    closePanels()
}
onMounted(() => {
    document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
    document.removeEventListener('click', onDocClick)
})

// ==================== 指标（独立注册表） ====================
// 用预设的唯一 key 记录勾选状态，保证 MA(5)/MA(10)/MA(20) 可独立开关
function presetKey(p) {
    return p.id + ':' + (p.params?.period ?? '')
}
const activeIds = ref(new Set(['ma:20', 'boll:20']))
const activeIndicators = computed(() =>
    PRESETS.filter(p => activeIds.value.has(presetKey(p))).map(p => createIndicator(p.id, p.params))
)

// 最多同时勾选的指标数量；超过时取消最先勾选的一个
const MAX_INDICATORS = 2

function toggleIndicator(p) {
    const k = presetKey(p)
    const next = new Set(activeIds.value)
    if (next.has(k)) {
        next.delete(k)                       // 取消勾选，不受数量上限限制
    } else {
        next.add(k)                          // 勾选
        if (next.size > MAX_INDICATORS) {    // 超过上限，移除最先勾选的那个（Set 保留插入顺序）
            next.delete(next.values().next().value)
        }
    }
    activeIds.value = next
}
function isActive(p) {
    return activeIds.value.has(presetKey(p))
}

// 当前所有指标展开出的折线（与 kline 等长的 values）
const overlayLines = computed(() => {
    const ks = kline.value
    if (!ks || ks.length === 0) return []
    const lines = []
    activeIndicators.value.forEach(inst => {
        inst.lines(ks).forEach(l => lines.push(l))
    })
    return lines
})

// 顶部指标实时读数：默认取最新值，悬浮时跟随光标所在 K 线
const indicatorReadouts = computed(() => {
    const ks = kline.value
    if (!ks || ks.length === 0) return []
    const idx = (hover.value && hover.value.idx >= 0) ? hover.value.idx : ks.length - 1
    const res = []
    overlayLines.value.forEach(line => {
        const v = line.values?.[idx]
        if (v == null || isNaN(v)) return
        res.push({ name: line.name, color: line.color, value: v })
    })
    return res
})

// ==================== 视口（dataZoom：固定展示 N 条，可拖动/缩放） ====================
const MIN_VISIBLE = 10
const MAX_VISIBLE = 200   // dataZoom 最多同时展示的柱子数
const DEFAULT_VISIBLE = 80

const viewStart = ref(0)              // 视口起始绝对索引
const visibleCount = ref(DEFAULT_VISIBLE) // 当前展示条数

// Y 轴固定刻度：tapActive 拖拽 Scrub 时锁定，首次点击时缓存
const fixedYDomain = ref(null)

function clampView() {
    const len = kline.value.length
    if (len === 0) { viewStart.value = 0; return }
    visibleCount.value = Math.max(MIN_VISIBLE, Math.min(visibleCount.value, len, MAX_VISIBLE))
    viewStart.value = Math.max(0, Math.min(viewStart.value, len - visibleCount.value))
}
function resetView() {
    const len = kline.value.length
    if (len === 0) return
    visibleCount.value = Math.min(DEFAULT_VISIBLE, len)
    viewStart.value = len - visibleCount.value  // 默认展示最新一段
    hoverAbs.value = -1
    tapActive.value = false
    fixedYDomain.value = null
}

// 数据刷新后视口处理策略
let preserveView = false   // 置位时表示本次 kline 变化来自「向前加载」，不回跳最新
let initialized = false    // 首次数据到达
let pendingReset = false   // 级别切换后下次刷新需 reset 到最新
// 级别切换 → 标记下次 kline 变化时回到最新视口
watch(() => currentInterval.value, () => { pendingReset = true })
watch(kline, (newK, oldK) => {
    // 向前加载更早数据：保持用户当前视口（并已在 watch(viewStart) 中平移）
    if (preserveView) { preserveView = false; return }
    const len = newK.length
    // 首次加载 / 级别切换 → 回到最新一段
    if (!initialized || pendingReset) {
        pendingReset = false
        initialized = true
        resetView()
        hoverAbs.value = -1
        tapActive.value = false
        fixedYDomain.value = null
        return
    }
    if (len === 0) { viewStart.value = 0; return }
    // 自动刷新（60s 定时）：保持用户当前视口位置，不回跳
    const oldLen = oldK?.length || 0
    const wasAtTail = (viewStart.value + visibleCount.value) >= oldLen - 1
    visibleCount.value = Math.max(MIN_VISIBLE, Math.min(visibleCount.value, len, MAX_VISIBLE))
    if (wasAtTail) {
        // 原本就贴紧最新尾端 → 跟随最新（贴右）
        viewStart.value = len - visibleCount.value
    } else {
        // 否则保持当前绝对索引（拖到历史位置时不被刷新拉回）
        viewStart.value = Math.max(0, Math.min(viewStart.value, len - visibleCount.value))
    }
})

// 拖到最早（viewStart 到 0）时向前请求更早数据，并平移视口保持视野
const loadingMore = ref(false)
watch(viewStart, async (val) => {
    if (val > 0 || loadingMore.value || loading.value || loadingEarlier.value) return
    if (!kline.value.length) return
    loadingMore.value = true
    const oldLen = kline.value.length
    preserveView = true              // 前置合并不该触发 resetView
    const added = await loadEarlier()
    const newLen = kline.value.length
    if (added > 0 && newLen === oldLen + added) {
        viewStart.value = added      // 原最早一根现在位于 added 处，保持视野
    }
    loadingMore.value = false
})

// 当前可见窗口内的 K 线切片
const visibleKline = computed(() =>
    kline.value.slice(viewStart.value, viewStart.value + visibleCount.value)
)

// ==================== SVG 几何配置 ====================
const chartWidth = 820
const baseChartHeight = 380
const isSmallScreen = ref(false)
const chartHeight = computed(() => isSmallScreen.value ? baseChartHeight * 1.5 : baseChartHeight)
const chartPad = { top: 20, right: 140, bottom: 40, left: 12 }
const fontScale = computed(() => isSmallScreen.value ? 2 : 1)
const yAxisFontSize = computed(() => 10 * fontScale.value)
const yAxisHoverPriceFontSize = computed(() => 8 * fontScale.value)
const yAxisHoverRateFontSize = computed(() => 8 * fontScale.value)
// 右侧悬浮价格气泡尺寸：小屏放大，且宽度限制在右 margin(140) 内不越界、不压柱体
const yAxisHoverW = computed(() => isSmallScreen.value ? 128 : 104)
const yAxisHoverH = computed(() => isSmallScreen.value ? 60 : 40)
const yAxisHoverRx = computed(() => isSmallScreen.value ? 13 : 9)
const yAxisHoverTip = computed(() => isSmallScreen.value ? 10 : 7)
const yAxisHoverPadX = computed(() => isSmallScreen.value ? 16 : 11)
const yAxisHoverPriceY = computed(() => isSmallScreen.value ? 25 : 17)
const yAxisHoverRateY = computed(() => isSmallScreen.value ? 47 : 34)
const tooltipW = computed(() => 168 * fontScale.value)
const tooltipH = computed(() => 158 * fontScale.value)
const tooltipPadX = computed(() => 10 * fontScale.value)
const tooltipTitleY = computed(() => 22 * fontScale.value)
const tooltipRowYs = computed(() => [46, 68, 90, 112, 134].map(y => y * fontScale.value))
const tooltipBadgeX = computed(() => 118 * fontScale.value)
const tooltipTitleFontSize = computed(() => 12 * fontScale.value)
const tooltipRowFontSize = computed(() => 11 * fontScale.value)
const tooltipBadgeFontSize = computed(() => 10 * fontScale.value)

const plotW = computed(() => chartWidth - chartPad.left - chartPad.right)
const plotH = computed(() => chartHeight.value - chartPad.top - chartPad.bottom)

const step = computed(() => plotW.value / visibleCount.value)
// 蜡烛宽度随缩放自适应，避免密集时重叠
const candleW = computed(() => Math.max(1, Math.min(7, step.value * 0.6)))

function xOfRel(j) {
    return chartPad.left + j * step.value + step.value / 2
}

// 参与 Y 轴定标的所有数值：可见窗口内 K 线最高/最低 + 指标值
// tapActive 或 scrubMode 拖拽时使用 fixedYDomain 锁定刻度，避免拖拽中 Y 轴跳动
const yDomain = computed(() => {
    if ((tapActive.value || scrubMode.value) && fixedYDomain.value) {
        return fixedYDomain.value
    }
    const vs = visibleKline.value
    if (!vs.length) return { maxY: 1, minY: 0 }
    let maxH = -Infinity
    let minL = Infinity
    vs.forEach(k => {
        const h = Number(k.h)
        const l = Number(k.l)
        if (!isNaN(h)) maxH = Math.max(maxH, h)
        if (!isNaN(l)) minL = Math.min(minL, l)
    })
    overlayLinesVisible.value.forEach(line => {
        line.values.forEach(v => {
            if (v == null || isNaN(v)) return
            maxH = Math.max(maxH, v)
            minL = Math.min(minL, v)
        })
    })
    if (!isFinite(maxH) || !isFinite(minL)) return { maxY: 1, minY: 0 }
    const range = (maxH - minL) || 1
    const pad = range * 0.05
    return { maxY: maxH + pad, minY: minL - pad }
})

function yOf(v) {
    const { maxY, minY } = yDomain.value
    const totalRange = (maxY - minY) || 1
    return chartPad.top + ((maxY - v) / totalRange) * plotH.value
}

function priceOfY(y) {
    const { maxY, minY } = yDomain.value
    const totalRange = (maxY - minY) || 1
    const clampedY = Math.min(chartHeight.value - chartPad.bottom, Math.max(chartPad.top, y))
    return maxY - ((clampedY - chartPad.top) / plotH.value) * totalRange
}

const candleData = computed(() => {
    const vs = visibleKline.value
    return vs.map((k, j) => {
        const o = Number(k.o)
        const c = Number(k.c)
        const h = Number(k.h)
        const l = Number(k.l)
        const x = xOfRel(j)
        const up = c >= o
        const bodyTop = yOf(Math.max(o, c))
        const bodyH = Math.max(Math.abs(yOf(o) - yOf(c)), 1)
        return {
            x,
            yHigh: yOf(h),
            yLow: yOf(l),
            bodyTop,
            bodyH,
            color: up ? '#2ecc71' : '#e74c3c',
        }
    })
})

const yTicks = computed(() => {
    const { maxY, minY } = yDomain.value
    const totalRange = (maxY - minY) || 1
    const ticks = []
    const count = 5
    for (let i = 0; i <= count; i++) {
        const ratio = i / count
        ticks.push({ v: maxY - ratio * totalRange, y: chartPad.top + ratio * plotH.value })
    }
    return ticks
})

const xTicks = computed(() => {
    const vs = visibleKline.value
    if (!vs.length) return []
    const idxs = []
    if (vs.length === 1) idxs.push(0)
    else idxs.push(0, Math.floor((vs.length - 1) / 2), vs.length - 1)
    return idxs.map(j => {
        const d = new Date(Number(vs[j].t) * 1000)
        const label = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
        return { label, x: xOfRel(j) }
    })
})

// 可见窗口内的指标折线（切片到视口，值与 visibleKline 对齐）
const overlayLinesVisible = computed(() => {
    const vs = visibleKline.value
    if (!vs.length) return []
    const start = viewStart.value
    const end = start + visibleCount.value
    return overlayLines.value.map(line => ({
        ...line,
        values: line.values.slice(start, end),
    }))
})

// 折线路径（自动断开 null 断点；values 已按视口切片，索引 j 为相对坐标）
function linePath(values) {
    if (!values || values.length === 0) return ''
    let d = ''
    let pen = false
    values.forEach((v, j) => {
        if (v == null || isNaN(v)) { pen = false; return }
        const x = xOfRel(j)
        const y = yOf(v)
        d += (pen ? ' L' : ' M') + x.toFixed(2) + ' ' + y.toFixed(2)
        pen = true
    })
    return d
}

// ==================== 平移 / 缩放 / 十字光标 / 点击 / 拖拽Scrub ====================
const hoverAbs = ref(-1)
const tapActive = ref(false)
const scrubMode = ref(false) // 按住 0.5s 后进入自由移动模式
const dragging = ref(false)
const pinching = ref(false)   // 双指捏合缩放进行中
const panning = ref(false)    // 单指拖拽平移进行中
let dragState = null
let lastTapTime = 0

// 拖拽阈值：pointerdown 后移动超过此像素视为拖拽（panning），否则为点击（tap）
const TAP_THRESHOLD = 5

// 多指捏合缩放：追踪活动指针，以两指距离变化映射到视图缩放
const activePointers = new Map()
let pinchPrevDist = 0
let pinchAnchorAbs = 0      // 双指中点对应的连续绝对索引（缩放锚点）
let pinchAnchorRatio = 0    // 锚点在视口中的连续比例位置

// 客户端坐标 → 连续绝对索引（带小数），用于平滑缩放锚点
function clientToAbsIndex(clientX, clientY, rect) {
    const ratio = ((clientX - rect.left) / rect.width) * chartWidth
    const rel = (ratio - chartPad.left) / step.value
    return viewStart.value + rel
}

// 以锚点为中心按 ratio 缩放（ratio>1 表示放大→显示更少根数）
function zoomByRatio(ratio, anchorAbs, anchorRatio) {
    const len = kline.value.length
    if (!len || ratio <= 0) return
    const oldCount = visibleCount.value
    let newCount = Math.round(oldCount / ratio)
    newCount = Math.max(MIN_VISIBLE, Math.min(newCount, len, MAX_VISIBLE))
    let newStart = anchorAbs - anchorRatio * newCount
    newStart = Math.max(0, Math.min(newStart, len - newCount))
    visibleCount.value = newCount
    viewStart.value = Math.round(newStart)
}
// 按住时长：超过此值进入 Scrub 模式（自由移动，锁定视口和 Y 轴）
const SCRUB_HOLD_MS = 500
let pointerStartClientX = 0
let pointerStartClientY = 0
let pointerMoved = false
let scrubTimer = null
// 拖拽/长按结束后会派发 click 事件，用此标志吞掉它，避免误选中蜡烛
let suppressNextClick = false
// 长按进度（0 → 1），用于显示环形进度指示器
const holdProgress = ref(0)
let holdStartTime = 0
// 长按指针在 SVG 坐标中的位置（用于进度环定位）
const holdPointerX = ref(-1)
const holdPointerY = ref(-1)
const hoverPointerX = ref(-1)
const hoverPointerY = ref(-1)

function pxToRelIndex(px, rect) {
    const ratio = (px / rect.width) * chartWidth
    return Math.round((ratio - chartPad.left - step.value / 2) / step.value)
}

function clearScrubTimer() {
    if (scrubTimer) {
        clearTimeout(scrubTimer)
        scrubTimer = null
    }
}

// 更新长按进度（供 pointermove 调用）
function updateHoldProgress() {
    const elapsed = Date.now() - holdStartTime
    holdProgress.value = Math.min(1, elapsed / SCRUB_HOLD_MS)
}

function updateHoverFromPointer(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return
    const svgX = ((e.clientX - rect.left) / rect.width) * chartWidth
    const svgY = ((e.clientY - rect.top) / rect.height) * chartHeight.value
    hoverPointerX.value = svgX
    hoverPointerY.value = svgY
    const j = pxToRelIndex(e.clientX - rect.left, rect)
    const abs = viewStart.value + j
    hoverAbs.value = (abs >= 0 && abs < kline.value.length) ? abs : -1
}

function onPointerDown(e) {
    activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
    // 双指（及以上）→ 进入捏合缩放，暂停单指平移/Scrub
    if (activePointers.size >= 2) {
        clearScrubTimer()
        scrubMode.value = false
        dragging.value = false
        dragState = null
        pinching.value = true
        panning.value = false
        // 清除残留的跟随十字光标/tooltip
        hoverAbs.value = -1
        hoverPointerX.value = -1
        hoverPointerY.value = -1
        const pts = [...activePointers.values()]
        const dx = pts[0].x - pts[1].x
        const dy = pts[0].y - pts[1].y
        pinchPrevDist = Math.hypot(dx, dy) || 1
        const cx = (pts[0].x + pts[1].x) / 2
        const cy = (pts[0].y + pts[1].y) / 2
        const rect = e.currentTarget.getBoundingClientRect()
        pinchAnchorAbs = clientToAbsIndex(cx, cy, rect)
        pinchAnchorRatio = (pinchAnchorAbs - viewStart.value) / visibleCount.value
        return
    }
    // 多指场景（双指缩放）：放弃单指平移，交还给浏览器处理 pinch-zoom
    if (!e.isPrimary || dragging.value) {
        onPointerUp(e)
        return
    }
    pointerStartClientX = e.clientX
    pointerStartClientY = e.clientY
    pointerMoved = false
    suppressNextClick = false
    scrubMode.value = false
    pinching.value = false
    panning.value = false
    holdProgress.value = 0
    holdStartTime = Date.now()
    dragging.value = true
    dragState = {
        startClientX: e.clientX,
        startViewStart: viewStart.value,
    }
    // 按住 0.5s 后进入 Scrub 模式（自由移动，锁定视口和 Y 轴）
    scrubTimer = setTimeout(() => {
        scrubMode.value = true
        suppressNextClick = true
        holdProgress.value = 1
        // 进入 Scrub 模式时锁定 Y 轴为当前可见范围
        fixedYDomain.value = yDomain.value
    }, SCRUB_HOLD_MS)
    e.currentTarget.setPointerCapture?.(e.pointerId)
}
function onPointerMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    if (activePointers.has(e.pointerId)) {
        activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
    }
    // 双指捏合缩放：以两指距离变化为缩放比，保持中点锚点位置不动
    if (activePointers.size >= 2) {
        const pts = [...activePointers.values()]
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) || 1
        if (pinchPrevDist > 0) {
            zoomByRatio(dist / pinchPrevDist, pinchAnchorAbs, pinchAnchorRatio)
        }
        pinchPrevDist = dist
        return
    }
    if (!dragging.value || !dragState) {
        updateHoverFromPointer(e)
        return
    }

    const dxPx = Math.abs(e.clientX - pointerStartClientX)
    const dyPx = Math.abs(e.clientY - pointerStartClientY)

    // 首次超过阈值 → 判定为拖拽（panning），取消 Scrub 计时器
    if (!pointerMoved && (dxPx > TAP_THRESHOLD || dyPx > TAP_THRESHOLD)) {
        pointerMoved = true
        panning.value = true
        suppressNextClick = true
        clearScrubTimer()
        holdProgress.value = 0
    }

    // 更新长按进度（在 Scrub 判定前）
    if (!scrubMode.value && !pointerMoved) {
        updateHoldProgress()
        // 追踪指针在 SVG 坐标中的位置（用于进度环定位）
        holdPointerX.value = ((e.clientX - rect.left) / rect.width) * chartWidth
        holdPointerY.value = ((e.clientY - rect.top) / rect.height) * chartHeight.value
    }

    if (scrubMode.value) {
        // Scrub 模式：跟随手指/鼠标移动展示数据（锁定视口与 Y 轴），显示 tooltip
        updateHoverFromPointer(e)
        return
    }

    if (pointerMoved) {
        // 普通拖拽平移 → 隐藏跟随十字光标/tooltip，避免拖动时 tooltip 闪现
        hoverAbs.value = -1
        hoverPointerX.value = -1
        hoverPointerY.value = -1
        const stepPx = (rect.width / chartWidth) * step.value
        const dBars = Math.round((e.clientX - dragState.startClientX) / stepPx)
        viewStart.value = dragState.startViewStart - dBars
        clampView()
        return
    }

    // 非 Scrub 模式且未移动 → 不更新 hoverAbs（等待点击或 Scrub 判定）
}
function onPointerUp(e) {
    if (e && e.pointerId != null) activePointers.delete(e.pointerId)
    // 仍有双指 → 继续捏合，不清理
    if (activePointers.size >= 2) return
    // 退回单指：重置拖拽状态，剩余手指可作为单指平移/Scrub 重新识别
    if (activePointers.size === 1) {
        pinchPrevDist = 0
        dragging.value = false
        dragState = null
        pointerMoved = false
        return
    }
    // 无活动指针：完整清理
    clearScrubTimer()
    // 退出 Scrub 模式时，若没有 tap 选中则解锁 Y 轴
    if (scrubMode.value && !tapActive.value) {
        fixedYDomain.value = null
    }
    scrubMode.value = false
    dragging.value = false
    dragState = null
    pointerMoved = false
    holdProgress.value = 0
    holdPointerX.value = -1
    holdPointerY.value = -1
    pinchPrevDist = 0
    pinching.value = false
    panning.value = false
}
function onPointerLeave(e) {
    if (e && e.pointerId != null) activePointers.delete(e.pointerId)
    // 仍有双指（另一指在区域内）→ 继续捏合，不清理
    if (activePointers.size >= 2) return
    clearScrubTimer()
    // 退出 Scrub 模式时，若没有 tap 选中则解锁 Y 轴
    if (scrubMode.value && !tapActive.value) {
        fixedYDomain.value = null
    }
    scrubMode.value = false
    if (!tapActive.value) {
        hoverAbs.value = -1
        hoverPointerX.value = -1
        hoverPointerY.value = -1
    }
    dragging.value = false
    dragState = null
    pointerMoved = false
    holdProgress.value = 0
    holdPointerX.value = -1
    holdPointerY.value = -1
    pinchPrevDist = 0
    pinching.value = false
    panning.value = false
}

// 点击蜡烛 → 选中并持久显示数据（移动端核心交互）
function onChartClick(e) {
    // 刚经历过拖拽/长按 Scrub，吞掉这次 click，避免误选中
    if (suppressNextClick) {
        suppressNextClick = false
        return
    }
    const rect = e.currentTarget.getBoundingClientRect()
    if (rect.width === 0) return
    const j = pxToRelIndex(e.clientX - rect.left, rect)
    if (isNaN(j)) return
    const abs = viewStart.value + j
    if (abs < 0 || abs >= kline.value.length) {
        // 点击空白区域 → 取消选中
        tapActive.value = false
        hoverAbs.value = -1
        hoverPointerX.value = -1
        hoverPointerY.value = -1
        fixedYDomain.value = null
        return
    }
    // 快速连续点击同一根蜡烛 → 取消选中
    const now = Date.now()
    if (tapActive.value && hoverAbs.value === abs && now - lastTapTime < 400) {
        tapActive.value = false
        hoverAbs.value = -1
        hoverPointerX.value = -1
        hoverPointerY.value = -1
        fixedYDomain.value = null
        return
    }
    lastTapTime = now
    hoverAbs.value = abs
    tapActive.value = true
    // 缓存当前 Y 轴刻度，拖拽 Scrub 时锁定
    fixedYDomain.value = yDomain.value
}

// 滚轮缩放（以光标位置为锚点，保持光标下的蜡烛不动）
function onWheel(e) {
    const len = kline.value.length
    if (!len) return
    e.preventDefault()
    const rect = e.currentTarget.getBoundingClientRect()
    const anchorAbs = clientToAbsIndex(e.clientX, e.clientY, rect)
    const oldCount = visibleCount.value
    const oldStart = viewStart.value
    const factor = e.deltaY > 0 ? 1.12 : 1 / 1.12   // >1 放大（显示更少根数）
    let newCount = Math.max(MIN_VISIBLE, Math.min(Math.round(oldCount * factor), len, MAX_VISIBLE))
    // 锚点在视口中的比例位置保持不变
    let newStart = anchorAbs - ((anchorAbs - oldStart) / oldCount) * newCount
    newStart = Math.max(0, Math.min(newStart, len - newCount))
    visibleCount.value = newCount
    viewStart.value = Math.round(newStart)
}

// 底部 dataZoom 滑条
const sliderLeftPct = computed(() =>
    kline.value.length ? (viewStart.value / kline.value.length) * 100 : 0
)
const sliderWidthPct = computed(() =>
    kline.value.length ? (visibleCount.value / kline.value.length) * 100 : 100
)
// 滑条拖拽专用：仅标记 dragging，不启动 Scrub 长按、不混入图表指针表，
// 避免快速拖动时误入 Scrub 锁定 Y 轴（导致 Y 轴不实时更新）
function onSliderDown(e) {
    dragging.value = true
    e.currentTarget.setPointerCapture?.(e.pointerId)
}
function onSliderUp() {
    dragging.value = false
}
function sliderMove(e) {
    if (!dragging.value) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    const center = ratio * kline.value.length
    viewStart.value = Math.round(center - visibleCount.value / 2)
    clampView()
}

const hover = computed(() => {
    // 双指捏合缩放 / 单指拖拽平移进行中 → 隐藏跟随十字光标与 tooltip，避免干扰
    // 长按 Scrub 模式（按住 0.5s 后拖动看数据）仍正常显示 tooltip，需排除 panning
    if (pinching.value || (panning.value && !scrubMode.value)) return null
    const abs = hoverAbs.value
    const ks = kline.value
    if (abs < 0 || !ks || !ks[abs]) return null
    const k = ks[abs]
    const j = abs - viewStart.value
    const pointerX = Number.isFinite(hoverPointerX.value) ? hoverPointerX.value : xOfRel(j)
    const pointerY = Number.isFinite(hoverPointerY.value) ? hoverPointerY.value : chartPad.top
    const y = Math.min(chartHeight.value - chartPad.bottom, Math.max(chartPad.top, pointerY))
    const yAxisPrice = priceOfY(y)
    const closePrice = Number(k.c)
    // 最新价（全局最后一根收盘价），作为实时涨跌幅的基准
    const latestClose = Number(ks[ks.length - 1]?.c) || 0
    // 涨跌幅 = 鼠标 Y 轴价格 相对 最新价 的涨跌百分比
    const priceDiffRate = latestClose ? ((yAxisPrice - latestClose) / latestClose) * 100 : 0
    const tooltipMargin = 10
    const plotMidX = chartPad.left + plotW.value / 2
    const currentTooltipW = tooltipW.value
    const tooltipX = pointerX <= plotMidX
        ? chartWidth - chartPad.right - currentTooltipW - tooltipMargin
        : chartPad.left + tooltipMargin
    const tooltipY = chartPad.top + tooltipMargin
    const out = {
        idx: abs,
        x: xOfRel(j),
        y,
        yAxisLabelY: Math.min(chartHeight.value - chartPad.bottom - 10, Math.max(chartPad.top + 10, y)),
        tooltipX,
        tooltipY,
        currentPrice: yAxisPrice,
        priceDiffRate,
        priceDiffUp: priceDiffRate >= 0,
        t: ks[abs].t,
        o: Number(k.o), c: closePrice, h: Number(k.h), l: Number(k.l),
        indicators: [],
    }
    overlayLines.value.forEach(line => {
        const v = line.values[abs]
        if (v == null || isNaN(v)) return
        out.indicators.push({ name: line.name, color: line.color, value: v })
    })
    return out
})

// ==================== 格式化 ====================
function formatPrice(v) {
    if (v == null || isNaN(v)) return '-'
    v = Number(v)
    if (v >= 1) return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (v === 0) return '$0.00'
    // 0 < v < 1：按数量级动态展开小数（不使用科学计数法，避免被舍成 0）
    const decimals = Math.min(20, Math.max(2, Math.ceil(-Math.log10(v)) + 2))
    return '$' + v.toFixed(decimals)
}
function formatPercent(v) {
    if (v == null || isNaN(v)) return '-'
    const sign = v > 0 ? '+' : ''
    return sign + Number(v).toFixed(2) + '%'
}
function formatTime(t) {
    const d = new Date(Number(t) * 1000)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function updateSmallScreen() {
    isSmallScreen.value = window.matchMedia('(max-width: 768px)').matches
}

// ==================== 生命周期 ====================
onMounted(() => {
    updateSmallScreen()
    window.addEventListener('resize', updateSmallScreen)
    startAutoRefresh()
})
onUnmounted(() => {
    window.removeEventListener('resize', updateSmallScreen)
    stop()
})
</script>

<template>
    <div class="chart-card">
        <div class="chart-head">
            <!-- 工具栏：级别分段控件 + 更多面板 + 指标面板 -->
            <div class="toolbar">
                <!-- 快捷级别：连在一起的分段控件，点击高亮 -->
                <div class="seg">
                    <span
                        v-for="v in quickIntervals"
                        :key="'q-' + v"
                        class="seg-item"
                        :class="{ active: currentInterval === v }"
                        @click="selectInterval(v)"
                    >
                        {{ intervalLabel(v) }}
                    </span>
                </div>

                <!-- 更多：图标(＋)面板展示全部级别 -->
                <div class="tool-drop" @click.stop>
                    <button class="icon-btn" :class="{ active: showMore }" @click="showMore = !showMore; showIndicators = false" title="更多级别">
                        <svg viewBox="0 0 16 16" width="13" height="13"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>
                    </button>
                    <transition name="fade">
                        <div v-if="showMore" class="drop-panel drop-grid">
                            <button
                                v-for="v in moreOptions"
                                :key="'m-' + v"
                                class="drop-item"
                                :class="{ active: currentInterval === v }"
                                @click="selectInterval(v)"
                            >
                                {{ intervalLabel(v) }}
                            </button>
                        </div>
                    </transition>
                </div>

                <!-- 指标：图标(折线)面板展示指标勾选项 -->
                <div class="tool-drop" @click.stop>
                    <button class="icon-btn" :class="{ active: showIndicators }" @click="showIndicators = !showIndicators; showMore = false" title="指标">
                        <svg viewBox="0 0 16 16" width="13" height="13"><polyline points="2,12 6,6 9,9 14,3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 14h12" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
                    </button>
                    <transition name="fade">
                        <div v-if="showIndicators" class="drop-panel">
                            <label
                                v-for="p in PRESETS"
                                :key="presetKey(p)"
                                class="drop-item drop-check"
                            >
                                <input type="checkbox" :checked="isActive(p)" @change="toggleIndicator(p)" />
                                <span class="check-color" :style="{ background: p.id === 'ma' ? '#f1c40f' : '#9b59b6' }"></span>
                                {{ p.label }}
                            </label>
                        </div>
                    </transition>
                </div>
            </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading && kline.length === 0" class="chart-state">
            <div class="spinner"></div>
            <span>加载 K 线数据中...</span>
        </div>

        <!-- 错误 -->
        <div v-else-if="error && kline.length === 0" class="chart-state">
            <span>{{ error }}</span>
        </div>

        <!-- 空数据 -->
        <div v-else-if="kline.length === 0" class="chart-state">
            <span>暂无 K 线数据</span>
        </div>

        <!-- SVG 蜡烛图 + 指标叠加 -->
        <svg v-else
            :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
            class="candle-chart"
            :class="{ dragging }"
            preserveAspectRatio="xMidYMid meet"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointerleave="onPointerLeave"
            @pointercancel="onPointerLeave"
            @wheel="onWheel"
            @click="onChartClick"
        >
            <rect class="chart-hit-area" x="0" y="0" :width="chartWidth" :height="chartHeight" />

            <!-- 顶部指标实时读数（悬浮时跟随光标，否则显示最新值） -->
            <g class="indicator-bar">
                <text :x="chartPad.left + 4" :y="chartPad.top - 6" class="indicator-readout">
                    <tspan v-for="(r, i) in indicatorReadouts" :key="'ib-' + i"
                        :fill="r.color" :dx="i === 0 ? 0 : 13">{{ r.name }}: {{ formatPrice(r.value) }}</tspan>
                </text>
            </g>

            <!-- 网格线 + Y 轴价格刻度（最右侧） -->
            <g v-for="t in yTicks" :key="'y' + t.v">
                <line :x1="chartPad.left" :y1="t.y" :x2="chartWidth - chartPad.right" :y2="t.y"
                    stroke="rgba(30,58,95,0.5)" stroke-width="1" />
                <text :x="chartWidth - chartPad.right + 8" :y="t.y + 4" text-anchor="start" class="axis-text" :style="{ fontSize: yAxisFontSize + 'px' }">
                    {{ formatPrice(t.v) }}
                </text>
            </g>

            <!-- X 轴时间刻度 -->
            <g v-for="(t, i) in xTicks" :key="'x' + i">
                <line :x1="t.x" :y1="chartPad.top" :x2="t.x" :y2="chartHeight - chartPad.bottom"
                    stroke="rgba(30,58,95,0.3)" stroke-width="1" stroke-dasharray="2 3" />
                <text :x="t.x" :y="chartHeight - chartPad.bottom + 18" text-anchor="middle" class="axis-text">
                    {{ t.label }}
                </text>
            </g>

            <!-- 指标叠加折线（视口切片） -->
            <path
                v-for="(line, li) in overlayLinesVisible"
                :key="'ind-' + li + '-' + line.name"
                :d="linePath(line.values)"
                :stroke="line.color"
                stroke-width="1.4"
                fill="none"
            />

            <!-- 蜡烛 -->
            <g v-for="(c, i) in candleData" :key="'c' + i">
                <line :x1="c.x" :y1="c.yHigh" :x2="c.x" :y2="c.yLow"
                    :stroke="c.color" stroke-width="1" />
                <rect :x="c.x - candleW / 2" :y="c.bodyTop" :width="candleW" :height="c.bodyH"
                    :fill="c.color" />
            </g>

            <!-- 十字光标 -->
            <g v-if="hover">
                <line :x1="hover.x" :y1="chartPad.top" :x2="hover.x" :y2="chartHeight - chartPad.bottom"
                    stroke="rgba(200,216,232,0.35)" stroke-width="1" stroke-dasharray="2 3" />
                <line :x1="chartPad.left" :y1="hover.y" :x2="chartWidth - chartPad.right" :y2="hover.y"
                    stroke="rgba(200,216,232,0.26)" stroke-width="1" stroke-dasharray="2 3" />
                <rect :x="hover.x - 1" :y="chartPad.top" width="2" :height="plotH" fill="rgba(200,216,232,0.08)" />
                <g class="y-axis-hover-label" :transform="`translate(${chartWidth - chartPad.right + yAxisHoverTip}, ${hover.yAxisLabelY - yAxisHoverH / 2})`">
                    <polygon :class="hover.priceDiffUp ? 'y-axis-hover-arrow up' : 'y-axis-hover-arrow down'" :points="`-${yAxisHoverTip},${yAxisHoverH / 2} 0,${yAxisHoverH / 2 - yAxisHoverH * 0.18} 0,${yAxisHoverH / 2 + yAxisHoverH * 0.18}`" />
                    <rect :class="hover.priceDiffUp ? 'y-axis-hover-bg up' : 'y-axis-hover-bg down'" x="0" y="0" :width="yAxisHoverW" :height="yAxisHoverH" :rx="yAxisHoverRx" />
                    <text class="y-axis-hover-price" :x="yAxisHoverPadX" :y="yAxisHoverPriceY" :style="{ fontSize: yAxisHoverPriceFontSize + 'px' }">{{ formatPrice(hover.currentPrice) }}</text>
                    <text class="y-axis-hover-rate" :class="hover.priceDiffUp ? 'up' : 'down'" :x="yAxisHoverPadX" :y="yAxisHoverRateY" :style="{ fontSize: yAxisHoverRateFontSize + 'px' }">{{ formatPercent(hover.priceDiffRate) }}</text>
                </g>
            </g>

            <!-- 当前蜡烛高亮：仅保留竖线十字，不再绘制蓝色背景块 -->

            <!-- K 线 tooltip：OHLC + 当前 Y 轴价格 -->
            <g v-if="hover && Number.isFinite(hover.tooltipX)" class="chart-tooltip" :transform="`translate(${hover.tooltipX}, ${hover.tooltipY})`">
                <rect class="tooltip-bg" :width="tooltipW" :height="tooltipH" rx="6" />
                <text class="tooltip-title" :x="tooltipPadX" :y="tooltipTitleY" :style="{ fontSize: tooltipTitleFontSize + 'px' }">{{ formatTime(hover.t) }}</text>
                <text class="tooltip-row" :x="tooltipPadX" :y="tooltipRowYs[0]" :style="{ fontSize: tooltipRowFontSize + 'px' }">当前价：{{ formatPrice(hover.currentPrice) }}</text>
                <text class="tooltip-row" :x="tooltipPadX" :y="tooltipRowYs[1]" :style="{ fontSize: tooltipRowFontSize + 'px' }">开盘：{{ formatPrice(hover.o) }}</text>
                <text class="tooltip-row" :x="tooltipPadX" :y="tooltipRowYs[2]" :style="{ fontSize: tooltipRowFontSize + 'px' }">收盘：{{ formatPrice(hover.c) }}</text>
                <text class="tooltip-row tooltip-up" :x="tooltipPadX" :y="tooltipRowYs[3]" :style="{ fontSize: tooltipRowFontSize + 'px' }">最高：{{ formatPrice(hover.h) }}</text>
                <text class="tooltip-row tooltip-down" :x="tooltipPadX" :y="tooltipRowYs[4]" :style="{ fontSize: tooltipRowFontSize + 'px' }">最低：{{ formatPrice(hover.l) }}</text>
                <text v-if="tapActive" class="tooltip-badge" :x="tooltipBadgeX" :y="tooltipTitleY" :style="{ fontSize: tooltipBadgeFontSize + 'px' }">已选中</text>
            </g>

            <!-- 长按进度环（按住 0.5s 进入 Scrub 模式前的视觉提示） -->
            <g v-if="holdProgress > 0 && !scrubMode && holdPointerX >= 0">
                <circle :cx="holdPointerX" :cy="holdPointerY" r="22"
                    fill="rgba(59,130,196,0.08)" stroke="none" />
                <circle :cx="holdPointerX" :cy="holdPointerY" r="18"
                    fill="none" stroke="rgba(59,130,196,0.12)" stroke-width="3" />
                <circle :cx="holdPointerX" :cy="holdPointerY" r="18"
                    fill="none" stroke="rgba(59,130,196,0.9)" stroke-width="3"
                    :stroke-dasharray="`${2 * Math.PI * 18}`"
                    :stroke-dashoffset="`${2 * Math.PI * 18 * (1 - holdProgress)}`"
                    stroke-linecap="round"
                    :transform="`rotate(-90, ${holdPointerX}, ${holdPointerY})`"
                    class="hold-progress-ring" />
            </g>
        </svg>

        <!-- dataZoom 滑条：显示/拖动当前视口在全部数据中的位置 -->
        <div class="datazoom"
            @pointerdown="onSliderDown"
            @pointermove="sliderMove"
            @pointerup="onSliderUp"
            @pointerleave="onSliderUp"
        >
            <div class="dz-track">
                <div class="dz-window" :style="{ left: sliderLeftPct + '%', width: sliderWidthPct + '%' }"></div>
            </div>
            <div class="dz-hint">{{ visibleCount }} / {{ kline.length }} 根（拖动平移，滚轮/双指缩放）</div>
        </div>

    </div>
</template>

<style scoped>
.chart-card {
    background: rgba(13, 26, 38, 0.6);
    border: none;
    border-radius: 0;
    padding: 0;
}
.chart-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px 16px;
}
.chart-title {
    font-size: 15px;
    font-weight: 700;
    color: #e0edf5;
}

/* ---------- 工具栏 ---------- */
.toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
}
.tool-btn {
    padding: 4px 12px;
    background: rgba(30, 58, 95, 0.4);
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    color: #8ba4be;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
    white-space: nowrap;
}
.tool-btn:hover {
    color: #e0edf5;
    border-color: #3b82c4;
}
.tool-btn.active {
    background: #1e3a5f;
    border-color: #3b82c4;
    color: #fff;
}

/* ---------- 图标按钮（更多 ＋ / 指标 折线） ---------- */
.icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: #8ba4be;
    cursor: pointer;
    transition: all 0.15s;
}
.icon-btn:hover {
    color: #e0edf5;
    background: rgba(30, 58, 95, 0.7);
}
.icon-btn.active {
    background: #1e3a5f;
    color: #fff;
}

/* ---------- 分段控件（快捷级别，连在一起点击高亮，无边框） ---------- */
.seg {
    display: inline-flex;
    align-items: stretch;
    overflow: hidden;
}
.seg-item {
    padding: 4px 12px;
    font-size: 11px;
    color: #8ba4be;
    cursor: pointer;
    white-space: nowrap;
    background: transparent;
    transition: all 0.15s;
    font-family: inherit;
    user-select: none;
}
.seg-item:hover {
    color: #e0edf5;
    background: rgba(30, 58, 95, 0.7);
}
.seg-item.active {
    background: #1e3a5f;
    color: #fff;
}

.caret {
    font-size: 9px;
    margin-left: 2px;
    opacity: 0.8;
}

.tool-drop {
    position: relative;
}
.drop-panel {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 20;
    min-width: 110px;
    max-height: 320px;
    overflow: auto;
    padding: 6px;
    background: #0d1a26;
    border: 1px solid #2a5a8f;
    border-radius: 6px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.drop-item {
    padding: 5px 10px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: #c8d8e8;
    font-size: 12px;
    text-align: left;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
}
.drop-item:hover {
    background: rgba(30, 58, 95, 0.6);
}
.drop-item.active {
    color: #fff;
    background: #1e3a5f;
}

/* 更多面板：一行 3 个按钮的网格布局 */
.drop-grid {
    width: 156px;
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
}
.drop-grid .drop-item {
    text-align: center;
    padding: 5px 4px;
    white-space: nowrap;
}
.drop-item.drop-check {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}
.drop-item.drop-check input {
    accent-color: #3b82c4;
}
.check-color {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
}

.fade-enter-active, .fade-leave-active {
    transition: opacity 0.12s;
}
.fade-enter-from, .fade-leave-to {
    opacity: 0;
}

.candle-chart {
    width: 100%;   /* 宽度占比由外层布局控制，图表自身铺满所在列 */
    height: auto;
    display: block;
    margin: 0 auto;
    cursor: grab;
    /* pan-y: 纵向滚动交给浏览器；横向单指拖拽由 pointer 事件自行平移；
       双指捏合缩放由 JS 自行处理（不带 pinch-zoom，浏览器不会缩放整页） */
    touch-action: pan-y;
    user-select: none;
}
.candle-chart.dragging {
    cursor: grabbing;
}
.chart-hit-area {
    fill: transparent;
    pointer-events: all;
}
.axis-text {
    fill: #6a8aa8;
    font-size: 10px;
}
.y-axis-hover-label {
    pointer-events: none;
    font-variant-numeric: tabular-nums;
}
.y-axis-hover-bg {
    stroke-width: 1.5;
}
.y-axis-hover-bg.up {
    fill: #172230;
    stroke: rgb(46, 204, 113);
}
.y-axis-hover-bg.down {
    fill: #172230;
    stroke: rgb(231, 76, 60);
}
.y-axis-hover-arrow {
    stroke: none;
}
.y-axis-hover-arrow.up,
.y-axis-hover-arrow.down {
    fill: #172230;
}
.y-axis-hover-price {
    fill: #e8f1f8;
    font-size: 8px;
    font-weight: 700;
}
.y-axis-hover-rate {
    font-size: 8px;
}
.y-axis-hover-rate.up {
    fill: rgb(46, 204, 113);
}
.y-axis-hover-rate.down {
    fill: rgb(231, 76, 60);
}
.chart-tooltip {
    pointer-events: none;
    font-variant-numeric: tabular-nums;
}
.tooltip-bg {
    fill: rgba(8, 16, 24, 0.92);
    stroke: rgba(59, 130, 196, 0.55);
    stroke-width: 1;
    filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.35));
}
.tooltip-title {
    fill: #e0edf5;
    font-size: 12px;
    font-weight: 700;
}
.tooltip-row {
    fill: #c8d8e8;
    font-size: 11px;
}
.tooltip-up {
    fill: #2ecc71;
}
.tooltip-down {
    fill: #e74c3c;
}
.tooltip-badge {
    fill: #93c5fd;
    font-size: 10px;
    font-weight: 700;
}

/* ---------- dataZoom 滑条 ---------- */
.datazoom {
    margin-top: 10px;
    user-select: none;
    touch-action: none;
}
.dz-track {
    position: relative;
    height: 18px;
    background: rgba(30, 58, 95, 0.35);
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    cursor: pointer;
}
.dz-window {
    position: absolute;
    top: 0;
    bottom: 0;
    background: rgba(59, 130, 196, 0.4);
    border: 1px solid #3b82c4;
    border-radius: 3px;
    cursor: grab;
    box-sizing: border-box;
}
.dz-hint {
    margin-top: 4px;
    font-size: 11px;
    color: #6a8aa8;
    text-align: right;
}
.indicator-readout {
    font-size: 16px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

/* ---------- 长按进度环动画 ---------- */
.hold-progress-ring {
    animation: hold-pulse 0.6s ease-in-out infinite alternate;
}
@keyframes hold-pulse {
    from { stroke-opacity: 0.6; }
    to { stroke-opacity: 1; }
}

.chart-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    height: 300px;
    color: #8ba4be;
    font-size: 14px;
}
.spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #1e3a5f;
    border-top-color: #3b82c4;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
</style>