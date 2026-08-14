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

function toggleIndicator(p) {
    const k = presetKey(p)
    const next = new Set(activeIds.value)
    if (next.has(k)) next.delete(k)
    else next.add(k)
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

// ==================== 视口（dataZoom：固定展示 N 条，可拖动/缩放） ====================
const MIN_VISIBLE = 10
const DEFAULT_VISIBLE = 80

const viewStart = ref(0)              // 视口起始绝对索引
const visibleCount = ref(DEFAULT_VISIBLE) // 当前展示条数

// Y 轴固定刻度：tapActive 拖拽 Scrub 时锁定，首次点击时缓存
const fixedYDomain = ref(null)

function clampView() {
    const len = kline.value.length
    if (len === 0) { viewStart.value = 0; return }
    visibleCount.value = Math.max(MIN_VISIBLE, Math.min(visibleCount.value, len))
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

// 数据刷新后回到最新视口
let preserveView = false   // 置位时表示本次 kline 变化来自「向前加载」，不回跳最新
watch(kline, () => {
    if (preserveView) { preserveView = false; return }
    resetView()
    hoverAbs.value = -1
    tapActive.value = false
    fixedYDomain.value = null
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
let dragState = null
let lastTapTime = 0

// 拖拽阈值：pointerdown 后移动超过此像素视为拖拽（panning），否则为点击（tap）
const TAP_THRESHOLD = 5
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
    pointerStartClientX = e.clientX
    pointerStartClientY = e.clientY
    pointerMoved = false
    suppressNextClick = false
    scrubMode.value = false
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
    if (!dragging.value || !dragState) {
        updateHoverFromPointer(e)
        return
    }

    const dxPx = Math.abs(e.clientX - pointerStartClientX)
    const dyPx = Math.abs(e.clientY - pointerStartClientY)

    // 首次超过阈值 → 判定为拖拽（panning），取消 Scrub 计时器
    if (!pointerMoved && (dxPx > TAP_THRESHOLD || dyPx > TAP_THRESHOLD)) {
        pointerMoved = true
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
        // 长按过程中也实时显示当前位置的数据
        updateHoverFromPointer(e)
    }

    if (scrubMode.value) {
        // Scrub 模式：仅跟随手指/鼠标显示数据，不平移视口，Y 轴锁定
        updateHoverFromPointer(e)
        return
    }

    if (pointerMoved) {
        // 普通拖拽 → 平移视口
        const stepPx = (rect.width / chartWidth) * step.value
        const dBars = Math.round((e.clientX - dragState.startClientX) / stepPx)
        viewStart.value = dragState.startViewStart - dBars
        clampView()
    }

    // 非 Scrub 模式且未移动 → 不更新 hoverAbs（等待点击或 Scrub 判定）
}
function onPointerUp() {
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
}
function onPointerLeave() {
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

function dismissTap() {
    tapActive.value = false
    hoverAbs.value = -1
    hoverPointerX.value = -1
    hoverPointerY.value = -1
    fixedYDomain.value = null
}

// 滚轮缩放（以当前视口中心为锚点）
function onWheel(e) {
    const len = kline.value.length
    if (!len) return
    e.preventDefault()
    const oldCount = visibleCount.value
    const center = viewStart.value + oldCount / 2
    const factor = e.deltaY > 0 ? 1.12 : 1 / 1.12
    const newCount = Math.max(MIN_VISIBLE, Math.min(Math.round(oldCount * factor), len))
    visibleCount.value = newCount
    viewStart.value = Math.round(center - newCount / 2)
    clampView()
}

// 底部 dataZoom 滑条
const sliderLeftPct = computed(() =>
    kline.value.length ? (viewStart.value / kline.value.length) * 100 : 0
)
const sliderWidthPct = computed(() =>
    kline.value.length ? (visibleCount.value / kline.value.length) * 100 : 100
)
function sliderMove(e) {
    if (!dragging.value) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    const center = ratio * kline.value.length
    viewStart.value = Math.round(center - visibleCount.value / 2)
    clampView()
}

const hover = computed(() => {
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
    const priceDiffRate = closePrice ? ((yAxisPrice - closePrice) / closePrice) * 100 : 0
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
    if (v >= 1) return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    return '$' + Number(v).toFixed(6)
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
            @wheel="onWheel"
            @click="onChartClick"
        >
            <rect class="chart-hit-area" x="0" y="0" :width="chartWidth" :height="chartHeight" />

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
            @pointerdown="onPointerDown"
            @pointermove="sliderMove"
            @pointerup="onPointerUp"
            @pointerleave="onPointerUp"
        >
            <div class="dz-track">
                <div class="dz-window" :style="{ left: sliderLeftPct + '%', width: sliderWidthPct + '%' }"></div>
            </div>
            <div class="dz-hint">{{ visibleCount }} / {{ kline.length }} 根（拖动平移，滚轮缩放）</div>
        </div>

        <!-- 固定选中/长按提示，不再承载行情数据 -->
        <div v-if="tapActive || (holdProgress > 0 && !scrubMode)" class="hover-info">
            <span v-if="tapActive" class="hi-tap-badge">📌 已选中</span>
            <span v-if="holdProgress > 0 && !scrubMode" class="hi-tap-badge" style="background: rgba(59,130,196,0.15); border-color: rgba(59,130,196,0.3); color: #6ea8f7;">
                按住查看
            </span>
            <button v-if="tapActive" class="hi-close" @click.stop="dismissTap" title="取消选中">✕</button>
        </div>

        <!-- 图例（指标 + 涨跌） -->
        <div class="chart-legend">
            <span><i class="dot up"></i> 上涨</span>
            <span><i class="dot down"></i> 下跌</span>
            <template v-for="(line, li) in overlayLines" :key="'lg-' + li + '-' + line.name">
                <span v-if="li < 8"><i class="dot" :style="{ background: line.color }"></i> {{ line.name }}</span>
            </template>
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
.indicator-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
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
.chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin-top: 10px;
    font-size: 12px;
    color: #8ba4be;
}
.chart-legend .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    margin-right: 5px;
    vertical-align: middle;
}
.dot.up { background: #2ecc71; }
.dot.down { background: #e74c3c; }

.hover-info {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
    padding: 8px 12px;
    background: rgba(15, 25, 35, 0.6);
    border: 1px solid rgba(30, 58, 95, 0.6);
    border-radius: 6px;
    font-size: 12px;
    color: #c8d8e8;
    font-variant-numeric: tabular-nums;
}
/* ---------- 移动端点击选中样式 ---------- */
.hi-tap-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    background: rgba(59, 130, 196, 0.25);
    border: 1px solid rgba(59, 130, 196, 0.5);
    border-radius: 4px;
    font-size: 11px;
    color: #93c5fd;
    font-weight: 600;
    white-space: nowrap;
}
.hi-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    padding: 0;
    background: transparent;
    border: 1px solid rgba(106, 138, 168, 0.4);
    border-radius: 50%;
    color: #8ba4be;
    font-size: 11px;
    cursor: pointer;
    line-height: 1;
    flex-shrink: 0;
    transition: all 0.15s;
}
.hi-close:hover {
    background: rgba(231, 76, 60, 0.2);
    border-color: #e74c3c;
    color: #e74c3c;
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