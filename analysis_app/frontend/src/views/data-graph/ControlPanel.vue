<script setup>
/**
 * ControlPanel — 首页总控面板（独立组件）
 * 分类：
 *   主题  —— 深色 / 浅色
 *   数据源 —— 股票 / 货币
 *   导航  —— 新闻 / 行情首页（点击触发 navigate）
 *
 * 注：「默认时间维度 / 过滤」已拆分到独立的 FunctionPanel 组件（点击顶栏 [功能] 按钮触发），
 *     二者复用同一套 .control-panel / .cp-* 样式（全局，见本文件 <style>）。
 *
 * props:
 *   theme           主题 'dark' | 'light'
 *   dataType        数据源类型 'gate'(货币) | 'stock'(股票)
 * emits:
 *   update:theme / update:dataType / navigate(name) / close
 */
const props = defineProps({
    theme:    { type: String, default: 'dark' },
    dataType: { type: String, default: 'gate' },
})

const emit = defineEmits([
    'update:theme',
    'update:dataType',
    'navigate',
    'close',
])
</script>

<template>
    <div class="control-panel" @click.stop>
        <div class="cp-header">
            <span class="cp-title">控制面板</span>
            <button class="cp-close" type="button" @click="emit('close')">✕</button>
        </div>

        <div class="cp-body">
            <!-- ===== 主题 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    主题
                </h4>
                <div class="cp-field">
                    <span class="cp-label">外观</span>
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
            </section>

            <!-- ===== 数据源 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <ellipse cx="12" cy="5" rx="9" ry="3"/>
                        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                        <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
                    </svg>
                    数据源
                </h4>
                <div class="cp-field">
                    <span class="cp-label">类型</span>
                    <div class="cp-theme-switch">
                        <button
                            type="button"
                            :class="{ active: props.dataType === 'stock' }"
                            @click="emit('update:dataType', 'stock')"
                        >股票</button>
                       <button
                            type="button"
                            :class="{ active: props.dataType === 'future' }"
                            @click="emit('update:dataType', 'future')"
                        >期货</button>
                        <button
                            type="button"
                            :class="{ active: props.dataType === 'gate' }"
                            @click="emit('update:dataType', 'gate')"
                        >货币</button>
                    </div>
                </div>
            </section>

            <!-- ===== 导航 ===== -->
            <section class="cp-section">
                <h4 class="cp-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="3" width="7" height="7" rx="1"/>
                        <rect x="14" y="3" width="7" height="7" rx="1"/>
                        <rect x="3" y="14" width="7" height="7" rx="1"/>
                        <rect x="14" y="14" width="7" height="7" rx="1"/>
                    </svg>
                    导航
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

<style>
/* 全局通用控制面板样式：ControlPanel 与 FunctionPanel 共用 .control-panel / .cp-* 体系 */
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
.control-panel ::-webkit-scrollbar { width: 8px; height: 8px; }
.control-panel ::-webkit-scrollbar-track { background: transparent; }
.control-panel ::-webkit-scrollbar-thumb {
    background: #1e3a5f;
    border-radius: 4px;
}
.control-panel ::-webkit-scrollbar-thumb:hover { background: #2b5278; }

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
.cp-tf-btn.locked {
    opacity: 0.35;
    cursor: not-allowed;
    background: transparent;
    color: #5a708a;
    border-color: #1e3a5f;
}
.cp-tf-btn.locked:hover {
    border-color: #1e3a5f;
    color: #5a708a;
}

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
</style>
