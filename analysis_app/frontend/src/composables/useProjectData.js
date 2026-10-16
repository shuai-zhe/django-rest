import { ref } from 'vue'
import { ProjectList } from "@/utils/apis/project"

/**
 * 按作用域隔离的数据实例池。
 * 首页（气泡图 / 表格 / 头部 / 筛选面板）共享同一个 'home' 实例（全量数据），
 * 详情页（容器 / 概览）共享同一个 'detail' 实例（按 code_id 拉取的单条），
 * 两者完全独立，详情页拉单条不会污染首页全量数据，反之亦然。
 */
const stores = {}

// ==================== 全局数据源类型（跨作用域共享） ====================
// 持久化到 localStorage，刷新页面后仍记住上次选择（仅 'gate' / 'stock' 合法）
const STORAGE_KEY = 'global_data_type'
const _savedType = (() => {
    try {
        const v = localStorage.getItem(STORAGE_KEY)
        return v === 'gate' || v === 'stock' || v ==="future" ? v : 'gate'
    } catch {
        return 'gate'
    }
})()
const globalDataType = ref(_savedType)   // 'gate'=货币, 'stock'=股票 , 'future'=期货
function createStore() {
    const projectListData = ref([])
    const loading = ref(false)
    const progress = ref(0)     // 0‑1, 平滑更新供进度条使用

    // 以下状态均按 scope 独立，互不干扰
    let fetchPromise = null
    let autoRefreshTimerId = null
    let progressRafId = null
    let refreshStartTime = null
    let refreshIntervalMs = 60000
    let refreshRefCount = 0     // 引用计数：同作用域内多个组件启用时不会重复开定时器
    let refreshParams = {}      // 自动刷新时透传给后端的查询参数（如 { code_id } / { id }）

    const fetchData = (force = false, params = {}) => {
        const hasParams = Object.keys(params || {}).length > 0
        // 仅在没有显式参数且已有缓存时直接返回，避免带参请求被无参缓存拦截
        if (!force && !hasParams && projectListData.value.length > 0) return Promise.resolve(projectListData.value)
        if (fetchPromise && !force) return fetchPromise

        loading.value = true
        fetchPromise = ProjectList(params, globalDataType.value)
            .then(res => {
                // 无论带参与否，都整体替换本作用域的数据（各作用域独立，无需 upsert）
                projectListData.value = res.data || []
                return projectListData.value
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

    // ==================== 定时刷新 ====================

    /** 平滑更新 progress */
    function progressLoop() {
        if (refreshStartTime === null) return
        const elapsed = Date.now() - refreshStartTime
        progress.value = Math.min(elapsed / refreshIntervalMs, 1)
        progressRafId = requestAnimationFrame(progressLoop)
    }

    /**
     * 启动自动刷新（同作用域内引用计数，可被多个组件安全调用）
     * @param {number} intervalMs  刷新间隔，默认 60000
     * @param {object|function} params  刷新时透传给后端的查询参数；
     *        可为对象（固定参数）或函数（每次刷新重新计算，确保筛选变化后刷新仍带最新筛选）
     */
    const startAutoRefresh = (intervalMs = 60000, params = {}) => {
        refreshRefCount++
        if (refreshRefCount > 1) return // 已有定时器在运行
        refreshParams = params || {}

        refreshIntervalMs = intervalMs
        refreshStartTime = Date.now()
        progress.value = 0

        progressRafId = requestAnimationFrame(progressLoop)

        autoRefreshTimerId = setInterval(() => {
            // params 为函数时每次重新计算，避免拿到过期的筛选条件
            const p = typeof refreshParams === 'function' ? refreshParams() : refreshParams
            fetchData(true, p) // force = true，强制刷新；带参数则只刷新指定项目
            refreshStartTime = Date.now()
        }, intervalMs)
    }

    /** 停止自动刷新（同作用域引用计数） */
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
        refreshParams = {}
    }

    // 暴露 currentRefreshParams 供外部查看当前刷新参数（调试用，可选）
    function getCurrentRefreshParams() {
        return typeof refreshParams === 'function' ? refreshParams() : refreshParams
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

/**
 * 切换数据源类型（'gate'=货币, 'stock'=股票），全局生效。
 * 更新全局 dataType 后，强制重新拉取【所有已激活作用域】的数据，
 * 首页与详情页（列表 + 自动刷新）都会跟随切换。
 */
function setDataType(type) {
    if (type === globalDataType.value) return Promise.resolve()
    globalDataType.value = type
    // 持久化到 localStorage，刷新后保持上次选择
    try {
        localStorage.setItem(STORAGE_KEY, type)
    } catch {
        // 忽略隐私模式等写入失败，不影响内存态
    }
    const tasks = []
    for (const key of Object.keys(stores)) {
        tasks.push(stores[key].fetchData(true))
    }
    return Promise.all(tasks)
}

/**
 * 获取（或创建）某作用域的项目数据实例。
 * @param {string} scope 作用域标识：'home' = 首页全量数据，'detail' = 详情页单条数据
 */
export function useProjectData(scope = 'home') {
    if (!stores[scope]) stores[scope] = createStore()
    // HMR / 版本兼容：若已缓存的旧实例缺少 fetchData 等核心方法，
    // 丢弃旧实例重建，避免调用时报 "xxx is not a function"
    if (typeof stores[scope].fetchData !== 'function') {
        stores[scope] = createStore()
    }
    return stores[scope]
}

/** 全局数据源类型（响应式 ref，所有组件共享只读引用） */
export function useGlobalDataType() {
    return globalDataType
}

export { setDataType }

// Vite HMR：热更新时清空单例池，确保下次调用重建为最新版本
if (import.meta.hot) {
    import.meta.hot.dispose(() => {
        for (const key of Object.keys(stores)) delete stores[key]
    })
}