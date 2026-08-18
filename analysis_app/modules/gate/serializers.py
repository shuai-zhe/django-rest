from rest_framework import serializers

from core.base_serializers import PageSerializer
from core.constants import KlineInterval
from core.excepting import ValidateErrorException


class ProjectSerializer(PageSerializer):
    id = serializers.IntegerField(required=False, label="项目主键ID")
    name = serializers.CharField(max_length=100, required=False, label="项目名称")
    display_name = serializers.CharField(max_length=100, required=False, label="项目显示名称")
    code_id = serializers.CharField(max_length=100, required=False, label="项目代码")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        filter_format = {}
        # id 为主键，精确匹配
        project_id = attrs.get("id")
        if project_id:
            filter_format["id"] = project_id
        # code_id 为项目唯一代码，精确匹配
        code_id = attrs.get("code_id")
        if code_id:
            filter_format["code_id"] = code_id
        # name / display_name 支持模糊匹配
        for field in ["name", "display_name"]:
            value = attrs.get(field)
            if value:
                filter_format[f"{field}__contains"] = value
        attrs["filter_format"] = filter_format
        return attrs


class ProjectKlineSerializer(ProjectSerializer):
    from_date = serializers.CharField(required=False, label="起始时间")
    to_date = serializers.CharField(required=False, label="指定 K 线图的起始时间")
    interval = serializers.ChoiceField(
        required=True, choices=KlineInterval.choices(), label="事件级别"
    )
    limit = serializers.IntegerField(required=False, label="柱体数量", default=1000)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        code_id = attrs.get("code_id", "").strip()

        if not code_id:
            raise ValidateErrorException("数据校验失败，缺少code_id进行查询")
        if attrs.get("from_date", ""):
            attrs["limit"] = 0

        return attrs
