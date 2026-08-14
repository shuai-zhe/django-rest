<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NewDetail } from "@/utils/apis/new"

const route = useRoute()
const router = useRouter()

const id = computed(() => (route.params.id || '').toString())

const detail = ref(null)
const loading = ref(false)
const error = ref('')

const TYPE_LABEL = { new: '加密', stock: '股票' }

// 热度：取自 extra.hot / extra.views，缺失时占位
const hot = computed(() => {
    const extra = detail.value?.extra || {}
    const v = extra.hot ?? extra.views
    return v != null ? v : '--'
})

function formatTime(t) {
    if (!t) return ''
    const d = new Date(t)
    if (isNaN(d.getTime())) return ''
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function stripHtml(s) {
    if (!s) return ''
    return String(s).replace(/<[^>]*>/g, '')
}

function goBack() {
    // 优先返回上一页（来自列表），否则回到新闻列表
    if (window.history.length > 1) router.back()
    else router.push('/news')
}

async function fetchDetail() {
    if (!id.value) {
        error.value = '缺少新闻 ID'
        return
    }
    loading.value = true
    error.value = ''
    try {
        const res = await NewDetail(id.value)
        // 后端统一响应用于 code/data/success 包裹，响应拦截器已剥离 HTTP 层，
        // 业务数据在 res.data 中；查无时 res.data 为 null。
        detail.value = res?.data ?? null
        if (!detail.value) error.value = '新闻不存在或已删除'
    } catch (e) {
        error.value = '新闻加载失败，请稍后重试'
        console.error('获取新闻详情失败:', e)
        detail.value = null
    } finally {
        loading.value = false
    }
}

onMounted(fetchDetail)
</script>

<template>
    <div class="nd-page">
        <!-- 顶部导航 -->
        <div class="nd-header">
            <button class="back-btn" @click="goBack" title="返回" aria-label="返回">
                <svg viewBox="0 0 24 24" width="20" height="20"><path d="M15 5l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
            </button>
            <span class="nd-title">新闻详情</span>
        </div>

        <!-- 主体：最大宽度居中 -->
        <div class="nd-body" v-if="!loading && !error && detail">
            <!-- 顶部：标题 -->
            <h1 class="nd-headline">{{ detail.title }}</h1>

            <!-- 标题下方：日期、热度等 -->
            <div class="nd-meta">
                <span class="nd-date">{{ formatTime(detail.created_at) }}</span>
                <span class="nd-dot">·</span>
                <span class="nd-type">{{ TYPE_LABEL[detail.new_type] || '资讯' }}</span>
                <span class="nd-dot">·</span>
                <span class="nd-hot">热度 {{ hot }}</span>
            </div>

            <!-- 内容区：左内容 + 右保留区 -->
            <div class="nd-content">
                <!-- 左侧：内容 -->
                <article class="nd-main">
                    <div class="nd-text" v-html="detail.content"></div>
                </article>

                <!-- 右侧：保留内容（后续扩展），小屏不显示 -->
                <aside class="nd-aside">
                    <!-- TODO: 后续扩展（相关新闻 / 标签云 / 项目关联等） -->
                </aside>
            </div>
        </div>

        <!-- 加载 -->
        <div v-else-if="loading" class="nd-state">
            <div class="spinner"></div>
            <span>加载中…</span>
        </div>

        <!-- 错误 -->
        <div v-else class="nd-state">
            <span>{{ error }}</span>
            <button class="nd-back-link" @click="goBack">返回</button>
        </div>
    </div>
</template>

<style scoped>
.nd-page {
    min-height: 100vh;
    background: #0f1923;
    color: #c8d8e8;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
}
.nd-header {
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
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 50%;
    color: #c8d8e8;
    cursor: pointer;
    transition: all 0.2s;
}
.back-btn:hover {
    background: rgba(30, 58, 95, 0.7);
    color: #fff;
}
.nd-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
}

/* 主体：最大宽度居中 */
.nd-body {
    max-width: 1100px;
    margin: 28px auto;
    padding: 0 24px;
}

/* 顶部：标题 */
.nd-headline {
    margin: 0 0 14px;
    font-size: 26px;
    font-weight: 700;
    line-height: 1.35;
    color: #eef5fa;
}

/* 标题下方：日期、热度等 */
.nd-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding-bottom: 16px;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.5);
    font-size: 13px;
    color: #8ba4be;
}
.nd-dot {
    color: #3a5675;
}
.nd-type {
    padding: 2px 8px;
    background: rgba(30, 58, 95, 0.4);
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    color: #9fc1e6;
}
.nd-hot {
    color: #f0a85a;
}

/* 内容区：左内容 + 右保留区 */
.nd-content {
    display: flex;
    gap: 28px;
    align-items: flex-start;
}
.nd-main {
    flex: 1 1 auto;
    min-width: 0;
}
.nd-text {
    font-size: 15px;
    line-height: 1.8;
    color: #c8d8e8;
    word-break: break-word;
}
.nd-text :deep(p) {
    margin: 0 0 14px;
}
.nd-text :deep(img) {
    max-width: 100%;
    border-radius: 6px;
    margin: 8px 0;
}
.nd-text :deep(a) {
    color: #6ea8f7;
}

/* 右侧：保留内容（后续扩展） */
.nd-aside {
    flex: 0 0 300px;
    width: 300px;
    align-self: stretch;
    min-height: 200px;
    background: rgba(13, 26, 38, 0.6);
    border: 1px dashed rgba(30, 58, 95, 0.6);
    border-radius: 10px;
}

/* 状态 */
.nd-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 50vh;
    color: #8ba4be;
    font-size: 14px;
}
.spinner {
    width: 28px;
    height: 28px;
    border: 3px solid #1e3a5f;
    border-top-color: #3b82c4;
    border-radius: 50%;
    animation: nd-spin 0.8s linear infinite;
}
@keyframes nd-spin { to { transform: rotate(360deg); } }
.nd-back-link {
    padding: 6px 18px;
    background: #1e3a5f;
    border: 1px solid #3b82c4;
    border-radius: 6px;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
}

/* 小屏：右侧保留区不显示，内容占满 */
@media (max-width: 768px) {
    .nd-content {
        display: block;
    }
    .nd-aside {
        display: none;
    }
    .nd-headline {
        font-size: 21px;
    }
}
</style>
