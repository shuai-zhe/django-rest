from django.db.models import F, Func, Q, QuerySet, Value


class QueryBuild:
    """
    过滤器格式化器
    """

    SUFFIXES = {
        "eq": "__in",
        "include": "__contains",
        "contains": "__icontains",
        "gt": "__gt",
        "lt": "__lt",
        "gte": "__gte",
        "lte": "__lte",
        "json__in": "__in",
    }
    RATE = {
        "abs": Func(
            Func(
                F("extra_info"),
                Value("$.performance.day"),
                function="JSON_EXTRACT",
            ),
            function="ABS",
        ).desc(),
        "positive": "-",
        "negative": "+",
    }

    def __init__(
        self,
        query: QuerySet,
        filter_params: list[dict] = None,
        order_params: list[dict] | str = None,
    ):
        self.query = query
        self.filter_params = filter_params or []
        self.order_params = order_params or []

    @staticmethod
    def _default(param: dict):
        v = {"op": param.get("op", "eq"), "cond": param.get("cond", "and")}
        param.update(v)
        return param

    @classmethod
    def formatter(cls, value):
        # 格式验证 必须包含
        #         key:字段名
        #         value:查询值
        #         op:操作符：eq、neq、in、nin、gt、gte、lt、lte
        #         cond:条件：and、or
        if not isinstance(value, dict):
            raise ValueError(f"格式错误：{value}")
        if not all(key in value for key in ["key", "value", "op", "cond"]):
            raise ValueError(f"格式错误：{value}")
        if value.get("cond", "and") not in ["and", "or"]:
            raise ValueError(f"不支持的条件：{value.get('cond')}")
        value = cls.expand_formatter(value)
        return value

    @classmethod
    def expand_formatter(cls, value):
        """
        扩展格式化器，用于处理扩展字段
        """
        filter_type = value.get("type")
        if not filter_type:
            return value

        match filter_type:
            case "metric":
                # 指标类型情况下
                field = value["key"]
                if "performance__" in field or field in ["rank"]:
                    # 对时间字段需要进行改装
                    value["key"] = "extra_info__" + field
        return value

    def filter_format(self, filter_param):
        """
        过滤处理 根据传入类型解析；所以的格式应该为 {key:col,value:v,op:operator}
        key:字段名
        value:查询值
        op:操作符：eq、include、gt、gte、lt、lte
        cond:条件：and、or
        return 返回一个
        """
        filter_format_dict = []
        if isinstance(filter_param, list):
            for item in filter_param:
                self._default(item)
                filter_format_dict.append(self.formatter(item))
        elif isinstance(filter_param, dict):
            filter_param = {
                "key": filter_param["key"],
                "value": filter_param["value"],
            }
            self._default(filter_param)
            filter_format_dict.append(self.formatter(filter_param))
        return filter_format_dict

    def filter(self):
        # 所有的query查询都应该写成
        query_list = Q()
        for param in self.filter_format(self.filter_params):
            cond = param.get("cond", "and")
            op = self.SUFFIXES.get(param["op"], "")
            query_value = param["value"]
            query_key = f"""{param["key"]}{op}"""
            query_dsl = Q(**{query_key: query_value})
            # op构造，扩展或许需要判断其它类型；比如JSON
            if param["op"] == "json__in":
                # json包含特殊用例，建议少用
                q_objects = Q()
                for value in query_value:
                    q_objects |= Q(**{f"{query_key}__contains": [value]})
                query_dsl = q_objects

            query_list = (
                query_list & query_dsl if cond == "and" else query_list | query_dsl
            )
        self.query = self.query.filter(query_list)

        return self.query

    def order_format(self, order_params):
        """
        排序处理 根据传入类型解析；所以的格式应该为 {key:col,value:v,op:operator}
        key:字段名
        value:查询值
        op:操作符：eq、include、gt、gte、lt、lte
        cond:条件：and、or
        return 返回一个
        """
        if isinstance(order_params, str):
            return order_params
        order_ = []
        for order_param in order_params:
            if order_param is None:
                continue
            if isinstance(order_param, dict):
                if order_param.get("type", "") == "metric":
                    _ = self.RATE.get(order_param["value"])
                    if not _:
                        continue
                    if _ in ["-", "+"]:
                        field = f"extra_info__{order_param['key']}"
                        order_.append(f"{_}{field}".replace("+", ""))
                        if "performance" in order_param["key"]:
                            performance_filter = {
                                field + "__gt" if _ == "-" else field + "__lt": 0
                            }
                            self.query = self.query.filter(**performance_filter)
                    elif _:
                        order_.append(_)  # 特殊值 直接排序
        return order_

    def order_by(self):
        order_ = self.order_format(self.order_params)
        if not order_:
            return self.query
        self.query = self.query.order_by(*order_)
        return self.query

    def exec(self):
        """执行全部数据操作"""
        self.filter()
        self.order_by()
        return self.query
