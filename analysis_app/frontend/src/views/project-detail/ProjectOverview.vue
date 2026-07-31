<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useProjectData } from "@/composables/useProjectData"
import { useKlineData } from "./useKlineData"

const props = defineProps({
    codeId: { type: String, required: true },
})

// ==================== 项目信息（来自 Project 表共享数据） ====================
const { projectListData, fetchData } = useProjectData()
const project = computed(() =>
    projectListData.value.find(d => d.code_id === props.codeId) || null
)

// ==================== K 线数据（自身请求） ====================
const { stats, latestPrice, loadKline, startAutoRefresh, stop, bind } = useKlineData(() => props.codeId)
bind()

// 成交量 / 市值（优先 spot，兜底取第一个）
function pickFirst(dict) {
    if (!dict) return null
    if (dict.spot != null) return dict.spot
    const keys = Object.keys(dict)
    return keys.length ? dict[keys[0]] : null
}
const volume = computed(() => pickFirst(project.value?.volume_dict))
const marketCap = computed(() => pickFirst(project.value?.market_cap_dict))

// 最新价：优先 K 线，其次 Project 表
const latestPriceFinal = computed(() => latestPrice.value ?? project.value?.price_dict?.spot ?? null)

// ==================== 格式化 ====================
function formatPrice(v) {
    if (v == null || isNaN(v)) return '-'
    if (v >= 1) return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    return '$' + Number(v).toFixed(6)
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
    await fetchData()          // 拉取 Project 表（成交量/市值）
    startAutoRefresh()         // 请求 K 线并开启 60s 刷新
})
onUnmounted(() => {
    stop()
})
</script>

<template>
    <div class="overview-card">
        <div class="ov-price">
            <span class="ov-price-value">{{ formatPrice(latestPriceFinal) }}</span>
            <span class="ov-price-change" :class="pctClass(stats.changePct)">
                {{ formatPct(stats.changePct) }}
            </span>
        </div>
        <div class="ov-grid">
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
</template>

<style scoped>
.overview-card {
    background: rgba(13, 26, 38, 0.6);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 20px 24px;
}
.ov-price {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 18px;
}
.ov-price-value {
    font-size: 30px;
    font-weight: 700;
    color: #fff;
    font-variant-numeric: tabular-nums;
}
.ov-price-change {
    font-size: 15px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.ov-price-change.up { color: #2ecc71; }
.ov-price-change.down { color: #e74c3c; }

.ov-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}
.ov-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px 16px;
    background: rgba(15, 25, 35, 0.5);
    border-radius: 8px;
    border: 1px solid rgba(30, 58, 95, 0.5);
}
.ov-label {
    font-size: 12px;
    color: #6a8aa8;
}
.ov-value {
    font-size: 16px;
    font-weight: 700;
    color: #e0edf5;
    font-variant-numeric: tabular-nums;
}
.ov-value.up { color: #2ecc71; }
.ov-value.down { color: #e74c3c; }

@media (max-width: 700px) {
    .ov-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
