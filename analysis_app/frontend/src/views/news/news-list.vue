<script setup>
import { useRouter } from 'vue-router'
import NewsList from "@/views/project-detail/NewsList.vue"

const router = useRouter()

function goBack() {
    router.push('/')
}
</script>

<template>
    <div class="news-page">
        <!-- 顶部导航 -->
        <div class="np-header">
            <button class="back-btn" @click="goBack" title="返回" aria-label="返回">
                <svg viewBox="0 0 24 24" width="20" height="20"><path d="M15 5l-7 7 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
            </button>
            <span class="np-title">新闻资讯</span>
        </div>

        <!-- 主体：最大宽度居中，完整模式（含搜索栏 + 分页） -->
        <div class="np-body">
            <NewsList :compact="false" :page-size="10" title="全部新闻" />
        </div>
    </div>
</template>

<style scoped>
.news-page {
    min-height: 100vh;
    background: #0f1923;
    color: #c8d8e8;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
}
.np-header {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 56px;
    padding: 0 24px;
    background: rgba(13, 26, 38, 0.95);
    border-bottom: 1px solid #1e3a5f;
    position: sticky;
    top: 0;
    z-index: 10;
}
.back-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 50%;
    color: #c8d8e8;
    cursor: pointer;
    transition: all 0.2s;
}
.back-btn:hover {
    background: rgba(30, 58, 95, 0.7);
    color: #fff;
}
.np-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
}
.np-body {
    max-width: 960px;
    margin: 24px auto;
    padding: 0 16px;
}
</style>
