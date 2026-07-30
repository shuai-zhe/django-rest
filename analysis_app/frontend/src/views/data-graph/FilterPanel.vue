<script setup>
/**
 * FilterPanel — 下拉筛选面板
 * 三列等宽：排名区间 / 交易量 / 市值
 * 底部：Symbol 搜索 + 涨幅阈值
 *
 * v-model 绑定 FilterState 对象：
 * {
 *   rank:    { presetIdx,  customMin, customMax }
 *   vol:     { presetIdx,  customMin, customMax }
 *   mc:      { presetIdx,  customMin, customMax }
 *   symbols: '',
 *   riseMin: null,
 * }
 * presetIdx = -1 表示自定义模式
 */
import { reactive, computed } from 'vue'
import { useProjectData } from "@/composables/useProjectData"

const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue', 'close'])

// ==================== 预设数据 ====================
const rankPresets = [
    { label: '1-100',       min: 1,   max: 100 },
    { label: '101-200',     min: 101, max: 200 },
    { label: '201-300',     min: 201, max: 300 },
    { label: '301-500',     min: 301, max: 500 },
    { label: '501-1000',    min: 501, max: 1000 },
    { label: '1000+',       min: 1001,max: Infinity },
]

const mcVolPresets = [
    { label: '<10万',        min: 0,          max: 100000 },
    { label: '<100万',       min: 0,          max: 1000000 },
    { label: '1-5百万',      min: 1000000,    max: 5000000 },
    { label: '5-10百万',     min: 5000000,    max: 10000000 },
    { label: '1-3千万',      min: 10000000,   max: 30000000 },
    { label: '3-6千万',      min: 30000000,   max: 60000000 },
    { label: '6-10千万',     min: 60000000,   max: 100000000 },
    { label: '>1亿',         min: 100000000,  max: Infinity },
]

// ==================== 本地状态 ====================
const local = reactive({
    rank:    { presetIdx: -1, customMin: 0, customMax: 250 },    // 默认自定义 0-250
    vol:     { presetIdx: -2, customMin: null, customMax: null },
    mc:      { presetIdx: -2, customMin: null, customMax: null },
    symbols: '',
    riseMin: null,
})

// 从 props 初始化
function initFromProps() {
    if (!props.modelValue) return
    local.rank    = { ...props.modelValue.rank }
    local.vol     = { ...props.modelValue.vol }
    local.mc      = { ...props.modelValue.mc }
    local.symbols = props.modelValue.symbols || ''
    local.riseMin = props.modelValue.riseMin ?? null
}
initFromProps()

// ==================== 帮助函数 ====================
function clamp(v, lo, hi) {
    if (v == null || v === '') return null
    const n = Number(v)
    return isNaN(n) ? null : Math.max(lo, Math.min(hi, n))
}

function emitChange() {
    emit('update:modelValue', {
        rank:    { ...local.rank },
        vol:     { ...local.vol },
        mc:      { ...local.mc },
        symbols: local.symbols,
        riseMin: local.riseMin,
    })
}

function selectPreset(section, idx) {
    local[section].presetIdx = idx
    local[section].customMin = null
    local[section].customMax = null
    emitChange()
}

function selectCustom(section) {
    local[section].presetIdx = -1
    emitChange()
}

function selectNone(section) {
    local[section].presetIdx = -2
    local[section].customMin = null
    local[section].customMax = null
    emitChange()
}

function updateCustom(section, field, val) {
    local[section][field] = val === '' ? null : Number(val)
    emitChange()
}

function handleReset() {
    local.rank    = { presetIdx: -1, customMin: 0, customMax: 250 }    // 恢复自定义 0-250
    local.vol     = { presetIdx: -2, customMin: null, customMax: null }
    local.mc      = { presetIdx: -2, customMin: null, customMax: null }
    local.symbols = ''
    local.riseMin = null
    emitChange()
}

// ==================== 当前激活的筛选标签 ====================
const activeTags = computed(() => {
    const tags = []
    // 排名
    const r = local.rank
    if (r.presetIdx >= 0 && r.presetIdx < rankPresets.length) {
        tags.push(rankPresets[r.presetIdx].label)
    } else if (r.presetIdx === -1 && (r.customMin != null || r.customMax != null)) {
        const lo = r.customMin ?? ''
        const hi = r.customMax ?? ''
        tags.push(`排名 ${lo}~${hi}`)
    }
    // 交易量
    const v = local.vol
    if (v.presetIdx >= 0 && v.presetIdx < mcVolPresets.length) {
        tags.push(mcVolPresets[v.presetIdx].label)
    } else if (v.presetIdx === -1 && (v.customMin != null || v.customMax != null)) {
        tags.push(`量 ${v.customMin??''}~${v.customMax??''}`)
    }
    // 市值
    const m = local.mc
    if (m.presetIdx >= 0 && m.presetIdx < mcVolPresets.length) {
        tags.push(mcVolPresets[m.presetIdx].label)
    } else if (m.presetIdx === -1 && (m.customMin != null || m.customMax != null)) {
        tags.push(`市值 ${m.customMin??''}~${m.customMax??''}`)
    }
    if (local.symbols) tags.push(local.symbols)
    if (local.riseMin != null) tags.push(`涨幅≥${local.riseMin}%`)
    return tags
})

// ==================== 交易所选项（从项目数据提取） ====================
const { projectListData } = useProjectData()

const exchangeOptions = computed(() => {
    const exchanges = new Set()
    for (const item of projectListData.value) {
        const syms = item.extra_info?.symbols
        if (syms) {
            for (const ex of Object.keys(syms)) {
                exchanges.add(ex)
            }
        }
    }
    return Array.from(exchanges).sort()
})

defineExpose({ activeTags, handleReset })
</script>

<template>
    <div class="filter-panel" @click.stop>
        <!-- 顶部标题栏 + 关闭 -->
        <div class="panel-header">
            <span class="panel-title">筛选条件</span>
            <button class="panel-close" @click="$emit('close')">✕</button>
        </div>

        <!-- 三列 -->
        <div class="panel-body">
            <!-- 1. 排名区间 -->
            <div class="panel-col">
                <div class="col-title">排名区间</div>
                <label class="preset-row" :class="{ active: local.rank.presetIdx === -2 }">
                    <input type="radio" :checked="local.rank.presetIdx === -2"
                        @change="selectNone('rank')" />
                    <span>不限</span>
                </label>
                <label
                    v-for="(p, i) in rankPresets"
                    :key="'r'+i"
                    class="preset-row"
                    :class="{ active: local.rank.presetIdx === i }"
                >
                    <input type="radio" :checked="local.rank.presetIdx === i"
                        @change="selectPreset('rank', i)" />
                    <span>{{ p.label }}</span>
                </label>
                <label class="preset-row" :class="{ active: local.rank.presetIdx === -1 }">
                    <input type="radio" :checked="local.rank.presetIdx === -1"
                        @change="selectCustom('rank')" />
                    <span>自定义</span>
                </label>
                <div class="custom-row" :class="{ disabled: local.rank.presetIdx !== -1 }">
                    <input type="number" class="ci" placeholder="最小"
                        :value="local.rank.customMin"
                        @input="updateCustom('rank', 'customMin', $event.target.value)"
                        :disabled="local.rank.presetIdx !== -1" />
                    <span class="ci-sep">—</span>
                    <input type="number" class="ci" placeholder="最大"
                        :value="local.rank.customMax"
                        @input="updateCustom('rank', 'customMax', $event.target.value)"
                        :disabled="local.rank.presetIdx !== -1" />
                </div>
            </div>

            <!-- 2. 交易量 -->
            <div class="panel-col">
                <div class="col-title">交易量</div>
                <label class="preset-row" :class="{ active: local.vol.presetIdx === -2 }">
                    <input type="radio" :checked="local.vol.presetIdx === -2"
                        @change="selectNone('vol')" />
                    <span>不限</span>
                </label>
                <label
                    v-for="(p, i) in mcVolPresets"
                    :key="'v'+i"
                    class="preset-row"
                    :class="{ active: local.vol.presetIdx === i }"
                >
                    <input type="radio" :checked="local.vol.presetIdx === i"
                        @change="selectPreset('vol', i)" />
                    <span>{{ p.label }}</span>
                </label>
                <label class="preset-row" :class="{ active: local.vol.presetIdx === -1 }">
                    <input type="radio" :checked="local.vol.presetIdx === -1"
                        @change="selectCustom('vol')" />
                    <span>自定义</span>
                </label>
                <div class="custom-row" :class="{ disabled: local.vol.presetIdx !== -1 }">
                    <input type="number" class="ci" placeholder="最小"
                        :value="local.vol.customMin"
                        @input="updateCustom('vol', 'customMin', $event.target.value)"
                        :disabled="local.vol.presetIdx !== -1" />
                    <span class="ci-sep">—</span>
                    <input type="number" class="ci" placeholder="最大"
                        :value="local.vol.customMax"
                        @input="updateCustom('vol', 'customMax', $event.target.value)"
                        :disabled="local.vol.presetIdx !== -1" />
                </div>
            </div>

            <!-- 3. 市值 -->
            <div class="panel-col">
                <div class="col-title">市值</div>
                <label class="preset-row" :class="{ active: local.mc.presetIdx === -2 }">
                    <input type="radio" :checked="local.mc.presetIdx === -2"
                        @change="selectNone('mc')" />
                    <span>不限</span>
                </label>
                <label
                    v-for="(p, i) in mcVolPresets"
                    :key="'m'+i"
                    class="preset-row"
                    :class="{ active: local.mc.presetIdx === i }"
                >
                    <input type="radio" :checked="local.mc.presetIdx === i"
                        @change="selectPreset('mc', i)" />
                    <span>{{ p.label }}</span>
                </label>
                <label class="preset-row" :class="{ active: local.mc.presetIdx === -1 }">
                    <input type="radio" :checked="local.mc.presetIdx === -1"
                        @change="selectCustom('mc')" />
                    <span>自定义</span>
                </label>
                <div class="custom-row" :class="{ disabled: local.mc.presetIdx !== -1 }">
                    <input type="number" class="ci" placeholder="最小"
                        :value="local.mc.customMin"
                        @input="updateCustom('mc', 'customMin', $event.target.value)"
                        :disabled="local.mc.presetIdx !== -1" />
                    <span class="ci-sep">—</span>
                    <input type="number" class="ci" placeholder="最大"
                        :value="local.mc.customMax"
                        @input="updateCustom('mc', 'customMax', $event.target.value)"
                        :disabled="local.mc.presetIdx !== -1" />
                </div>
            </div>
        </div>

        <!-- 底部：Symbol + 涨幅 + 重置 -->
        <div class="panel-footer">
            <div class="footer-item">
                <label class="footer-label">交易所</label>
                <select class="footer-select"
                    :value="local.symbols"
                    @change="local.symbols = $event.target.value; emitChange()">
                    <option value="">不限</option>
                    <option v-for="ex in exchangeOptions" :key="ex" :value="ex">{{ ex }}</option>
                </select>
            </div>
            <div class="footer-item footer-narrow">
                <label class="footer-label">涨幅 ≥</label>
                <input type="number" class="footer-input footer-input-sm" placeholder="%"
                    :value="local.riseMin"
                    @input="local.riseMin = $event.target.value === '' ? null : Number($event.target.value); emitChange()"
                    min="0" />
            </div>
            <button class="confirm-btn" @click="$emit('close')">确定</button>
            <button class="reset-btn" @click="handleReset">重置</button>
        </div>
    </div>
</template>

<style scoped>
/* ========== 面板容器 ========== */
.filter-panel {

    width: 90vw;
    max-width: 720px;

    background: #0d1a26;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    padding: 16px 16px 12px;
    z-index: 200;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
}

/* ========== 面板标题栏 ========== */
.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}
.panel-title {
    font-size: 14px;
    font-weight: 700;
    color: #c8d8e8;
}
.panel-close {
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #6a8aa8;
    font-size: 15px;
    cursor: pointer;
    transition: all 0.15s;
}
.panel-close:hover {
    background: rgba(180, 60, 60, 0.2);
    color: #e08080;
}

/* ========== 三列 ========== */
.panel-body {
    display: flex;
    gap: 12px;
}
.panel-col {
    flex: 1;
    min-width: 0;
    border-right: 1px solid #152a3a;
    padding-right: 12px;
}
.panel-col:last-child {
    border-right: none;
    padding-right: 0;
}
.col-title {
    font-size: 13px;
    font-weight: 700;
    color: #c8d8e8;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e3a5f;
}

/* ========== 预设行 ========== */
.preset-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.12s;
    font-size: 12px;
    color: #8ba4be;
}
.preset-row:hover {
    background: rgba(30, 58, 95, 0.4);
}
.preset-row.active {
    background: rgba(59, 130, 196, 0.15);
    color: #c8d8e8;
}
.preset-row input[type="radio"] {
    appearance: none;
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    border: 2px solid #2a4a6a;
    border-radius: 50%;
    flex-shrink: 0;
    cursor: pointer;
    transition: all 0.15s;
}
.preset-row input[type="radio"]:checked {
    border-color: #3b82c4;
    background: #3b82c4;
    box-shadow: inset 0 0 0 3px #0d1a26;
}

/* ========== 自定义行 ========== */
.custom-row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 6px;
    padding: 0 6px 4px;
    transition: opacity 0.15s;
}
.custom-row.disabled {
    opacity: 0.3;
    pointer-events: none;
}
.ci {
    width: 0;
    flex: 1;
    height: 26px;
    padding: 0 6px;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    background: #0a1520;
    color: #c8d8e8;
    font-size: 12px;
    text-align: center;
    outline: none;
    transition: border-color 0.2s;
}
.ci:focus {
    border-color: #3b82c4;
}
.ci::-webkit-inner-spin-button,
.ci::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.ci-sep {
    color: #4a6a8a;
    font-size: 12px;
    flex-shrink: 0;
}

/* ========== 底部 ========== */
.panel-footer {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #1e3a5f;
}
.footer-item {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
}
.footer-narrow {
    flex: 0 0 120px;
}
.footer-label {
    font-size: 12px;
    color: #8ba4be;
    white-space: nowrap;
}
.footer-input {
    flex: 1;
    height: 30px;
    padding: 0 10px;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    background: #0a1520;
    color: #c8d8e8;
    font-size: 12px;
    outline: none;
    transition: border-color 0.2s;
}
.footer-input:focus {
    border-color: #3b82c4;
}
.footer-input-sm {
    width: 70px;
    flex: none;
    text-align: center;
}
.footer-input::-webkit-inner-spin-button,
.footer-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.footer-select {
    flex: 1;
    height: 30px;
    padding: 0 8px;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    background: #0a1520;
    color: #c8d8e8;
    font-size: 12px;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s;
    min-width: 0;
}
.footer-select:focus {
    border-color: #3b82c4;
}
.footer-select option {
    background: #0d1a26;
    color: #c8d8e8;
}
.reset-btn {
    flex-shrink: 0;
    height: 30px;
    padding: 0 14px;
    border: 1px solid #3a2a2a;
    border-radius: 4px;
    background: transparent;
    color: #b07a7a;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
}
.reset-btn:hover {
    background: rgba(180, 60, 60, 0.15);
    border-color: #8a3a3a;
    color: #e08080;
}
.confirm-btn {
    flex-shrink: 0;
    height: 30px;
    padding: 0 20px;
    border: 1px solid #2a5a8f;
    border-radius: 4px;
    background: #1a3a5f;
    color: #c8d8e8;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
}
.confirm-btn:hover {
    background: #2a5a8f;
    border-color: #3b82c4;
    color: #fff;
}

/* ========== 窄屏适配 ========== */
@media (max-width: 1400px) {
    .filter-panel {
        width: 300px;
    }
    .panel-footer {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 8px 12px;
    }
    .confirm-btn,
    .reset-btn {
        width: 100%;
    }
}

@media (max-width: 600px) {
    .filter-panel {
        width: calc(100vw - 24px);
        max-width: 340px;
        padding: 12px 10px 10px;
    }

    .panel-header {
        margin-bottom: 8px;
    }
    .panel-title {
        font-size: 13px;
    }

    .panel-body {
        gap: 6px;
    }
    .panel-col {
        padding-right: 6px;
    }
    .panel-col:last-child {
        padding-right: 0;
    }
    .col-title {
        font-size: 11px;
        margin-bottom: 4px;
        padding-bottom: 4px;
    }

    .preset-row {
        padding: 2px 4px;
        font-size: 11px;
        gap: 4px;
    }
    .preset-row input[type="radio"] {
        width: 12px;
        height: 12px;
    }
    .preset-row input[type="radio"]:checked {
        box-shadow: inset 0 0 0 2px #0d1a26;
    }

    .custom-row {
        padding: 0 4px 2px;
        gap: 2px;
        margin-top: 2px;
    }
    .ci {
        height: 22px;
        font-size: 11px;
        padding: 0 4px;
    }
    .ci-sep {
        font-size: 11px;
    }

    .panel-footer {
        padding-top: 8px;
        margin-top: 8px;
        gap: 6px;
    }
    .footer-label {
        font-size: 11px;
    }
    .footer-input,
    .footer-select {
        height: 26px;
        font-size: 11px;
    }
    .footer-narrow {
        flex: 0 0 90px;
    }
    .reset-btn,
    .confirm-btn {
        height: 26px;
        font-size: 11px;
        padding: 0 12px;
    }
}
</style>
