<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import DataHeader from "./DataHeader.vue"
import ProjectList from "./ProjectList.vue"
import AnalysisScatterGraph from "./AnalysisScatterGraph.vue"

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

// 查看详情事件（暂时空处理，待后续实现）
function onViewDetail(item) {
    // TODO: 跳转详情页 / 弹出详情弹窗
    console.log('viewDetail', item)
}

// 时间维度（由 DataHeader 中的按钮控制）
const activeTimeFrame = ref('day')

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
            :hidden="showTable"
            @update:active-time-frame="activeTimeFrame = $event"
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
