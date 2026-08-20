import request from "../request"

// 数据源类型 → 后端接口前缀（gate=货币，stock=股票，两者结构对齐）
const PROJECT_ENDPOINT = {
    gate:  "/gate/project",
    stock: "/stock/project",
}
const KLINE_ENDPOINT = {
    gate:  "/gate/project/kline",
    stock: "/stock/project/kline",
}

export const ProjectList=(params = {}, dataType = 'gate')=>{
    const ep = PROJECT_ENDPOINT[dataType] || PROJECT_ENDPOINT.gate
    return request.get(ep, { params })
}

export const ProjectKline=(params, dataType = 'gate')=>{
    const ep = KLINE_ENDPOINT[dataType] || KLINE_ENDPOINT.gate
    return request.get(ep, { params })
}