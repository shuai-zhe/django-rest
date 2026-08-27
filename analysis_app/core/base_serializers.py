from rest_framework import serializers


class PageSerializer(serializers.Serializer):
    page = serializers.IntegerField(default=1, label="页码")
    page_size = serializers.IntegerField(default=20, label="每页数量")


class BaseProjectSerializer(PageSerializer):
    id = serializers.IntegerField(required=False, label="项目主键ID")
    name = serializers.CharField(max_length=100, required=False, label="项目名称")
    display_name = serializers.CharField(max_length=100, required=False, label="项目显示名称")
    code_id = serializers.CharField(max_length=100, required=False, label="项目代码")
    filters = serializers.ListField(
        child=serializers.DictField(), required=False, label="过滤条件DSL"
    )
    order_by = serializers.ListField(
        child=serializers.DictField(), required=False, label="排序条件DSL"
    )

    def build_op(self, op, key, value, type=None, cond="and"):
        _ = {"op": op, "key": key, "value": value, "cond": cond}
        if type:
            _["type"] = type
        return _

    def validate(self, attrs):
        attrs = super().validate(attrs)
        filters = attrs.get("filters", [])
        # id 为主键，精确匹配
        project_id = attrs.get("id")
        if project_id:
            filters.append(self.build_op("eq", "id", project_id))
        # code_id 为项目唯一代码，精确匹配
        code_id = attrs.get("code_id")
        if code_id:
            filters.append(self.build_op("eq", "code_id", code_id))
        # code_type 交易所类型，精确匹配
        code_type = attrs.get("code_type")
        if code_type:
            filters.append(self.build_op("eq", "code_type", code_type))
        # name / display_name 支持模糊匹配
        for field in ["name", "display_name"]:
            value = attrs.get(field)
            if value:
                filters.append(self.build_op("contains", field, value))
        attrs["filters"] = filters
        return attrs
