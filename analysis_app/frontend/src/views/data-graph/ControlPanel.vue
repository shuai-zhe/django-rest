<script setup>
/**
 * ControlPanel — 首页总控面板（独立组件）
 * 三大分类：
 *   设置  —— 默认时间维度、主题（深色/浅色，示例）
 *   过滤  —— 直接内嵌现有 FilterPanel（复用筛选逻辑）
 *   功能  —— 新闻 / 行情首页 等导航入口
 *
 * props:
 *   activeTimeFrame 当前时间维度 key
 *   modelValue      筛选状态对象（v-model，透传给 FilterPanel）
 *   theme           主题 'dark' | 'light'
 *   dataType        数据源类型 'gate'(货币) | 'stock'(股票)
 * emits:
 *   update:activeTimeFrame / update:modelValue / update:theme / update:dataType / navigate(name) / close
 */
import FilterPanel from "./FilterPanel.vue"

const props = defineProps({
    activeTimeFrame: { type: String, default: 'day' },
    modelValue:      { type: Object, default: () => ({}) },
    theme:           { type: String, default: 'dark' },
    dataType:        { type: String, default: 'gate' },
})

const emit = defineEmits([
    'update:activeTimeFrame',
    'update:modelValue',
    'update:theme',
    'update:dataType',
    'navigate',
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
            <span class="cp-title">控制面板</span>
            <button class="cp-close" type="button" @click="emit('close')">✕</button>
        </div>

        <div class="cp-body">
            <!-- ===== 设置 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    设置
                </h4>

                <div class="cp-field">
                    <span class="cp-label">默认时间维度</span>
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

                <div class="cp-field">
                    <span class="cp-label">主题</span>
                    <div class="cp-theme-switch">
                        <button
                            type="button"
                            :class="{ active: props.theme === 'dark' }"
                            @click="emit('update:theme', 'dark')"
                        >深色</button>
                        <button
                            type="button"
                            :class="{ active: props.theme === 'light' }"
                            @click="emit('update:theme', 'light')"
                        >浅色</button>
                    </div>
                </div>

                <div class="cp-field">
                    <span class="cp-label">数据源</span>
                    <div class="cp-theme-switch">
                        <button
                            type="button"
                            :class="{ active: props.dataType === 'stock' }"
                            @click="emit('update:dataType', 'stock')"
                        >股票</button>
                        <button
                            type="button"
                            :class="{ active: props.dataType === 'gate' }"
                            @click="emit('update:dataType', 'gate')"
                        >货币</button>
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

            <!-- ===== 功能 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="3" width="7" height="7" rx="1"/>
                        <rect x="14" y="3" width="7" height="7" rx="1"/>
                        <rect x="3" y="14" width="7" height="7" rx="1"/>
                        <rect x="14" y="14" width="7" height="7" rx="1"/>
                    </svg>
                    功能
                </h4>
                <div class="cp-nav-grid">
                    <button class="cp-nav-item" type="button" @click="emit('navigate', 'news')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 4h16v16H4z"/>
                            <path d="M8 8h8M8 12h8M8 16h5"/>
                        </svg>
                        <span>新闻</span>
                    </button>
                    <button class="cp-nav-item" type="button" @click="emit('navigate', 'home')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 11l9-8 9 8"/>
                            <path d="M5 10v10h14V10"/>
                        </svg>
                        <span>行情首页</span>
                    </button>
                </div>
            </section>
        </div>
    </div>
</template>

<style scoped>
.control-panel {
    position: fixed;
    top: 72px;
    left: 50%;
    right: auto;
    transform: translateX(-55%);
    display: block;
    box-sizing: border-box;
    width: 550px;
    max-width: 95vw;
    max-height: 78vh;
    overflow-y: auto;
    padding: 12px;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    background: rgba(13, 26, 38, 0.98);
    box-shadow: 0 16px 44px rgba(0, 0, 0, 0.5);
    z-index: 130;
    color: #c8d8e8;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
    scrollbar-width: thin;
    scrollbar-color: #1e3a5f transparent;
}
/* 滚动条与主题对齐 */
.control-panel::-webkit-scrollbar { width: 8px; height: 8px; }
.control-panel::-webkit-scrollbar-track { background: transparent; }
.control-panel::-webkit-scrollbar-thumb {
    background: #1e3a5f;
    border-radius: 4px;
}
.control-panel::-webkit-scrollbar-thumb:hover { background: #2b5278; }
.control-panel :deep(::-webkit-scrollbar) { width: 8px; height: 8px; }
.control-panel :deep(::-webkit-scrollbar-track) { background: transparent; }
.control-panel :deep(::-webkit-scrollbar-thumb) {
    background: #1e3a5f;
    border-radius: 4px;
}
.control-panel :deep(::-webkit-scrollbar-thumb:hover) { background: #2b5278; }

.cp-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 10px;
    margin-bottom: 6px;
    border-bottom: 1px solid #1e3a5f;
}
.cp-title {
    font-size: 14px;
    font-weight: 700;
    color: #e0edf5;
    letter-spacing: 0.5px;
}
.cp-close {
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 5px;
    background: transparent;
    color: #6f8bab;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.12s;
}
.cp-close:hover { background: rgba(30, 58, 95, 0.6); color: #fff; }

.cp-body { display: flex; flex-direction: column; gap: 4px; }

.cp-section { padding: 10px 2px; }
.cp-section + .cp-section { border-top: 1px dashed #1e3a5f; }

.cp-section-title {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0 0 10px;
    font-size: 12px;
    font-weight: 700;
    color: #7fa8d0;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

.cp-field {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}
.cp-field:last-child { margin-bottom: 0; }
.cp-label {
    flex: none;
    width: 76px;
    padding-top: 5px;
    font-size: 12px;
    color: #8ba4be;
}

/* 时间维度按钮组 */
.cp-tf-group {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}
.cp-tf-btn {
    height: 28px;
    padding: 0 9px;
    border: 1px solid #1e3a5f;
    border-radius: 5px;
    background: transparent;
    color: #8ba4be;
    font-size: 12px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
}
.cp-tf-btn:hover { border-color: #3b82c4; color: #c8d8e8; }
.cp-tf-btn.active { background: #1e3a5f; color: #fff; border-color: #2b5278; }

/* 主题开关 */
.cp-theme-switch {
    display: inline-flex;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    overflow: hidden;
}
.cp-theme-switch button {
    height: 28px;
    padding: 0 14px;
    border: none;
    background: transparent;
    color: #8ba4be;
    font-size: 12px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
}
.cp-theme-switch button + button { border-left: 1px solid #1e3a5f; }
.cp-theme-switch button:hover { color: #c8d8e8; }
.cp-theme-switch button.active { background: #1e3a5f; color: #fff; }

/* 功能导航网格 */
.cp-nav-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.cp-nav-item {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    height: 38px;
    border: 1px solid #1e3a5f;
    border-radius: 7px;
    background: rgba(15, 25, 35, 0.5);
    color: #c8d8e8;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
}
.cp-nav-item:hover {
    border-color: #3b82c4;
    background: rgba(30, 58, 95, 0.35);
    color: #fff;
}

/* 内嵌的 FilterPanel：去掉其外边距/标题冗余，作为卡片融入 */
.control-panel :deep(.filter-panel) {
    margin: 0;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    background: rgba(15, 25, 35, 0.45);
    box-shadow: none;
}
</style>
