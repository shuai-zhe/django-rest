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
    interval: { type: String, default: '1m' },
})

// ==================== K 线数据（自身请求） ====================
// 图表内部自行管理当前级别（可被工具栏切换），props.interval 仅作为初始值
const currentInterval = ref(props.interval || '1m')
const { kline, intervals, loading, error, startAutoRefresh, stop, bind } =
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
    startAutoRefresh()
})
onUnmounted(() => {
    document.removeEventListener('click', onDocClick)
    stop()
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
}

// 数据刷新后回到最新视口
watch(kline, () => {
    resetView()
    hoverAbs.value = -1
})

// 当前可见窗口内的 K 线切片
const visibleKline = computed(() =>
    kline.value.slice(viewStart.value, viewStart.value + visibleCount.value)
)

// ==================== SVG 几何配置 ====================
const chartWidth = 820
const chartHeight = 380
const chartPad = { top: 20, right: 76, bottom: 40, left: 12 }

const plotW = computed(() => chartWidth - chartPad.left - chartPad.right)
const plotH = computed(() => chartHeight - chartPad.top - chartPad.bottom)

const step = computed(() => plotW.value / visibleCount.value)
// 蜡烛宽度随缩放自适应，避免密集时重叠
const candleW = computed(() => Math.max(1, Math.min(7, step.value * 0.6)))

function xOfRel(j) {
    return chartPad.left + j * step.value + step.value / 2
}

// 参与 Y 轴定标的所有数值：可见窗口内 K 线最高/最低 + 指标值
const yDomain = computed(() => {
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

// ==================== 平移 / 缩放 / 十字光标 ====================
const hoverAbs = ref(-1)
const dragging = ref(false)
let dragState = null

function pxToRelIndex(px, rect) {
    const ratio = (px / rect.width) * chartWidth
    return Math.round((ratio - chartPad.left - step.value / 2) / step.value)
}

function onPointerDown(e) {
    dragging.value = true
    dragState = {
        startClientX: e.clientX,
        startViewStart: viewStart.value,
    }
    e.currentTarget.setPointerCapture?.(e.pointerId)
}
function onPointerMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    // 拖动中 → 平移视口
    if (dragging.value && dragState) {
        const dxPx = e.clientX - dragState.startClientX
        const stepPx = (rect.width / chartWidth) * step.value
        const dBars = Math.round(dxPx / stepPx)
        viewStart.value = dragState.startViewStart - dBars
        clampView()
        return
    }
    // 否则更新悬停十字光标
    const j = pxToRelIndex(e.clientX - rect.left, rect)
    const abs = viewStart.value + j
    hoverAbs.value = (abs >= 0 && abs < kline.value.length) ? abs : -1
}
function onPointerUp() {
    dragging.value = false
    dragState = null
}
function onPointerLeave() {
    hoverAbs.value = -1
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
    const out = {
        idx: abs,
        x: xOfRel(j),
        t: ks[abs].t,
        o: Number(k.o), c: Number(k.c), h: Number(k.h), l: Number(k.l),
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
function formatTime(t) {
    const d = new Date(Number(t) * 1000)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ==================== 生命周期 ====================
onMounted(() => {
    startAutoRefresh()
})
onUnmounted(() => {
    stop()
})
</script>

<template>
    <div class="chart-card">
        <div class="chart-head">
            <span class="chart-title">K 线图</span>

            <!-- 工具栏：级别快捷按钮 + 更多面板 + 指标面板 -->
            <div class="toolbar">
                <!-- 快捷级别 -->
                <button
                    v-for="v in quickIntervals"
                    :key="'q-' + v"
                    class="tool-btn"
                    :class="{ active: currentInterval === v }"
                    @click="selectInterval(v)"
                >
                    {{ intervalLabel(v) }}
                </button>

                <!-- 更多：面板展示全部级别 -->
                <div class="tool-drop" @click.stop>
                    <button class="tool-btn" :class="{ active: showMore }" @click="showMore = !showMore; showIndicators = false">
                        更多 <span class="caret">▾</span>
                    </button>
                    <transition name="fade">
                        <div v-if="showMore" class="drop-panel">
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

                <!-- 指标：面板展示指标勾选项 -->
                <div class="tool-drop" @click.stop>
                    <button class="tool-btn" :class="{ active: showIndicators }" @click="showIndicators = !showIndicators; showMore = false">
                        指标 <span class="caret">▾</span>
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
            @wheel.prevent="onWheel"
        >
            <!-- 网格线 + Y 轴价格刻度（最右侧） -->
            <g v-for="t in yTicks" :key="'y' + t.v">
                <line :x1="chartPad.left" :y1="t.y" :x2="chartWidth - chartPad.right" :y2="t.y"
                    stroke="rgba(30,58,95,0.5)" stroke-width="1" />
                <text :x="chartWidth - chartPad.right + 8" :y="t.y + 4" text-anchor="start" class="axis-text">
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
                <rect :x="hover.x - 1" :y="chartPad.top" width="2" :height="plotH" fill="rgba(200,216,232,0.08)" />
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

        <!-- 悬浮信息栏：OHLC + 指标数值 -->
        <div v-if="hover" class="hover-info">
            <span class="hi-time">{{ formatTime(hover.t) }}</span>
            <span class="hi-item">开 {{ formatPrice(hover.o) }}</span>
            <span class="hi-item">高 <b class="up">{{ formatPrice(hover.h) }}</b></span>
            <span class="hi-item">低 <b class="down">{{ formatPrice(hover.l) }}</b></span>
            <span class="hi-item">收 {{ formatPrice(hover.c) }}</span>
            <span
                v-for="(ind, ii) in hover.indicators"
                :key="'hi-' + ii"
                class="hi-item"
                :style="{ color: ind.color }"
            >
                {{ ind.name }} {{ formatPrice(ind.value) }}
            </span>
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
    touch-action: none;
    user-select: none;
}
.candle-chart.dragging {
    cursor: grabbing;
}
.axis-text {
    fill: #6a8aa8;
    font-size: 10px;
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
.hover-info .hi-time {
    color: #8ba4be;
    font-weight: 700;
}
.hover-info .hi-item b.up { color: #2ecc71; }
.hover-info .hi-item b.down { color: #e74c3c; }

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
