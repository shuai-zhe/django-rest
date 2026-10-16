import request from "../request"

// 合法数据源白名单（与后端模块前缀对齐），用于校验，避免脏值打到不存在的路由
const VALID_DATA_TYPES = ['gate', 'stock', 'future']
// 默认前缀：未存储 / 非法时回退到 gate（货币）
const DEFAULT_DATA_TYPE = 'gate'

// 实时计算接口前缀：gate -> /gate，stock -> /stock
function resolvePrefix(dataType) {
    const type = VALID_DATA_TYPES.includes(dataType) ? dataType : DEFAULT_DATA_TYPE
    return `/${type}`
}

export const ProjectList=(params = {}, dataType = DEFAULT_DATA_TYPE)=>{
    // 列表接口：<prefix>/project
    // 使用 POST：指标通配符 DSL（metric[] 数组条件）放在请求体中，
    // 避免复杂嵌套结构序列化进 query string 导致后端解析困难
    return request.post(`${resolvePrefix(dataType)}/project`, params)
}

export const ProjectKline=(params, dataType = DEFAULT_DATA_TYPE)=>{
    // K线接口：<prefix>/project/kline
    return request.get(`${resolvePrefix(dataType)}/project/kline`, { params })
}