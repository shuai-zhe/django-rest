<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import DataHeader from "./DataHeader.vue"
import ProjectList from "./ProjectList.vue"
import AnalysisScatterGraph from "./AnalysisScatterGraph.vue"
import { useGlobalDataType, useProjectData } from "@/composables/useProjectData"

const router = useRouter()

// 首页全量数据实例（用于指标/时间维度变化后重新请求）
const { fetchData, startAutoRefresh, stopAutoRefresh } = useProjectData()

// 筛选值（由 DataHeader 面板计算后 emit 上来）
const rankMin = ref(null)
const rankMax = ref(null)
const mcMin = ref(null)
const mcMax = ref(null)
const volMin = ref(null)
const volMax = ref(null)
const symbols = ref('')
const riseMin = ref(null)
const searchName = ref(null)   // 名称搜索选中的 code_id（仅表格）

// 查看详情：跳转到项目详情页（搜索选中、气泡点击、表格点击共用）
function onViewDetail(item) {
    const codeId = item?.code_id
    if (!codeId) return
    router.push(`/project/${codeId}`)
}

// 时间维度（由 DataHeader 中的按钮控制）
const activeTimeFrame = ref('day')
// 交易类型：spot=现货 / futures=期货 / stock=股票（暂默认 spot，切换数据源时预留）
const tradeType = ref('spot')
// 指标栏（单选通配符 DSL 数组，互斥）：绝对涨幅 / 正涨幅 / 负涨幅，key 拼接 performance__<时间维度>
const activeMetric = ref([{ op: 'eq', key: 'performance__day', value: 'abs', type: 'metric' }])

// 将筛选条件（排名 / 交易量 / 市值 / 涨幅阈值 / 交易所）转换为通配符 DSL 条件数组
// 排名 → performance__rank，交易量 → volume_dict，市值 → market_cap_dict，涨幅阈值 → performance__<时间维度>
function buildFilterConditions() {
    const conds = []
    if (rankMin.value != null && rankMin.value !== '') {
        conds.push({ op: 'gte', key: 'rank', value: Number(rankMin.value), type: 'metric' })
    }
    if (rankMax.value != null && rankMax.value !== '') {
        conds.push({ op: 'lte', key: 'rank', value: Number(rankMax.value), type: 'metric' })
    }
    if (volMin.value != null && volMin.value !== '') {
        conds.push({ op: 'gte', key: 'volume_dict', value: Number(volMin.value), type: 'metric' })
    }
    if (volMax.value != null && volMax.value !== '') {
        conds.push({ op: 'lte', key: 'volume_dict', value: Number(volMax.value), type: 'metric' })
    }
    if (mcMin.value != null && mcMin.value !== '') {
        conds.push({ op: 'gte', key: 'market_cap_dict', value: Number(mcMin.value), type: 'metric' })
    }
    if (mcMax.value != null && mcMax.value !== '') {
        conds.push({ op: 'lte', key: 'market_cap_dict', value: Number(mcMax.value), type: 'metric' })
    }
    if (riseMin.value != null && riseMin.value !== '') {
        conds.push({ op: 'gte', key: `performance__${activeTimeFrame.value}`, value: Number(riseMin.value), type: 'metric' })
    }
    if (symbols.value) {
        conds.push({ op: 'eq', key: 'symbols', value: symbols.value, type: 'metric' })
    }
    return conds
}

// 统一拼装请求体：指标(单选) + 过滤条件 + 时间维度 + 交易类型
function buildRequest() {
    return {
        filters: [...activeMetric.value, ...buildFilterConditions()],
        time_frame: activeTimeFrame.value,
        trade_type: tradeType.value,
    }
}

const AUTO_REFRESH_INTERVAL = 60000
let autoRefreshStarted = false

function startHomeAutoRefresh() {
    if (autoRefreshStarted) stopAutoRefresh()
    startAutoRefresh(AUTO_REFRESH_INTERVAL, buildRequest)
    autoRefreshStarted = true
}

function stopHomeAutoRefresh() {
    if (!autoRefreshStarted) return
    stopAutoRefresh()
    autoRefreshStarted = false
}

function fetchDataAndRestartTimer() {
    fetchData(true, buildRequest())
    startHomeAutoRefresh()
}

// 指标 / 时间维度 / 筛选条件任一变化 → 带参请求后端
// 注意：此处【不】使用 immediate。
// 原因：immediate 会在父组件 setup 阶段立即触发一次「仅含指标」的请求（此时子组件
// DataHeader 的默认筛选尚未 emit 上来），随后 DataHeader 的 filter watch(immediate)
// 又会将默认筛选（如排名 1-150）emit 上来，再次触发请求，导致刷新首页时发了两次 /gate/project。
// 改为：首屏请求统一放在 onMounted 中（nextTick 后 DataHeader 已 emit 默认值），
// 只发一次「指标 + 默认筛选」合并后的请求；watch 仅响应挂载完成后的用户变更。
let initialFetched = false
watch(
    () => [
        JSON.stringify(activeMetric.value),
        activeTimeFrame.value,
        tradeType.value,
        rankMin.value, rankMax.value,
        volMin.value, volMax.value, mcMin.value, mcMax.value, riseMin.value, symbols.value,
    ],
    () => {
        if (!initialFetched) return   // 挂载前的默认值 emit 不触发请求，交给 onMounted 统一处理
        fetchDataAndRestartTimer()
    },
)

// 数据源类型（货币=gate / 股票=stock）：全局状态，工具栏切换后全站生效
const dataType = useGlobalDataType()

// 滚动节段切换：气泡图 ↔ 表格
const showTable = ref(false)
const chartSectionRef = ref(null)
const tableSectionRef = ref(null)
let observer = null

// 进入提示：刚打开 3s + 滚动时出现 + 按住不动出现 + 点击不算
const showHint = ref(false)
const scrollContainerRef = ref(null)
let hintTimer = null
let pressTimer = null
let tableReached = false   // 用户到达过表格区 → 下次回到气泡图不再滚动提示

onMounted(() => {
    // 首屏统一请求：等 nextTick 后 DataHeader 已把默认筛选（如排名 1-150）emit 上来，
    // 这里一次只发「指标 + 默认筛选」合并后的请求，避免重复请求。
    nextTick(() => {
        initialFetched = true
        fetchDataAndRestartTimer()
    })

    // 用 IntersectionObserver 监听哪个节段占据视口
    observer = new IntersectionObserver((entries) => {
        let bestTarget = null
        let bestRatio = 0
        for (const e of entries) {
            if (e.intersectionRatio > bestRatio) {
                bestRatio = e.intersectionRatio
                bestTarget = e.target
            }
        }
        if (bestTarget && bestRatio > 0.1) {
            const nowTable = bestTarget === tableSectionRef.value
            if (nowTable) tableReached = true
            showTable.value = nowTable
        }
    }, { threshold: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1] })

    if (chartSectionRef.value) observer.observe(chartSectionRef.value)
    if (tableSectionRef.value) observer.observe(tableSectionRef.value)

    // ① 刚进入页面时显示提示 3s
    showHint.value = true
    hintTimer = setTimeout(() => {
        showHint.value = false
        hintTimer = null
    }, 3000)

    // ② 滚动中显示，停下来立即隐藏
    const container = scrollContainerRef.value
    if (container) {
        container.addEventListener('scroll', onScrollHint, { passive: true })
    }

    // ③ 按住不动也显示（点击不算 -> 快速释放不触发）
    const chartEl = chartSectionRef.value
    if (chartEl) {
        chartEl.addEventListener('pointerdown', onPointerDown)
        chartEl.addEventListener('pointerup', onPointerUp)
        chartEl.addEventListener('pointercancel', onPointerUp)
    }

})

onUnmounted(() => {
    stopHomeAutoRefresh()
    if (observer) observer.disconnect()
    const container = scrollContainerRef.value
    if (container) container.removeEventListener('scroll', onScrollHint)
    const chartEl = chartSectionRef.value
    if (chartEl) {
        chartEl.removeEventListener('pointerdown', onPointerDown)
        chartEl.removeEventListener('pointerup', onPointerUp)
        chartEl.removeEventListener('pointercancel', onPointerUp)
    }
    if (hintTimer) { clearTimeout(hintTimer); hintTimer = null }
    if (pressTimer) { clearTimeout(pressTimer); pressTimer = null }
})

function onScrollHint() {
    // 到表格区了不显示
    if (showTable.value) {
        showHint.value = false
        return
    }

    // 已去过表格区 → 不再通过滚动显示提示（用户已经知道）
    if (tableReached) return

    // 滚动时显示
    showHint.value = true

    // 清除上一次的定时器（包含首次加载的 3s 和之前的滚动停止）
    if (hintTimer) {
        clearTimeout(hintTimer)
        hintTimer = null
    }

    // 停止滚动后立即隐藏（200ms 防抖）
    hintTimer = setTimeout(() => {
        showHint.value = false
        hintTimer = null
    }, 200)
}

function onPointerDown() {
    if (showTable.value) return
    // 按住 200ms 还没释放 → 显示提示（说明在犹豫/准备滑动）
    pressTimer = setTimeout(() => {
        showHint.value = true
        pressTimer = null
    }, 200)
}

function onPointerUp() {
    // 快速释放 → 点击 → 不显示提示
    if (pressTimer) {
        clearTimeout(pressTimer)
        pressTimer = null
    }
}
</script>

<template>
    <div class="page-root">
        <DataHeader
            :active-time-frame="activeTimeFrame"
            :data-type="dataType"
            :metric="activeMetric"
            :hidden="showTable"
            @update:active-time-frame="activeTimeFrame = $event"
            @update:metric="activeMetric = $event"
            @update:rank-min="rankMin = $event"
            @update:rank-max="rankMax = $event"
            @update:mc-min="mcMin = $event"
            @update:mc-max="mcMax = $event"
            @update:vol-min="volMin = $event"
            @update:vol-max="volMax = $event"
            @update:symbols="symbols = $event"
            @update:rise-min="riseMin = $event"
            @update:search-name="searchName = $event"
            @view-detail="onViewDetail"
        />
        <!-- 可滚动容器（scroll-snap） -->
        <div ref="scrollContainerRef" class="scroll-container">
            <!-- 节段 1：气泡图 -->
            <section ref="chartSectionRef" class="snap-section">
                <AnalysisScatterGraph
                    :active-time-frame="activeTimeFrame"
                    :rank-min="rankMin"
                    :rank-max="rankMax"
                    :mc-min="mcMin"
                    :mc-max="mcMax"
                    :vol-min="volMin"
                    :vol-max="volMax"
                    :symbols="symbols"
                    :rise-min="riseMin"
                />
                <!-- 下滑提示（渐变透明条，拖动时显示） -->
                <div v-show="showHint" class="scroll-hint-bar">
                    <div class="scroll-hint">
                        <span class="scroll-hint-text">下滑查看数据详情</span>
                        <div class="scroll-arrow">
                            <svg width="16" height="24" viewBox="0 0 16 24" fill="none">
                                <path d="M8 2v18M2 14l6 6 6-6" stroke="currentColor" stroke-width="2"
                                    stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                    </div>
                </div>
            </section>
            <!-- 节段 2：表格 -->
            <section ref="tableSectionRef" class="snap-section table-section">
                <ProjectList
                    :rank-min="rankMin"
                    :rank-max="rankMax"
                    :mc-min="mcMin"
                    :mc-max="mcMax"
                    :vol-min="volMin"
                    :vol-max="volMax"
                    :symbols="symbols"
                    :rise-min="riseMin"
                    :search-name="searchName"
                />
            </section>
        </div>
    </div>
</template>

<style scoped>
.page-root {
    position: relative;
    width: 100%;
    height: 100vh;
    background: #0f1923;
}

/* ====== scroll-snap 滚动容器 ====== */
.scroll-container {
    height: 100vh;
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
    scroll-behavior: smooth;
    scrollbar-width: none;   /* Firefox */
}
.scroll-container::-webkit-scrollbar {
    width: 0;
    height: 0;
}

/* ====== 每个节段占满视口 ====== */
.snap-section {
    scroll-snap-align: start;
    height: 100vh;
    position: relative;
}
/* 表格节段需要禁止外层滚动，让内层 table-scroll 接管 */
.snap-section.table-section {
    overscroll-behavior: contain;
}

/* ====== 下滑提示（渐变透明条，拖动时显示） ====== */
.scroll-hint-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 140px;
    background: linear-gradient(
        to bottom,
        transparent 0%,
        rgba(15, 25, 35, 0.25) 30%,
        rgba(15, 25, 35, 0.6) 70%,
        rgba(15, 25, 35, 0.92) 100%
    );
    pointer-events: none;
    z-index: 10;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 36px;
    transition: opacity 0.4s ease;
}
.scroll-hint {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    opacity: 0.85;
}
.scroll-hint-text {
    font-size: 13px;
    color: #8ab4d0;
    letter-spacing: 1px;
}
.scroll-arrow {
    color: #5b9bd5;
    animation: bounce-down 1.8s ease-in-out infinite;
}
@keyframes bounce-down {
    0%, 100% { transform: translateY(-4px); opacity: 0.4; }
    50% { transform: translateY(10px); opacity: 1; }
}
</style>
