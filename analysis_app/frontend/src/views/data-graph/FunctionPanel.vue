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
import FilterPanel from "./FilterPanel.vue"

const props = defineProps({
    activeTimeFrame: { type: String, default: 'day' },
    modelValue:      { type: Object, default: () => ({}) },
})

const emit = defineEmits([
    'update:activeTimeFrame',
    'update:modelValue',
    'close',
])

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
</script>

<template>
    <div class="control-panel" @click.stop>
        <div class="cp-header">
            <span class="cp-title">功能</span>
            <button class="cp-close" type="button" @click="emit('close')">✕</button>
        </div>

        <div class="cp-body">
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
                            :class="['cp-tf-btn', { active: props.activeTimeFrame === opt.key }]"
                            @click="emit('update:activeTimeFrame', opt.key)"
                        >{{ opt.label }}</button>
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