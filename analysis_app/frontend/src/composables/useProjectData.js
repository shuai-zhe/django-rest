import { ref } from 'vue'
import { ProjectList } from "@/utils/apis/project"

// 模块级单例——所有组件共享同一份数据
const projectListData = ref([])
const loading = ref(false)
const progress = ref(0)     // 0‑1, 平滑更新供进度条使用
let fetchPromise = null
let autoRefreshTimerId = null
let progressRafId = null
let refreshStartTime = null
let refreshIntervalMs = 60000
let refreshRefCount = 0     // 引用计数：多个组件启用时不会重复开定时器

export function useProjectData() {
    /**
     * 获取项目数据
     * @param {boolean} force  true=强制重新请求(用于后台刷新), false=有缓存时直接返回
     */
    const fetchData = (force = false) => {
        if (!force && projectListData.value.length > 0) return Promise.resolve(projectListData.value)
        if (fetchPromise) return fetchPromise

        loading.value = true
        fetchPromise = ProjectList()
            .then(res => {
                const raw = res.data || []
                projectListData.value = raw
                return raw
            })
            .catch(err => {
                console.error('获取项目数据失败:', err)
                throw err
            })
            .finally(() => {
                loading.value = false
                fetchPromise = null
            })
        return fetchPromise
    }

    // ==================== 60s 定时刷新 ====================

    /** 平滑更新 progress */
    function progressLoop() {
        if (refreshStartTime === null) return
        const elapsed = Date.now() - refreshStartTime
        progress.value = Math.min(elapsed / refreshIntervalMs, 1)
        progressRafId = requestAnimationFrame(progressLoop)
    }

    /**
     * 启动自动刷新（引用计数，可被多个组件安全调用）
     * @param {number} intervalMs  刷新间隔，默认 60000
     */
    const startAutoRefresh = (intervalMs = 60000) => {
        refreshRefCount++
        if (refreshRefCount > 1) return // 已有定时器在运行

        refreshIntervalMs = intervalMs
        refreshStartTime = Date.now()
        progress.value = 0

        progressRafId = requestAnimationFrame(progressLoop)

        autoRefreshTimerId = setInterval(() => {
            fetchData(true) // force = true，强制刷新
            refreshStartTime = Date.now()
        }, intervalMs)
    }

    /** 停止自动刷新（引用计数） */
    const stopAutoRefresh = () => {
        refreshRefCount--
        if (refreshRefCount > 0) return // 还有其他组件在使用
        if (progressRafId) {
            cancelAnimationFrame(progressRafId)
            progressRafId = null
        }
        if (autoRefreshTimerId) {
            clearInterval(autoRefreshTimerId)
            autoRefreshTimerId = null
        }
        refreshStartTime = null
        progress.value = 0
    }

    return {
        projectListData,
        loading,
        progress,
        fetchData,
        startAutoRefresh,
        stopAutoRefresh,
    }
}
