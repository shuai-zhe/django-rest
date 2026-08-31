<script setup>
/**
 * FunctionPanel — 功能面板（独立组件）
 * 复用 ControlPanel 的 .control-panel / .cp-* 全局样式体系（见 ControlPanel.vue）。
 * 内容承载：
 *   默认时间维度 —— 时间维度按钮组
 *   过滤         —— 内嵌现有 FilterPanel（复用筛选逻辑）
 *
 * props:
 *   activeTimeFrame 当前时间维度 key
 *   modelValue      筛选状态对象（v-model，透传给 FilterPanel）
 * emits:
 *   update:activeTimeFrame / update:modelValue / close
 */
import { computed, ref, watch, onUnmounted } from "vue"
import FilterPanel from "./FilterPanel.vue"
import { useGlobalDataType } from "@/composables/useProjectData"

const props = defineProps({
    activeTimeFrame: { type: String, default: 'day' },
    // metric 为通配符 DSL 数组，例如 [{ op:'eq', field:'metric', value:'abs', type:'metric' }]
    metric:          { type: Array, default: () => [] },
    modelValue:      { type: Object, default: () => ({}) },
})

const emit = defineEmits([
    'update:activeTimeFrame',
    'update:modelValue',
    'update:metric',
    'close',
])

// 指标栏默认选中「绝对涨幅」，构造为通配符条件（key 拼接 performance__<时间维度>）
// 默认值跟随当前时间维度，避免排序/筛选一直锁定在 day
const DEFAULT_METRIC = { op: 'eq', key: `performance__${props.activeTimeFrame}`, value: 'abs', type: 'metric' }
// 当前选中态（通配符 DSL 数组，受控于父级 metric prop，保证刷新/切换数据源后同步）
const activeMetric = ref(props.metric.length ? [...props.metric] : [DEFAULT_METRIC])

// 全局数据源类型（gate=货币 / stock=股票）
const dataType = useGlobalDataType()
// 股票模式下仅允许「日」级别：其它时间维度静止（不可点击）
const timeFrameLocked = computed(() => dataType.value === 'stock')

// ===== 指标栏（可扩展，单选通配符模式）=====
// 每个选项对应一个通配符条件：{ op, key, value, type }
// 与 home-data-main 的过滤 DSL 同构（type:'metric'），涨幅 key 规则统一为 performance__<时间维度>，
// 与「涨幅 ≥」过滤复用同一拼接逻辑。
// value 对应后端 metric 参数：abs=绝对涨幅 / positive=正涨幅 / negative=负涨幅
// 后续新增指标只需在此数组追加一项即可
// 注意：涨幅指标互斥，仅允许单选（点击即替换，不追加、不取消）
const metricOptions = [
    { key: 'abs',      label: '绝对涨幅' },
    { key: 'positive', label: '正涨幅' },
    { key: 'negative', label: '负涨幅' },
]
// 当前选中的 value 集合（用于模板高亮判断）
const selectedMetricKeys = computed(() => activeMetric.value.map((m) => m.value))
// 构造指标/排序条件：与过滤 DSL 同构，key 拼接 performance__<时间维度>
function buildMetricCondition(metricKey, timeFrame) {
    return { op: 'eq', key: `performance__${timeFrame}`, value: metricKey, type: 'metric' }
}
// 点击切换选中态（单选通配符模式）：直接替换为当前选项，不追加/不取消
function onMetricClick(opt) {
    const next = buildMetricCondition(opt.key, props.activeTimeFrame)
    activeMetric.value = [next]
    emit('update:metric', [next])
}
// 父级 metric 变化（如切换数据源重置）同步到本地选中态
watch(() => props.metric, (v) => { activeMetric.value = [...v] }, { deep: true })

// 时间维度选项（与 DataHeader 保持一致）
const timeFrameOptions = [
    { key: 'min1',   label: '1分钟' },
    { key: 'min5',   label: '5分钟' },
    { key: 'min15',  label: '15分钟' },
    { key: 'hour',   label: '1小时' },
    { key: 'hour4',  label: '4小时' },
    { key: 'day',    label: '日' },
    { key: 'week',   label: '周' },
    { key: 'month',  label: '月' },
    { key: 'month3', label: '3月' },
    { key: 'year',   label: '年' },
]

// 锁定提示：股票模式下点击/悬浮被禁用的时间维度时给出说明
const lockHint = ref(false)
let lockHintTimer = null
function showLockHint() {
    if (!timeFrameLocked.value) return
    lockHint.value = true
    if (lockHintTimer) clearTimeout(lockHintTimer)
    lockHintTimer = setTimeout(() => { lockHint.value = false }, 1600)
}
function onTfClick(opt) {
    if (timeFrameLocked.value && opt.key !== 'day') {
        showLockHint()
        return
    }
    emit('update:activeTimeFrame', opt.key)
}
onUnmounted(() => { if (lockHintTimer) clearTimeout(lockHintTimer) })
</script>

<template>
    <div class="control-panel" @click.stop>
        <div class="cp-header">
            <span class="cp-title">功能</span>
            <button class="cp-close" type="button" @click="emit('close')">✕</button>
        </div>

        <div class="cp-body">
            <!-- ===== 指标栏（可扩展） ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 17l6-6 4 4 8-8"/>
                        <path d="M21 7v6h-6"/>
                    </svg>
                    指标
                </h4>
                <div class="cp-field">
                    <div class="cp-metric-group">
                        <button
                            v-for="opt in metricOptions"
                            :key="opt.key"
                            type="button"
                            :class="['cp-metric-btn', { active: selectedMetricKeys.includes(opt.key) }]"
                            @click="onMetricClick(opt)"
                        >{{ opt.label }}</button>
                    </div>
                </div>
            </section>

            <!-- ===== 默认时间维度 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="9"/>
                        <path d="M12 7v5l3 2"/>
                    </svg>
                    默认时间维度
                </h4>
                <div class="cp-field">
                    <div class="cp-tf-group">
                        <button
                            v-for="opt in timeFrameOptions"
                            :key="opt.key"
                            type="button"
                            :class="['cp-tf-btn', { active: props.activeTimeFrame === opt.key, locked: timeFrameLocked && opt.key !== 'day' }]"
                            @click="onTfClick(opt)"
                            @mouseenter="showLockHint"
                        >{{ opt.label }}</button>
                        <!-- 锁定提示：股票模式仅支持「日」级别 -->
                        <transition name="lockhint">
                            <span v-if="lockHint" class="cp-tf-lockhint">股票模式仅支持「日」级别</span>
                        </transition>
                    </div>
                </div>
            </section>

            <!-- ===== 过滤 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor"
                        stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M2 4h12M4 8h8M6 12h4"/>
                    </svg>
                    过滤
                </h4>
                <!-- 内嵌现有筛选面板（普通卡片形式，非浮层） -->
                <FilterPanel
                    :model-value="props.modelValue"
                    @update:model-value="emit('update:modelValue', $event)"
                />
            </section>
        </div>
    </div>
</template>

<style scoped>
/* ===== 指标栏按钮组（复用时间维度按钮视觉） ===== */
.cp-metric-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.cp-metric-btn {
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid #2b3f52;
    background: #16242f;
    color: #9fb3c8;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
}
.cp-metric-btn:hover {
    border-color: #3a6ea5;
    color: #cfe3f5;
}
.cp-metric-btn.active {
    background: #1f6feb;
    border-color: #1f6feb;
    color: #fff;
    box-shadow: 0 2px 8px rgba(31, 111, 235, 0.35);
}

/* 锁定提示浮层（股票模式禁用时间维度时） */
.cp-tf-group {
    position: relative;
}
.cp-tf-lockhint {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);
    white-space: nowrap;
    padding: 6px 12px;
    border-radius: 6px;
    background: rgba(20, 32, 44, 0.96);
    border: 1px solid #2b5278;
    color: #e0edf5;
    font-size: 12px;
    line-height: 1;
    pointer-events: none;
    z-index: 30;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
}
.cp-tf-lockhint::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-top-color: #2b5278;
}
.lockhint-enter-active,
.lockhint-leave-active {
    transition: opacity 0.18s ease, transform 0.18s ease;
}
.lockhint-enter-from,
.lockhint-leave-to {
    opacity: 0;
    transform: translateX(-50%) translateY(4px);
}
</style>