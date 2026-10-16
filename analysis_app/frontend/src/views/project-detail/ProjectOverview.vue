<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useProjectData } from "@/composables/useProjectData"

const props = defineProps({
    codeId: { type: String, required: true },
})

// ==================== 项目信息（来自 Project 表共享数据） ====================
const { projectListData, fetchData, startAutoRefresh, stopAutoRefresh } = useProjectData('detail')
const project = computed(() =>
    projectListData.value.find(d => d.code_id === props.codeId) || null
)

// ==================== 24h 统计 ====================
// 不再自行请求 K 线，直接读取后端随 K 线请求回写的 extra_info.analysis
const analysis = computed(() => project.value?.extra_info?.analysis || {})
const stats = computed(() => ({
    high: analysis.value?.high_24h ?? null,
    low: analysis.value?.low_24h ?? null,
    changePct: analysis.value?.change_24h_pct ?? null,
}))

// 最新价：优先 analysis 中的最新价，其次 Project 表 spot 价
const latestPriceFinal = computed(
    () => analysis.value?.price ?? project.value?.price_dict?.spot ?? null
)

// 成交量 / 市值：优先后端 analysis（与图表口径一致），兜底 Project 表
function pickFirst(dict) {
    if (!dict) return null
    if (dict.spot != null) return dict.spot
    const keys = Object.keys(dict)
    return keys.length ? dict[keys[0]] : null
}
const volume = computed(() => analysis.value?.volume_24h ?? pickFirst(project.value?.volume_dict))
const marketCap = computed(() => analysis.value?.market_cap ?? pickFirst(project.value?.market_cap_dict))

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
function formatMoney(v) {
    if (v == null || isNaN(v)) return '-'
    if (v >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T'
    if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B'
    if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M'
    if (v >= 1e3) return '$' + (v / 1e3).toFixed(2) + 'K'
    return '$' + Number(v).toLocaleString('en-US')
}
function formatPct(v) {
    if (v == null || isNaN(v)) return '-'
    const prefix = v >= 0 ? '+' : ''
    return prefix + v.toFixed(2) + '%'
}
function pctClass(v) {
    if (v == null || isNaN(v)) return ''
    return v > 0 ? 'up' : v < 0 ? 'down' : ''
}

// ==================== 生命周期 ====================
onMounted(async () => {
    await fetchData(true, { code_id: props.codeId })   // 强制按 code_id 过滤请求该项目单条
    startAutoRefresh(10000, { code_id: props.codeId }) // 开启刷新，每 10s 拉取当前项目单条
})
onUnmounted(() => {
    stopAutoRefresh()
})
</script>

<template>
    <div class="overview-card">
        <!-- 两列布局：左 = 价格/涨幅，右 = 24h 数据（小字体） -->
        <div class="ov-cols">
            <!-- 第一列：价格 + 涨幅 -->
            <div class="ov-col col-price">
                <div class="ov-price">
                    <span class="ov-price-value">{{ formatPrice(latestPriceFinal) }}</span>
                    <span class="ov-price-change" :class="pctClass(stats.changePct)">
                        {{ formatPct(stats.changePct) }}
                    </span>
                </div>
            </div>

            <!-- 第二列：24h 数据（字体小一点） -->
            <div class="ov-col col-data">
                <div class="ov-item">
                    <span class="ov-label">24h 最高</span>
                    <span class="ov-value up">{{ formatPrice(stats.high) }}</span>
                </div>
                <div class="ov-item">
                    <span class="ov-label">24h 最低</span>
                    <span class="ov-value down">{{ formatPrice(stats.low) }}</span>
                </div>
                <div class="ov-item">
                    <span class="ov-label">24h 成交量</span>
                    <span class="ov-value">{{ formatMoney(volume) }}</span>
                </div>
                <div class="ov-item">
                    <span class="ov-label">市值</span>
                    <span class="ov-value">{{ formatMoney(marketCap) }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.overview-card {
    background: rgba(13, 26, 38, 0.6);
    border-radius: 10px;
    padding: 16px 24px;
}

/* 两列：左价格/涨幅（较宽），右 24h 数据（紧凑小字） */
.ov-cols {
    display: flex;
    align-items: center;
    gap: 24px;
}
.ov-col {
    flex: 1;
}
.col-price {
    flex: 1.2;
}
.col-data {
    display: flex;
    flex-direction: column;   /* 竖着排序 */
    gap: 8px;
    flex: 2;
}

.ov-price {
    display: flex;
    flex-direction: column;      /* 竖着排：价格在上，涨幅在下 */
    align-items: flex-start;
    gap: 4px;
}
.ov-price-value {
    font-size: 12px;
    font-weight: 700;
    color: #fff;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
}
.ov-price-change {
    font-size: 13px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    margin-left: 18px;           /* 向右缩进，形成右斜排 */
}
.ov-price-change.up { color: #2ecc71; }
.ov-price-change.down { color: #e74c3c; }

/* 24h 数据项：无边框、竖排；标签列固定宽度，数值紧跟 */
.ov-item {
    display: flex;
    align-items: baseline;
    gap: 8px;                        /* 标签与数值紧凑 */
    padding: 4px 0;
}
.ov-label {
    font-size: 12px;
    color: #6a8aa8;
    white-space: nowrap;
    width: 70px;                     /* 标签列固定 70px */
    overflow: hidden;
    text-overflow: ellipsis;
}
.ov-value {
    font-size: 12px;
    font-weight: 700;
    color: #e0edf5;
    font-variant-numeric: tabular-nums;
    text-align: left;                /* 数值靠左，紧跟标签 */
    white-space: nowrap;
}
.ov-value.up { color: #2ecc71; }
.ov-value.down { color: #e74c3c; }

/* 小屏幕：仍保持两列，仅缩小间距，price:data = 4:6
   注意：原比例 1.2:2≈37.5%:62.5%，4:6=40%:60%，视觉差异很小（仅 2.5%）
   本媒体查询基于视口宽度，需窗口/设备宽度 ≤ 700px 才会触发 */
@media (max-width: 700px) {
    .ov-cols {
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
    }
    .ov-cols .ov-col {
        flex: none !important;
    }
    .ov-cols .col-price {
        flex: 4 1 0 !important;
    }
    .ov-cols .col-data {
        flex: 6 1 0 !important;
    }
    .ov-cols .ov-price-value {
        font-size: 15px !important;
    }
}
</style>
