<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectData } from "@/composables/useProjectData"

const router = useRouter()

// 点击项目行 → 跳转详情页
function goDetail(item) {
    if (item?.code_id) router.push(`/project/${item.code_id}`)
}

// ==================== Props ====================
const props = defineProps({
    rankMin: { type: Number, default: null },
    rankMax: { type: Number, default: null },
    mcMin: { type: Number, default: null },
    mcMax: { type: Number, default: null },
    volMin: { type: Number, default: null },
    volMax: { type: Number, default: null },
    symbols: { type: String, default: '' },
    riseMin: { type: Number, default: null },
    searchName: { type: String, default: null },
})

// ==================== 共享数据 ====================
const { projectListData, loading, fetchData } = useProjectData()
const sortKey = ref('rank')
const sortDesc = ref(false)

// 时间维度的配置（用于表头）
const timeColumns = [
    { key: 'min1', label: '1分钟' },
    { key: 'min5', label: '5分钟' },
    { key: 'min15', label: '15分钟' },
    { key: 'hour', label: '1小时' },
    { key: 'hour4', label: '4小时' },
    { key: 'day', label: '日' },
    { key: 'week', label: '周' },
    { key: 'month', label: '月' },
    { key: 'month3', label: '3月' },
    { key: 'year', label: '年' },
]

// 格式化为货币
function formatPrice(v) {
    if (v == null) return '-'
    v = Number(v)
    if (v >= 1) return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (v === 0) return '$0.00'
    // 0 < v < 1：按数量级动态展开小数（不使用科学计数法，避免被舍成 0）
    const decimals = Math.min(20, Math.max(2, Math.ceil(-Math.log10(v)) + 2))
    return '$' + v.toFixed(decimals)
}

function formatMarketCap(v) {
    if (v == null) return '-'
    if (v >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T'
    if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B'
    if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M'
    return '$' + Number(v).toLocaleString('en-US')
}

function formatVolume(v) {
    if (v == null) return '-'
    if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B'
    if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M'
    return '$' + Number(v).toLocaleString('en-US')
}

function formatPct(v) {
    if (v == null) return '-'
    const prefix = v >= 0 ? '+' : ''
    return prefix + v.toFixed(2) + '%'
}

// 根据涨幅返回颜色类名
function pctClass(v) {
    if (v == null) return ''
    if (v > 0) return 'pct-up'
    if (v < 0) return 'pct-down'
    return 'pct-zero'
}

// 排序后的数据
const sortedData = ref([])
const renderKey = ref(0) // 每次排序递增，强制重建 DOM

function getSortValue(item) {
    if (sortKey.value === 'rank') return item.extra_info?.rank ?? 999
    if (sortKey.value === 'market_cap') return item.market_cap_dict?.spot ?? 0
    if (sortKey.value === 'volume') return item.volume_dict?.spot ?? 0
    return item.extra_info?.performance?.[sortKey.value] ?? 0
}

function updateSort() {
    const raw = projectListData.value
    if (!raw || raw.length === 0) {
        sortedData.value = []
        return
    }
    
    const desc = sortDesc.value
    let result = raw.slice().sort((a, b) => {
        const va = getSortValue(a)
        const vb = getSortValue(b)
        const diff = va - vb
        return desc ? (diff > 0 ? -1 : diff < 0 ? 1 : 0) : diff
    })
    // 名称搜索过滤（独立，不影响气泡图）
    if (props.searchName) {
        result = result.filter(d => d.code_id === props.searchName)
    }
    sortedData.value = result
    renderKey.value++
}

function toggleSort(key) {
    if (sortKey.value === key) {
        sortDesc.value = !sortDesc.value
    } else {
        sortKey.value = key
        sortDesc.value = key !== 'rank'
    }
    updateSort()
}

function sortArrow(key) {
    if (sortKey.value !== key) return ''
    return sortDesc.value ? ' ▼' : ' ▲'
}

// 拉取数据：不再自行发起无参请求。首页全量数据由 home-data-main 统一在 onMounted
// 中带参拉取（指标 + 默认筛选合并一次完成），此处仅消费共享 store 的数据。
onMounted(() => {
    updateSort()
})

// 定时刷新时自动重排序
watch(projectListData, () => {
    updateSort()
})

// 任何筛选条件变化时重新过滤
watch(
    () => [props.rankMin, props.rankMax, props.mcMin, props.mcMax, props.volMin, props.volMax, props.symbols, props.riseMin, props.searchName],
    () => { updateSort() }
)
</script>

<template>
    <div class="table-container">
        <!-- 标题栏 -->
        <div class="table-header">

        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <span>加载数据中...</span>
        </div>

        <!-- 空数据 -->
        <div v-else-if="projectListData.length === 0" class="empty-state">
            暂无项目数据
        </div>

        <!-- 表格 -->
        <div v-else class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th class="col-rank" @click="toggleSort('rank')">
                            排名<span class="sort-arrow">{{ sortArrow('rank') }}</span>
                        </th>
                        <th class="col-name">名称</th>
                        <th class="col-price">价格</th>
                        <th class="col-marketcap" @click="toggleSort('market_cap')">
                            市值<span class="sort-arrow">{{ sortArrow('market_cap') }}</span>
                        </th>
                        <th class="col-volume" @click="toggleSort('volume')">
                            24h成交量<span class="sort-arrow">{{ sortArrow('volume') }}</span>
                        </th>
                        <th
                            v-for="col in timeColumns"
                            :key="col.key"
                            class="col-pct"
                            @click="toggleSort(col.key)"
                        >
                            {{ col.label }}<span class="sort-arrow">{{ sortArrow(col.key) }}</span>
                        </th>
                    </tr>
                </thead>
                <tbody :key="'tb-' + renderKey">
                    <tr v-for="(item, idx) in sortedData" :key="item.code_id">
                        <!-- 排名 -->
                        <td class="col-rank">
                            <span class="rank-badge">{{ item.extra_info?.rank ?? idx + 1 }}</span>
                        </td>

                        <!-- 名称（点击跳转详情） -->
                        <td class="col-name name-link" @click.stop="goDetail(item)">
                            <span class="name-main">{{ item.name?.toUpperCase() || '' }}</span>
                            <span class="name-sub">{{ item.display_name || item.name }}</span>
                        </td>

                        <!-- 价格 -->
                        <td class="col-price">{{ formatPrice(item.price_dict?.spot) }}</td>

                        <!-- 市值 -->
                        <td class="col-marketcap">{{ formatMarketCap(item.market_cap_dict?.spot) }}</td>

                        <!-- 24h成交量 -->
                        <td class="col-volume">{{ formatVolume(item.volume_dict?.spot) }}</td>

                        <!-- 各时间维度涨幅 -->
                        <td
                            v-for="col in timeColumns"
                            :key="col.key"
                            class="col-pct"
                            :class="pctClass(item.extra_info?.performance?.[col.key])"
                        >
                            {{ formatPct(item.extra_info?.performance?.[col.key]) }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style scoped>
/* ---------- 全局底色 ---------- */
.table-container {
    width: 100%;
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: #0f1923;
    color: #c8d8e8;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    overflow: hidden;
}

/* ---------- 标题栏 ---------- */
.table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px 8px;
    flex-shrink: 0;
}

.table-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #e0edf5;
}

.refresh-btn {
    padding: 6px 18px;
    background: #1e3a5f;
    border: 1px solid #2a5a8f;
    border-radius: 6px;
    color: #c8d8e8;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
}

.refresh-btn:hover {
    background: #2a5a8f;
    color: #fff;
}

/* ---------- 加载 / 空状态 ---------- */
.loading-state,
.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: #8ba4be;
    font-size: 15px;
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

/* ---------- 滚动容器 ---------- */
.table-scroll {
    flex: 1;
    overflow: auto;
    padding: 0 16px 16px;
}

.table-scroll::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

.table-scroll::-webkit-scrollbar-track {
    background: transparent;
}

.table-scroll::-webkit-scrollbar-thumb {
    background: #1e3a5f;
    border-radius: 3px;
}

/* ---------- 表格 ---------- */
table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 13px;
    min-width: 1200px;
}

thead {
    position: sticky;
    top: 0;
    z-index: 2;
}

th {
    background: #0d1a26;
    padding: 30px 12px;
    text-align: center;
    vertical-align: bottom;
    font-weight: 600;
    color: #8ba4be;
    border-bottom: 2px solid #1e3a5f;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;
}

th:hover {
    color: #c8d8e8;
}

th .sort-arrow {
    font-size: 10px;
    color: #3b82c4;
    margin-left: 2px;
}

/* 左对齐的列 */
th.col-rank {
    position: sticky;
    left: -16px;   /* 吃掉 .table-scroll padding-left */
    z-index: 3;
    text-align: center;
    width: 40px;
}
th.col-name {
    position: sticky;
    left: 24px;    /* 40 - 16 */
    z-index: 3;
    max-width: 80px;
}

/* ---------- 行 ---------- */
tr {
    transition: background 0.15s;
}

td.name-link {
    cursor: pointer;
}

tbody tr:hover {
    background: rgba(30, 58, 95, 0.25);
}

tbody tr:nth-child(even) {
    background: rgba(255, 255, 255, 0.02);
}

tbody tr:nth-child(even):hover {
    background: rgba(30, 58, 95, 0.25);
}

/* ---------- 单元格 ---------- */
td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.4);
    white-space: nowrap;
}

/* 排名（冻结列） */
.col-rank {
    position: sticky;
    left: -16px;   /* 吃掉 .table-scroll padding-left */
    z-index: 1;
    background: #0f1923;
    text-align: center;
    border-right: 1px solid #1e3a5f;
}

.rank-badge {
    display: inline-block;
    color: #8ba4be;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

/* 名称（冻结列） */
.col-name {
    position: sticky;
    left: 24px;    /* 40 - 16 */
    z-index: 1;
    background: #0f1923;
    text-align: left;
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
    border-right: 1px solid #1e3a5f;
}

.name-main {
    display: block;
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.name-sub {
    display: block;
    font-size: 10px;
    color: #6a8aa8;
    margin-top: 1px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* 价格 / 市值 / 成交量 */
.col-price,
.col-marketcap,
.col-volume {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #e0edf5;
}

.col-volume {
    color: #8ba4be;
    font-size: 12px;
}

/* 涨幅列 */
.col-pct {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    min-width: 70px;
}

.col-pct.pct-up {
    color: #2ecc71;
}

.col-pct.pct-down {
    color: #e74c3c;
}

.col-pct.pct-zero {
    color: #8ba4be;
}
</style>
