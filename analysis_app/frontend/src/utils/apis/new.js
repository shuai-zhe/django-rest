import request from "../request"

/**
 * 新闻列表查询
 * @param {Object} params
 * @param {string} [params.keyword]  关键字（对 title/content 分词检索），传空查全部
 * @param {string} [params.new_type] 新闻类型：new / stock
 * @param {number} [params.page]     页码（从 1 开始）
 * @param {number} [params.page_size] 每页数量
 */
export const NewList = (params = {}) => {
    return request.get("/new/list", { params })
}

/**
 * 新闻详情查询（按 ES 文档 id）
 * @param {string} id 新闻 id
 */
export const NewDetail = (id) => {
    return request.get("/new/detail", { params: { id } })
}
