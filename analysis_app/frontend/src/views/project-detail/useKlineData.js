import { ref, computed, watch } from 'vue'
import { ProjectKline } from "@/utils/apis/project"

// ==================== 时间窗口校验（柱子数上限） ====================
// 与后端 KlineInterval 对齐：interval 字符串 -> 秒
export const INTERVAL_SECONDS = {
    '1s': 1, '10s': 10, '1m': 60, '5m': 300, '15m': 900,
    '30m': 1800, '1h': 3600, '4h': 14400, '8h': 28800,
    '1d': 86400, '7d': 604800, '3d': 2592000,
}
export const MAX_BARS = 1000

/**
 * 校验/修正 K 线时间窗口，保证柱子数不超过 MAX_BARS。
 * 前端只下发 to_date（由后端按 limit/柱子数约束返回数据），故这里不返回 from_date。
 * @param {{ interval?: string, to_date?: string|number }} opts
 * @returns {{ bars: number, params: { to_date: string } }}
 */
export function validateKlineWindow({ interval = '1m', to_date }) {
    const stepSec = INTERVAL_SECONDS[interval] ?? 60
    const to = to_date != null ? Number(to_date) : Math.floor(Date.now() / 1000)
    // 基于 to_date 反推柱子数（用于校验提示；真正裁剪由后端 limit 决定）
    const from = to - MAX_BARS * stepSec
    const bars = Math.floor((to - from) / stepSec)
    return { bars, params: { to_date: String(to) } }
}

/**
 * 构建 K 线请求参数：仅 code_id / interval / to_date，不含 from_date。
 * 由后端按柱子数上限（limit）决定返回数量。
 */
export function buildKlineParams({ code_id, interval = '1m', to_date }) {
    const { bars, params } = validateKlineWindow({ interval, to_date })
    if (bars > MAX_BARS) {
        console.warn(`[K线] 窗口估计超过 ${MAX_BARS} 根柱子，返回数量以后端 limit 为准（interval=${interval}）`)
    }
    return { code_id, interval, ...params }
}

/**
 * 项目 K 线数据组合式函数（独立封装，供 project-detail 子组件使用）
 * - 按 codeId:interval 模块级缓存，多个子组件共享同一份数据，避免重复请求
 * - 自动 60s 定时刷新
 *
 * 用法：
 *   const { kline, intervals, loading, error, stats, latestPrice, loadKline, stop } =
 *       useKlineData(codeIdGetter, intervalGetter)
 */
const stores = new Map() // key: `${codeId}:${interval}` -> { kline, intervals, loading, error, timer }
export function useKlineData(codeIdRef, intervalRef) {
    // 兼容三种传参：getter 函数 / ref / 普通值
    const codeId = computed(() => {
        if (typeof codeIdRef === 'function') return codeIdRef()
        if (codeIdRef && typeof codeIdRef === 'object' && 'value' in codeIdRef) return codeIdRef.value
        return codeIdRef
    })
    const interval = computed(() => {
        if (typeof intervalRef === 'function') return intervalRef()
        if (intervalRef && typeof intervalRef === 'object' && 'value' in intervalRef) return intervalRef.value
        return intervalRef || '1m'
    })

    // store key = codeId + interval，切换级别时各用各的数据
    const storeKey = computed(() => `${codeId.value}:${interval.value}`)

    function getStore(key) {
        if (!key) return null
        if (!stores.has(key)) {
            stores.set(key, {
                kline: ref([]),
                intervals: ref([]),
                loading: ref(false),
                loadingEarlier: ref(false),
                error: ref(''),
                timer: null,
                refCount: 0,
            })
        }
        return stores.get(key)
    }

    const store = computed(() => getStore(storeKey.value))

    // 当前组件视角的引用（computed 转发到共享 store 内部 ref）
    const kline = computed(() => store.value?.kline.value ?? [])
    const intervals = computed(() => store.value?.intervals.value ?? [])
    const loading = computed(() => store.value?.loading.value ?? false)
    const loadingEarlier = computed(() => store.value?.loadingEarlier.value ?? false)
    const error = computed(() => store.value?.error.value ?? '')

    // 拉取 K 线数据（时间窗口自动限制在 MAX_BARS 根柱子内）
    async function loadKline() {
        const key = storeKey.value
        const s = getStore(key)
        if (!key || !s) return
        s.loading.value = true
        s.error.value = ''
        const params = buildKlineParams({ code_id: codeId.value, interval: interval.value })
        try {
            const res = await ProjectKline(params)
            const raw = res?.data?.kline || res?.kline || []
            const ivs = res?.data?.interval || res?.interval || []
            s.kline.value = raw
            if (Array.isArray(ivs) && ivs.length) s.intervals.value = ivs
        } catch (e) {
            console.error('获取 K 线数据失败:', e)
            s.error.value = 'K 线数据加载失败'
        } finally {
            s.loading.value = false
        }
    }

    /**
     * 向前加载更早的数据（无限滚动到过去）。
     * 以当前最早一根时间戳 - 一步长作为 to_date，向后端请求前一个窗口，
     * 结果按时间升序去重合并后置前。
     * @returns {Promise<number>} 新增前置的柱子数（供调用方平移视口）
     */
    async function loadEarlier() {
        const key = storeKey.value
        const s = getStore(key)
        if (!key || !s) return 0
        const ks = s.kline.value
        if (!ks || ks.length === 0) return 0
        if (s.loadingEarlier.value) return 0
        const stepSec = INTERVAL_SECONDS[interval.value] ?? 60
        const toDate = Number(ks[0].t) - stepSec
        s.loadingEarlier.value = true
        const oldLen = ks.length
        try {
            const params = buildKlineParams({ code_id: codeId.value, interval: interval.value, to_date: toDate })
            const res = await ProjectKline(params)
            const raw = res?.data?.kline || res?.kline || []
            if (Array.isArray(raw) && raw.length) {
                // 按时间戳去重合并（新数据在前），并升序排序
                const byT = new Map()
                raw.forEach(k => byT.set(String(k.t), k))
                ks.forEach(k => byT.set(String(k.t), k))
                s.kline.value = [...byT.values()].sort((a, b) => Number(a.t) - Number(b.t))
            }
        } catch (e) {
            console.error('加载更早 K 线失败:', e)
        } finally {
            s.loadingEarlier.value = false
        }
        return s.kline.value.length - oldLen
    }

    // ==================== 24h 统计（基于 K线计算） ====================
    const stats = computed(() => {
        const ks = kline.value
        if (!ks || ks.length === 0) return { high: null, low: null, change: null, changePct: null }
        const highs = ks.map(k => Number(k.h)).filter(v => !isNaN(v))
        const lows = ks.map(k => Number(k.l)).filter(v => !isNaN(v))
        const closes = ks.map(k => Number(k.c)).filter(v => !isNaN(v))
        const high = highs.length ? Math.max(...highs) : null
        const low = lows.length ? Math.min(...lows) : null
        const first = closes.length ? closes[0] : null
        const last = closes.length ? closes[closes.length - 1] : null
        const change = (first != null && last != null) ? last - first : null
        const changePct = (first != null && last != null && first !== 0)
            ? ((last - first) / first) * 100 : null
        return { high, low, change, changePct }
    })

    // 最新价（K线最后收盘价）
    const latestPrice = computed(() => {
        const ks = kline.value
        if (ks && ks.length) return Number(ks[ks.length - 1].c)
        return null
    })

    // 引用计数式自动刷新（多个子组件同时使用时只开一个定时器）
    function startAutoRefresh(intervalMs = 60000) {
        const key = storeKey.value
        const s = getStore(key)
        if (!key || !s) return
        s.refCount++
        if (s.timer) return
        loadKline()
        s.timer = setInterval(() => loadKline(), intervalMs)
    }
    function stop() {
        const s = store.value
        if (!s) return
        s.refCount = Math.max(0, s.refCount - 1)
        if (s.refCount === 0 && s.timer) {
            clearInterval(s.timer)
            s.timer = null
        }
    }

    // codeId / interval 任一变化时重载
    let stopWatch = null
    function bind() {
        stopWatch = watch([codeId, interval], ([newId, newIv], [oldId, oldIv]) => {
            if (newId === oldId && newIv === oldIv) return
            loadKline()
        })
    }

    return {
        kline,
        intervals,
        loading,
        loadingEarlier,
        error,
        stats,
        latestPrice,
        loadKline,
        loadEarlier,
        startAutoRefresh,
        stop,
        bind,
    }
}
