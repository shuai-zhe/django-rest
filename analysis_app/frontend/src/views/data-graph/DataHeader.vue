<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useProjectData } from "@/composables/useProjectData"
import FilterPanel from "./FilterPanel.vue"

const props = defineProps({
    activeTimeFrame: { type: String, default: 'day' },
})

const emit = defineEmits([
    'update:rankMin', 'update:rankMax',
    'update:mcMin', 'update:mcMax',
    'update:volMin', 'update:volMax',
    'update:symbols', 'update:riseMin',
    'update:activeTimeFrame',
    'update:searchName',
    'viewDetail',
])

const { projectListData, progress } = useProjectData()
const remaining = computed(() => Math.ceil((1 - progress.value) * 60))

// 时间维度按钮配置
const timeFrameOptions = [
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

// ==================== 面板开关 ====================
const panelOpen = ref(false)

function togglePanel() { panelOpen.value = !panelOpen.value }
function closePanel()  { panelOpen.value = false }

// 点击外部关闭
function onDocClick(e) {
    if (panelOpen.value) closePanel()
}
function onResize() {
    if (window.innerWidth > 500) searchExpanded.value = false
}

onMounted(() => {
    document.addEventListener('click', onDocClick)
    document.addEventListener('click', onDocSearchClick)
    window.addEventListener('resize', onResize)
})
onUnmounted(() => {
    document.removeEventListener('click', onDocClick)
    document.removeEventListener('click', onDocSearchClick)
    window.removeEventListener('resize', onResize)
})

// ==================== 筛选状态 ====================
const filterState = reactive({
    rank:    { presetIdx: -1, customMin: 0, customMax: 250 },    // 默认自定义 0-250
    vol:     { presetIdx: -2, customMin: null, customMax: null },
    mc:      { presetIdx: -2, customMin: null, customMax: null },
    symbols: '',
    riseMin: null,
})

// ==================== 预设数据（用于解析） ====================
const rankPresets = [
    { min: 1,   max: 100 },
    { min: 101, max: 200 },
    { min: 201, max: 300 },
    { min: 301, max: 500 },
    { min: 501, max: 1000 },
    { min: 1001,max: Infinity },
]
const mcVolPresets = [
    { min: 0,          max: 100000 },
    { min: 0,          max: 1000000 },
    { min: 1000000,    max: 5000000 },
    { min: 5000000,    max: 10000000 },
    { min: 10000000,   max: 30000000 },
    { min: 30000000,   max: 60000000 },
    { min: 60000000,   max: 100000000 },
    { min: 100000000,  max: Infinity },
]

// ==================== 解析后的值 ====================
function resolveRank() {
    const r = filterState.rank
    if (r.presetIdx === -2) return { min: null, max: null } // 不限
    if (r.presetIdx >= 0) return { min: rankPresets[r.presetIdx].min, max: rankPresets[r.presetIdx].max }
    return { min: r.customMin ?? null, max: r.customMax ?? null }
}
function resolveVol() {
    const v = filterState.vol
    if (v.presetIdx === -2) return { min: null, max: null }
    if (v.presetIdx >= 0) return { min: mcVolPresets[v.presetIdx].min, max: mcVolPresets[v.presetIdx].max }
    return { min: v.customMin ?? null, max: v.customMax ?? null }
}
function resolveMc() {
    const m = filterState.mc
    if (m.presetIdx === -2) return { min: null, max: null }
    if (m.presetIdx >= 0) return { min: mcVolPresets[m.presetIdx].min, max: mcVolPresets[m.presetIdx].max }
    return { min: m.customMin ?? null, max: m.customMax ?? null }
}

function isSectionActive(section) {
    const s = filterState[section]
    if (s.presetIdx === -2) return false
    if (s.presetIdx >= 0) return true
    return s.customMin != null || s.customMax != null
}

// ==================== 监听变化 → 发射 resolved 值 ====================
watch(filterState, () => {
    const r = resolveRank();  emit('update:rankMin', r.min);   emit('update:rankMax', r.max)
    const v = resolveVol();   emit('update:volMin',  v.min);   emit('update:volMax',  v.max)
    const m = resolveMc();    emit('update:mcMin',   m.min);   emit('update:mcMax',   m.max)
    emit('update:symbols', filterState.symbols)
    emit('update:riseMin', filterState.riseMin)
}, { deep: true, immediate: true })

// ==================== 活跃筛选计数 ====================
const activeCount = computed(() => {
    let n = 0
    if (isSectionActive('rank')) n++
    if (isSectionActive('vol')) n++
    if (isSectionActive('mc')) n++
    if (filterState.symbols) n++
    if (filterState.riseMin != null) n++
    return n
})

// ==================== 名称搜索（独立，不影响气泡图） ====================
const searchQuery = ref('')
const selectedItem = ref(null)
const searchOpen = ref(false)
const searchExpanded = ref(false)  // 超窄屏展开状态

function expandSearch() {
    searchExpanded.value = true
    nextTick(() => {
        document.querySelector('.ns-input')?.focus()
    })
}

const searchResults = computed(() => {
    const data = projectListData.value || []
    const q = searchQuery.value.trim().toLowerCase()
    if (!q) {
        // 未输入时展示默认前 10 条（每次数据刷新同步更新）
        return data.slice(0, 10)
    }
    return data.filter(d => {
        const name = (d.name || '').toLowerCase()
        const displayName = (d.display_name || '').toLowerCase()
        return name.includes(q) || displayName.includes(q)
    }).slice(0, 50)
})

function selectSearchItem(item) {
    selectedItem.value = item
    searchQuery.value = item?.name?.toUpperCase() || ''
    searchOpen.value = false
    emit('update:searchName', item?.code_id || null)
    emit('viewDetail', item)  // 查看详情事件，暂时空处理
}

function clearSearch() {
    selectedItem.value = null
    searchQuery.value = ''
    searchOpen.value = false
    searchExpanded.value = false
    emit('update:searchName', null)
}

function closeSearch() { searchOpen.value = false }

// 下拉选项格式化
function formatOptPrice(v) {
    if (v == null) return '-'
    if (v >= 1e3) return '$' + (v / 1e3).toFixed(2) + 'K'
    if (v >= 1) return '$' + v.toFixed(2)
    return '$' + v.toFixed(4)
}
function formatOptChange(v) {
    if (v == null) return '-'
    const prefix = v >= 0 ? '+' : ''
    return prefix + v.toFixed(2) + '%'
}
function changeClass(v) {
    if (v == null) return ''
    return v > 0 ? 'chg-up' : v < 0 ? 'chg-down' : ''
}

// 输入无匹配结果时自动收起下拉
watch(searchResults, (r) => { if (r.length === 0 && searchQuery.value.trim()) searchOpen.value = false })

function onDocSearchClick(e) {
    const wrapper = document.querySelector('.name-search-wrapper')
    if (wrapper && !wrapper.contains(e.target)) {
        closeSearch()
        // 超窄屏展开状态下点击外部 → 收起
        if (searchExpanded.value && !selectedItem.value) {
            searchExpanded.value = false
        }
    }
}
</script>

<template>
    <div class="data-header">
        <div class="header-left">
            <span class="header-title">AI Trade</span>
        </div>

        <div class="header-center">
            <!-- 时间维度：宽屏按钮组 / 窄屏下拉框 -->
            <div class="timeframe-bar">
                <button
                    v-for="opt in timeFrameOptions"
                    :key="opt.key"
                    :class="['tf-btn', { active: props.activeTimeFrame === opt.key }]"
                    @click="emit('update:activeTimeFrame', opt.key)"
                >
                    {{ opt.label }}
                </button>
            </div>
            <select
                class="timeframe-select"
                :value="props.activeTimeFrame"
                @change="emit('update:activeTimeFrame', $event.target.value)"
            >
                <option
                    v-for="opt in timeFrameOptions"
                    :key="opt.key"
                    :value="opt.key"
                >
                    {{ opt.label }}
                </option>
            </select>

            <!-- 名称搜索（在筛选框旁边） -->
            <div class="name-search-wrapper" :class="{ 'ns-expanded': searchExpanded }" @click.stop>
                <!-- 超窄屏：未展开时的搜索按钮 -->
                <button class="ns-mobile-btn" @click.stop="expandSearch">
                    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor"
                        stroke-width="1.5" stroke-linecap="round">
                        <circle cx="6.5" cy="6.5" r="5"/>
                        <path d="M10.5 10.5L15 15"/>
                    </svg>
                </button>
                <!-- 展开后的搜索图标 -->
                <svg class="ns-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor"
                    stroke-width="1.5" stroke-linecap="round">
                    <circle cx="6.5" cy="6.5" r="5"/>
                    <path d="M10.5 10.5L15 15"/>
                </svg>
                <input
                    v-model="searchQuery"
                    class="ns-input"
                    type="text"
                    placeholder="搜索名称…"
                    @focus="searchOpen = true"
                />
                <button v-if="searchQuery" class="ns-clear" @click="clearSearch">×</button>
                <!-- 下拉 -->
                <div v-if="searchOpen && searchResults.length > 0" class="ns-dropdown">
                    <div
                        v-for="item in searchResults"
                        :key="item.code_id"
                        class="ns-option"
                        :class="{ active: selectedItem?.code_id === item.code_id }"
                        @click="selectSearchItem(item)"
                    >
                        <span class="ns-opt-rank">{{ item.extra_info?.rank ?? '-' }}</span>
                        <div class="ns-opt-info">
                            <span class="ns-opt-name">{{ item.name?.toUpperCase() }}</span>
                            <span class="ns-opt-disp">{{ item.display_name || item.name }}</span>
                        </div>
                        <div class="ns-opt-meta">
                            <span class="ns-opt-price">{{ formatOptPrice(item.price_dict?.spot) }}</span>
                            <span class="ns-opt-change" :class="changeClass(item.extra_info?.performance?.day)">{{ formatOptChange(item.extra_info?.performance?.day) }}</span>
                        </div>
                    </div>
                </div>
                <div v-else-if="searchOpen && searchQuery.trim() && searchResults.length === 0" class="ns-dropdown">
                    <div class="ns-empty">无匹配结果</div>
                </div>
            </div>
            <div class="filter-area">
                <button class="filter-btn" @click.stop="togglePanel">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M2 4h12M4 8h8M6 12h4"/>
                    </svg>
                    筛选
                    <span v-if="activeCount > 0" class="filter-badge">{{ activeCount }}</span>
                    <svg class="arrow" :class="{ open: panelOpen }" width="10" height="6" viewBox="0 0 10 6" fill="none"
                        stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
                        <path d="M1 1l4 4 4-4"/>
                    </svg>
                </button>
                <!-- 弹出面板 — 用 Object.assign 保持 reactive 代理 -->
                <FilterPanel
                    v-if="panelOpen"
                    :model-value="filterState"
                    @update:model-value="Object.assign(filterState, $event)"
                    @close="closePanel"
                    class="panel-instance"
                />
            </div>
        </div>

        <!-- 底部全宽进度条 -->
        <div class="header-progress">
            <div class="hp-track">
                <div class="hp-fill" :style="{ width: (progress * 100) + '%' }"></div>
            </div>
            <span class="hp-text">{{ remaining }}s</span>
        </div>
    </div>
</template>

<style scoped>
.data-header {
    position: fixed;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 52px;
    width: 100%;
    padding: 0 20px;
    background: rgba(13, 26, 38, 0.95);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid #1e3a5f;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    user-select: none;
    gap: 12px;
}

/* ---- 左：标题 ---- */
.header-left {
    flex-shrink: 0;
}
.header-title {
    font-size: 16px;
    font-weight: 700;
    color: #e0edf5;
    letter-spacing: 0.5px;
    white-space: nowrap;
}

/* ---- 中：筛选按钮 + 面板锚点 ---- */
.header-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    position: relative;
}

/* 时间维度按钮栏 — 分割线式按钮组 */
.timeframe-bar {
    display: flex;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    overflow: hidden;
}
.tf-btn {
    height: 32px;
    padding: 0 10px;
    border: none;
    border-right: 1px solid #1e3a5f;
    background: transparent;
    color: #8ba4be;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
    user-select: none;
    white-space: nowrap;
}
.tf-btn:last-child {
    border-right: none;
}
.tf-btn:hover {
    background: rgba(30, 58, 95, 0.5);
    color: #c8d8e8;
}
.tf-btn.active {
    background: #1e3a5f;
    color: #ffffff;
}

/* 窄屏下拉框 — 默认隐藏 */
.timeframe-select {
    display: none;
    height: 32px;
    padding: 0 8px;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    background: rgba(13, 26, 38, 0.95);
    color: #c8d8e8;
    font-size: 12px;
    font-family: inherit;
    cursor: pointer;
    outline: none;
}
.timeframe-select:focus {
    border-color: #3b82c4;
}

/* 筛选区域锚点 */
.filter-area {
    position: relative;
}

.filter-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 14px;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    background: rgba(15, 25, 35, 0.6);
    color: #8ba4be;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
}
.filter-btn:hover {
    border-color: #3b82c4;
    color: #c8d8e8;
    background: rgba(30, 58, 95, 0.3);
}
.filter-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 9px;
    background: #3b82c4;
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
}
.arrow {
    transition: transform 0.2s;
}
.arrow.open {
    transform: rotate(180deg);
}

/* ========== 底部全宽进度条 ========== */
.header-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 14px;
    display: flex;
    align-items: center;
    pointer-events: none;
}
.hp-track {
    flex: 1;
    height: 3px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
}
.hp-fill {
    height: 100%;
    background: linear-gradient(90deg, #1a5276, #3b82c4);
    transition: width 0.3s linear;
}
.hp-text {
    position: absolute;
    right: 20px;
    top: -14px;
    font-size: 10px;
    font-weight: 600;
    color: #6a8aa8;
    font-variant-numeric: tabular-nums;
}

/* ========== 名称搜索（右侧） ========== */
.name-search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    margin-right: 8px;
}
.ns-icon {
    position: absolute;
    left: 14px;
    color: #6a8aa8;
    pointer-events: none;
    z-index: 1;
}
.ns-input {
    width: 160px;
    height: 30px;
    padding: 0 34px 0 34px;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    background: rgba(15, 25, 35, 0.6);
    color: #c8d8e8;
    font-size: 12px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
}
.ns-input::placeholder { color: #6a8aa8; }
.ns-input:focus { border-color: #3b82c4; }
.ns-clear {
    position: absolute;
    right: 8px;
    width: 20px;
    height: 20px;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: #6a8aa8;
    font-size: 15px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
}
.ns-clear:hover { color: #c8d8e8; }

/* 超窄屏搜索按钮 — 桌面隐藏 */
.ns-mobile-btn {
    display: none;
}

/* 下拉 */
.ns-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    width: 400px;
    max-height: 600px;
    overflow-y: auto;
    background: #0d1a26;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    margin-top: 5px;
    z-index: 200;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);

}
.ns-option {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    cursor: pointer;
    transition: background 0.15s;
}
.ns-option:nth-child(n+2) { background: rgba(255, 255, 255, 0.02); }
.ns-option:hover { background: rgba(30, 58, 95, 0.4); }
.ns-option:hover .ns-opt-name,
.ns-option:hover .ns-opt-price { color: #d8e6f2; }
.ns-option.active { background: rgba(59, 130, 196, 0.2); }
.ns-option.active .ns-opt-name,
.ns-option.active .ns-opt-price { color: #e0edf5; }
.ns-option.active .ns-opt-disp { color: #8ba4be; }
.ns-option.active .ns-opt-rank { color: #8ba4be; }
.ns-opt-rank {
    width: 24px;
    text-align: center;
    font-size: 11px;
    font-weight: 700;
    color: #7a94af;
    flex-shrink: 0;
}
.ns-opt-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
}
.ns-opt-name {
    font-weight: 700;
    color: #c8d8e8;
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ns-opt-disp {
    color: #7a94af;
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ns-opt-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
    flex-shrink: 0;
    padding-right: 4px;
}
.ns-opt-price {
    font-size: 12px;
    color: #c8d8e8;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}
.ns-opt-change {
    font-size: 11px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: #8ba4be;
}
.ns-opt-change.chg-up { color: #2ecc71; }
.ns-opt-change.chg-down { color: #e74c3c; }
.ns-empty {
    padding: 14px;
    text-align: center;
    color: #6a8aa8;
    font-size: 12px;
}

/* ========== 响应式：窄屏隐藏按钮组，显示下拉框 ========== */
@media (max-width: 900px) {
    .timeframe-bar { display: none; }
    .timeframe-select { display: inline-block; }
}

/* ========== 超窄屏：搜索按钮 / 展开覆盖 ========== */
@media (max-width: 500px) {
    /* 未展开：所有元素正常显示，搜索只是一个图标按钮 */
    .name-search-wrapper {
        flex: initial;
    }
    .ns-mobile-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: 1px solid #1e3a5f;
        border-radius: 6px;
        background: rgba(15, 25, 35, 0.6);
        color: #8ba4be;
        cursor: pointer;
        transition: all 0.15s;
    }
    .ns-mobile-btn:hover {
        border-color: #3b82c4;
        color: #c8d8e8;
    }
    /* 未展开时隐藏输入框相关元素 */
    .name-search-wrapper:not(.ns-expanded) .ns-icon,
    .name-search-wrapper:not(.ns-expanded) .ns-input,
    .name-search-wrapper:not(.ns-expanded) .ns-clear,
    .name-search-wrapper:not(.ns-expanded) .ns-dropdown {
        display: none;
    }

    /* ===== 展开后：覆盖整个 header-center ===== */
    .header-center:has(.name-search-wrapper.ns-expanded) .timeframe-bar,
    .header-center:has(.name-search-wrapper.ns-expanded) .timeframe-select,
    .header-center:has(.name-search-wrapper.ns-expanded) .filter-area {
        display: none;
    }
    .name-search-wrapper.ns-expanded {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        flex: 1;
        background: rgba(13, 26, 38, 0.98);
        z-index: 110;
        padding: 0 16px;
    }
    .name-search-wrapper.ns-expanded .ns-mobile-btn {
        display: none;
    }
    .name-search-wrapper.ns-expanded .ns-icon {
        display: block;
        left: 22px;
        z-index: 2;
    }
    .name-search-wrapper.ns-expanded .ns-input {
        display: block;
        width: 100%;
        height: 36px;
        border: 1.5px solid #3b82c4;
        border-radius: 8px;
        background: rgba(15, 25, 35, 0.9);
        color: #e0edf5;
        font-size: 14px;
        padding: 0 42px 0 42px;
        outline: none;
        transition: border-color 0.2s, box-shadow 0.2s;
        box-shadow: 0 0 8px rgba(59, 130, 196, 0.25);
    }
    .name-search-wrapper.ns-expanded .ns-input:focus {
        border-color: #5ba3e8;
        box-shadow: 0 0 14px rgba(59, 130, 196, 0.4);
    }
    .name-search-wrapper.ns-expanded .ns-input::placeholder {
        color: #6a8aa8;
    }
    .name-search-wrapper.ns-expanded .ns-clear {
        display: flex;
        right: 22px;
        z-index: 2;
    }
    .name-search-wrapper.ns-expanded .ns-dropdown {
        display: block;
        width:350px;
        right: 20px;
        top: 30px;
        position: absolute;
        margin-top: 0;
    }


}
  .panel-instance {
    position: fixed;  /* 相对于浏览器窗口 */
    top: 50px;
    left: 20px;
    width: 100vw;
    height: 500px;
  }
</style>