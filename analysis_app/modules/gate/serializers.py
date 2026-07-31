from core.base_serializers import *
from core.constants import KlineInterval
from core.excepting import ValidateErrorException


class ProjectSerializer(PageSerializer):
    name = serializers.CharField(max_length=100, required=False, label="项目名称")
    display_name = serializers.CharField(max_length=100, required=False, label="项目显示名称")
    code_id = serializers.CharField(max_length=100, required=False, label="项目代码")


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
