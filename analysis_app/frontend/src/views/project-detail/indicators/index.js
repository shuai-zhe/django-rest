/**
 * 独立 K 线指标注册表（用于 project-detail / KlineChart.vue）
 *
 * 设计目标：新增指标只需在 REGISTRY 中注册一条定义，无需改动图表渲染逻辑。
 *
 * 每个指标定义是一个工厂函数：`(params) => IndicatorInstance`
 * IndicatorInstance 结构：
 *   {
 *     id,                // 唯一标识，用于勾选状态
 *     label,             // 展示名，如 "MA(20)"
 *     lines(kline)       // (rawKline) => [{ name, color, values }]
 *                        // values 是与 kline 等长的数组，缺失位置为 null（如 MA 前 period-1 个点）
 *   }
 */

// ---------- 基础统计工具 ----------
function sum(arr) {
    return arr.reduce((a, b) => a + b, 0)
}
function mean(arr) {
    return arr.length ? sum(arr) / arr.length : null
}
function stdDev(arr, m) {
    return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length)
}

// 返回与 kline 等长的滑动窗口数组，窗口不足时该位置为 null
function rollingWindow(values, period) {
    return values.map((_, i) => {
        if (i + 1 < period) return null
        return values.slice(i - period + 1, i + 1)
    })
}

// 取收盘价序列
function closesOf(kline) {
    return kline.map(k => Number(k.c))
}

// ---------- 指标注册表 ----------
export const REGISTRY = {}

/**
 * 注册一个指标
 * @param {string} id       唯一标识
 * @param {Function} factory (params) => IndicatorInstance
 */
export function registerIndicator(id, factory) {
    REGISTRY[id] = factory
}

// ---------- MA：移动平均线（K线移动数量） ----------
registerIndicator('ma', (params = { period: 20 }) => {
    const period = params.period
    return {
        id: 'ma',
        label: `MA(${period})`,
        lines(kline) {
            const closes = closesOf(kline)
            const windows = rollingWindow(closes, period)
            const values = windows.map(w => (w ? mean(w) : null))
            return [{ name: `MA${period}`, color: '#f1c40f', values }]
        },
    }
})

// ---------- BOLL：布林带（上轨 / 中轨 / 下轨） ----------
registerIndicator('boll', (params = { period: 20, stdDev: 2 }) => {
    const period = params.period
    const k = params.stdDev
    return {
        id: 'boll',
        label: `BOLL(${period},${k})`,
        lines(kline) {
            const closes = closesOf(kline)
            const windows = rollingWindow(closes, period)
            const mid = windows.map(w => (w ? mean(w) : null))
            const upper = windows.map(w => (w ? mean(w) + k * stdDev(w, mean(w)) : null))
            const lower = windows.map(w => (w ? mean(w) - k * stdDev(w, mean(w)) : null))
            return [
                { name: `UP${period}`, color: '#e67e22', values: upper },
                { name: `MID${period}`, color: '#9b59b6', values: mid },
                { name: `LOW${period}`, color: '#16a085', values: lower },
            ]
        },
    }
})

// ---------- 便捷构建：按 id + params 生成指标实例 ----------
export function createIndicator(id, params) {
    const factory = REGISTRY[id]
    if (!factory) throw new Error(`未知指标: ${id}`)
    return factory(params)
}

// 预置常用指标（供界面默认勾选）
export const PRESETS = [
    { id: 'ma', label: 'MA(5)', params: { period: 5 } },
    { id: 'ma', label: 'MA(10)', params: { period: 10 } },
    { id: 'ma', label: 'MA(20)', params: { period: 20 } },
    { id: 'boll', label: 'BOLL(20,2)', params: { period: 20, stdDev: 2 } },
]
