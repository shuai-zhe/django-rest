from core.documents.new import NewDocument

# 新闻内部固定标签，不向接口与响应暴露
# 参与关键字分词检索的字段
SEARCH_FIELDS = ["title", "content"]


class NewService:
    def get_new_list(self, keyword=None, new_type=None, page=1, page_size=10):
        """
        查询新闻列表。
        :param keyword: 搜索关键字，对 title/content 做 IK 分词检索；为空则匹配全部
        :param new_type: 搜索新闻类型
        :param page: 页码（从 1 开始）
        :param page_size: 每页数量
        :return: dict -> {"total": 总数, "list": 新闻列表}
        """
        # 跨所有月份分区索引查询（news_YYYY-MM）
        s = NewDocument().search(all_index=True)
        # new_type 有值时才做过滤；为空则不过滤，避免 term 匹配 null 导致空结果
        if new_type:
            s = s.filter("term", new_type=new_type)
        # 需求3：关键字分词查询（title/content 使用 ik_max_word 索引 + ik_smart 搜索）
        if keyword:
            s = s.query(
                "multi_match",
                query=keyword,
                fields=SEARCH_FIELDS,
                analyzer="ik_smart",
                operator="or",
            )

        # 需求1：默认 created_at 降序
        s = s.sort("-created_at")

        # 分页
        page = max(int(page), 1)
        page_size = max(int(page_size), 1)
        start = (page - 1) * page_size
        s = s[start : start + page_size]

        response = s.execute()
        total = (
            response.hits.total.value
            if hasattr(response.hits.total, "value")
            else response.hits.total
        )

        news_list = []
        for hit in response:
            news_list.append(
                {
                    "id": hit.meta.id,
                    "title": getattr(hit, "title", ""),
                    "content": getattr(hit, "content", ""),
                    "new_type": getattr(hit, "new_type", ""),
                    "extra": getattr(hit, "extra", {}),
                    "created_at": getattr(hit, "created_at", None),
                }
            )

        return {"total": total, "list": news_list}
