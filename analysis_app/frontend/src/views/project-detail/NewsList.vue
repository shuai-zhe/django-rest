<script setup>
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { NewList } from "@/utils/apis/new"

const props = defineProps({
    // 紧凑模式：用于 col-side 嵌入，隐藏搜索栏、简化分页
    compact: { type: Boolean, default: false },
    // 每页条数（嵌入模式默认更少）
    pageSize: { type: Number, default: 0 },
    // 标题
    title: { type: String, default: '新闻资讯' },
    // 关键字（详情页嵌入时由父级传入当前项目名作为检索词）
    keyword: { type: String, default: '' },
    // 是否以父级 keyword 作为检索条件（详情页传 true，避免挂载时空 keyword 先发一次请求；独立页不传）
    keywordMode: { type: Boolean, default: false },
    // 列表项是否可点击跳转详情（父级可关闭）
    clickable: { type: Boolean, default: true },
})

const router = useRouter()

// 翻页后锚点回头部（.news-title）
const titleRef = ref(null)
function scrollToTop() {
    // 等待 DOM 更新（列表刷新）后再滚动
    nextTick(() => {
        const titleEl = titleRef.value
        if (!titleEl) return
        // 1) 列表自身可滚动容器（非 compact 模式内部 overflow:auto）→ 回到第一条
        const cardEl = titleEl.closest('.news-card')
        const listEl = cardEl ? cardEl.querySelector('.news-list') : null
        if (listEl && listEl.scrollHeight - listEl.clientHeight > 1) {
            listEl.scrollTo({ top: 0, behavior: 'smooth' })
        }
        // 2) 整页滚动场景（compact 嵌入 / 整页滚动）→ 头部滚入视口，避开顶部 sticky 头部(56px)
        const y = titleEl.getBoundingClientRect().top + window.scrollY - 56
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' })
    })
}

// 点击列表项 → 跳转新闻详情页
function onItemClick(item) {
    if (!props.clickable || !item?.id) return
    router.push(`/news/${item.id}`)
}

// ==================== 查询状态 ====================
const keyword = ref('')
const newType = ref('new')       // 默认加密
const page = ref(1)
const pageSize = computed(() => props.pageSize || (props.compact ? 8 : 10))
const total = ref(0)
const list = ref([])
const loading = ref(false)
const error = ref('')

// 类型选项（value 与后端 serializer choices 对齐，label 为中文展示）
const TYPE_OPTIONS = [
    { value: 'new', label: '加密' },
    { value: 'stock', label: '股票' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

function buildParams() {
    // 父级传入的关键字（详情页项目名）优先；否则使用本地搜索框输入
    const kw = (props.keyword || keyword.value).trim()
    return {
        keyword: kw || undefined,
        new_type: newType.value || undefined,
        page: page.value,
        page_size: pageSize.value,
    }
}

async function fetchList() {
    loading.value = true
    error.value = ''
    try {
        const res = await NewList(buildParams())
        // 后端统一响应：{ code, data:{total,list}, success, message }
        const data = res.data || {}
        list.value = data.list || []
        total.value = data.total || 0
    } catch (e) {
        error.value = '新闻加载失败，请稍后重试'
        console.error('获取新闻列表失败:', e)
        list.value = []
        total.value = 0
    } finally {
        loading.value = false
    }
}

// 搜索 / 切换类型 → 回到第一页
function onSearch() {
    page.value = 1
    fetchList()
}
function onTypeChange() {
    page.value = 1
    fetchList()
}
function prevPage() {
    if (page.value > 1) { page.value--; fetchList().then(scrollToTop) }
}
function nextPage() {
    if (page.value < totalPages.value) { page.value++; fetchList().then(scrollToTop) }
}
function goPage(p) {
    if (p < 1 || p > totalPages.value || p === page.value) return
    page.value = p
    fetchList().then(scrollToTop)
}

// ==================== 格式化 ====================
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
function shortContent(s, len = 80) {
    const text = stripHtml(s)
    return text.length > len ? text.slice(0, len) + '…' : text
}

// ==================== 生命周期 ====================
// keywordMode（详情页）：依赖父级异步传入的 keyword，挂载时若已有值则请求，否则等待 watch 命中后再请求，避免空 keyword 的冗余请求
// 非 keywordMode（独立页）：挂载即请求（使用本地搜索框输入）
onMounted(() => {
    if (props.keywordMode) {
        if (props.keyword && props.keyword.trim()) fetchList()
    } else {
        fetchList()
    }
})
// 父级传入的关键字（详情页项目名）变化（含异步加载完成）时重新检索
watch(
    () => props.keyword,
    (kw) => {
        if (kw && kw.trim()) {
            page.value = 1
            fetchList()
        }
    }
)
// 紧凑模式嵌入时，若父级需要刷新可监听（保留接口）
defineExpose({ refresh: fetchList })
onUnmounted(() => { /* 无定时器 */ })
</script>

<template>
    <div class="news-card" :class="{ compact }">
        <!-- 头部 -->
        <div class="news-head">
            <span ref="titleRef" class="news-title">{{ title }}</span>
            <span v-if="!compact" class="news-count">共 {{ total }} 条</span>
        </div>

        <!-- 搜索栏（仅完整模式展示） -->
        <div v-if="!compact" class="news-filter">
            <input
                v-model="keyword"
                class="nf-input"
                type="text"
                placeholder="搜索标题 / 内容…"
                @keyup.enter="onSearch"
            />
            <div class="nf-types">
                <button
                    v-for="opt in TYPE_OPTIONS"
                    :key="opt.value"
                    class="nf-type"
                    :class="{ active: newType === opt.value }"
                    @click="newType = opt.value; onTypeChange()"
                >
                    {{ opt.label }}
                </button>
            </div>
            <button class="nf-search" @click="onSearch">搜索</button>
        </div>

        <!-- 加载 -->
        <div v-if="loading && list.length === 0" class="news-state">
            <div class="spinner"></div>
            <span>加载中…</span>
        </div>

        <!-- 错误 -->
        <div v-else-if="error && list.length === 0" class="news-state">
            <span>{{ error }}</span>
        </div>

        <!-- 空 -->
        <div v-else-if="list.length === 0" class="news-state">
            <span>暂无新闻</span>
        </div>

        <!-- 列表 -->
        <ul v-else class="news-list">
            <li v-for="item in list" :key="item.id" class="news-item" :class="{ clickable }"
                @click="onItemClick(item)">
                <div class="ni-top">
                    <span class="ni-title">{{ item.title }}</span>
                </div>
                <p v-if="item.content" class="ni-content">{{ shortContent(item.content, 140) }}</p>
                <div class="ni-meta">
                    <span class="ni-time">{{ formatTime(item.created_at) }}</span>
                    <span v-if="clickable" class="ni-more" @click.stop="onItemClick(item)">详情 ›</span>
                </div>
            </li>
        </ul>

        <!-- 分页 -->
        <div v-if="list.length > 0" class="news-pager">
            <button class="pg-btn" :disabled="page <= 1" @click="prevPage">上一页</button>
            <span class="pg-info">{{ page }} / {{ totalPages }}</span>
            <button class="pg-btn" :disabled="page >= totalPages" @click="nextPage">下一页</button>
        </div>
    </div>
</template>

<style scoped>
.news-card {
    background: rgba(13, 26, 38, 0.6);
    border-radius: 10px;
    padding: 16px;
    height: 100%;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
}
.news-card.compact {
    padding: 12px;
    height: auto;
}

/* 头部 */
.news-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}
.news-title {
    font-size: 15px;
    font-weight: 700;
    color: #e0edf5;
}
.news-count {
    font-size: 12px;
    color: #6a8aa8;
}

/* 搜索栏 */
.news-filter {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}
.nf-input {
    flex: 1 1 160px;
    min-width: 120px;
    height: 32px;
    padding: 0 10px;
    background: rgba(15, 25, 35, 0.8);
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    color: #c8d8e8;
    font-size: 13px;
    font-family: inherit;
    outline: none;
}
.nf-input:focus {
    border-color: #3b82c4;
}
.nf-types {
    display: inline-flex;
    gap: 4px;
}
.nf-type {
    padding: 4px 10px;
    background: transparent;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    color: #8ba4be;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.nf-type:hover { color: #e0edf5; border-color: #3b82c4; }
.nf-type.active { background: #1e3a5f; border-color: #3b82c4; color: #fff; }
.nf-search {
    padding: 0 16px;
    height: 32px;
    background: #1e3a5f;
    border: 1px solid #3b82c4;
    border-radius: 6px;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.nf-search:hover { background: #27567f; }

/* 状态 */
.news-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    flex: 1;
    min-height: 120px;
    color: #8ba4be;
    font-size: 13px;
}
.spinner {
    width: 26px;
    height: 26px;
    border: 3px solid #1e3a5f;
    border-top-color: #3b82c4;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 列表 */
.news-list {
    list-style: none;
    margin: 0;
    padding: 0;
    flex: 1;
    overflow-y: auto;
}
/* 紧凑模式（嵌入详情页）：跟随整页一起滚动，不单独滚动 */
.news-card.compact .news-list {
    flex: none;
    overflow-y: visible;
}
.news-item {
    padding: 10px 0;
    border-bottom: 1px solid rgba(30, 58, 95, 0.5);
}
.news-item.clickable {
    cursor: pointer;
    transition: background 0.15s;
}
.news-item.clickable:hover {
    background: rgba(30, 58, 95, 0.25);
}
.news-item:last-child { border-bottom: none; }
.ni-top {
    display: flex;
    align-items: center;
    gap: 8px;
}
.ni-title {
    font-size: 14px;
    font-weight: 600;
    color: #e0edf5;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}
/* 紧凑模式（详情页嵌入）：标题字号调小 */
.news-card.compact .ni-title {
    font-size: 12px;
    font-weight: 500;
}
/* 紧凑模式（详情页嵌入）：内容预览更紧凑 */
.news-card.compact .ni-content {
    margin-top: 4px;
    font-size: 11px;
    line-height: 1.45;
    max-height: 40px;
    -webkit-line-clamp: 2;
}
.news-card.compact .ni-meta {
    margin-top: 4px;
}
.news-card.compact .ni-time {
    font-size: 10px;
}
.news-card.compact .ni-more {
    font-size: 10px;
}
.news-card.compact .news-item {
    padding: 8px 0;
}
.ni-content {
    margin: 6px 0 0;
    font-size: 12px;
    color: #8ba4be;
    line-height: 1.5;
    /* 内容超过 50px 高度截断，其余以省略号收起 */
    max-height: 50px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
}
.ni-meta {
    margin-top: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.ni-time {
    font-size: 11px;
    color: #6a8aa8;
}
.ni-more {
    font-size: 11px;
    color: #6ea8f7;
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;
}
.ni-more:hover { color: #9cc4fb; text-decoration: underline; }

/* 分页 */
.news-pager {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid rgba(30, 58, 95, 0.5);
}
.pg-btn {
    padding: 4px 14px;
    background: rgba(30, 58, 95, 0.4);
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    color: #8ba4be;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.pg-btn:hover:not(:disabled) { color: #e0edf5; border-color: #3b82c4; }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pg-info {
    font-size: 12px;
    color: #8ba4be;
    font-variant-numeric: tabular-nums;
}
</style>
