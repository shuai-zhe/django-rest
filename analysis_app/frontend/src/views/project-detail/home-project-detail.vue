<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectData } from "@/composables/useProjectData"
import ProjectOverview from "./ProjectOverview.vue"
import KlineChart from "./KlineChart.vue"

const route = useRoute()
const router = useRouter()

// 从路由参数读取 codeId（子组件通过 prop 接收并各自请求数据）
const codeId = computed(() => (route.params.codeId || '').toString())

// 项目名称/显示名（容器页用于顶部导航，取自 Project 表共享数据）
const { projectListData, fetchData } = useProjectData()
const project = computed(() =>
    projectListData.value.find(d => d.code_id === codeId.value) || null
)

function goBack() {
    router.push('/')
}

onMounted(() => {
    fetchData()   // 预加载 Project 表，供头部展示名称
})
</script>

<template>
    <div class="detail-root">
        <!-- 顶部导航 -->
        <div class="detail-header">
            <button class="back-btn" @click="goBack">← 返回</button>
            <span class="header-title">{{ (project?.name || codeId).toUpperCase() }}</span>
            <span class="header-sub">{{ project?.display_name || '' }}</span>
        </div>

        <div class="detail-body">
            <!-- 左列（60%）：项目概览 + K 线图 -->
            <div class="col-chart">
                <!-- 概览子组件：自身请求 K 线 + Project 表展示 24h高低/成交量/市值 -->
                <ProjectOverview :code-id="codeId" />

                <!-- K 线图子组件：自身请求 K 线数据并绘制蜡烛图 -->
                <KlineChart :code-id="codeId" interval="1m" />
            </div>

            <!-- 右列（40%）：预留区域，供后续其它内容展示 -->
            <div class="col-side">
                <!-- 占位提示：后续在此放置其它内容 -->
            </div>
        </div>
    </div>
</template>

<style scoped>
.detail-root {
    min-height: 100vh;
    background: #0f1923;
    color: #c8d8e8;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
}

/* ---------- 顶部导航 ---------- */
.detail-header {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 56px;
    padding: 0 24px;
    background: rgba(13, 26, 38, 0.95);
    border-bottom: 1px solid #1e3a5f;
    position: sticky;
    top: 0;
    z-index: 10;
}
.back-btn {
    padding: 6px 14px;
    background: #1e3a5f;
    border: 1px solid #2a5a8f;
    border-radius: 6px;
    color: #c8d8e8;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
}
.back-btn:hover {
    background: #2a5a8f;
    color: #fff;
}
.header-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
}
.header-sub {
    font-size: 13px;
    color: #6a8aa8;
}

/* ---------- 主体 ---------- */
.detail-body {
    width: 100%;
    display: flex;
    flex-direction: column;
}
.col-chart,
.col-side {
    width: 100%;
}

/* 大屏幕：左 60% 图表 + 右 40% 预留内容 */
@media (min-width: 1200px) {
    .detail-body {
        flex-direction: row;
    }
    .col-chart {
        width: 60%;
    }
    .col-side {
        width: 40%;
    }
}
</style>
