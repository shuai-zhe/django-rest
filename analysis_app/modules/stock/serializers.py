from rest_framework import serializers

from core.base_serializers import BaseProjectSerializer
from core.constants import KlineInterval, StockTrade, time_interval_limit_builder
from core.excepting import ValidateErrorException
from core.utils import to_strftime


class StockProjectSerializer(BaseProjectSerializer):
    code_type = serializers.CharField(max_length=2, required=False, label="代码类型")


class StockKlineSerializer(StockProjectSerializer):
    from_date = serializers.CharField(required=False, label="起始时间")
    to_date = serializers.CharField(required=False, label="指定 K 线图的起始时间")
    interval = serializers.ChoiceField(
        required=True, choices=KlineInterval.choices(), label="事件级别"
    )
    limit = serializers.IntegerField(required=False, label="柱体数量", default=1000)
    dtype = serializers.ChoiceField(
        required=False, choices=StockTrade.choices(), label="接口请求类型"
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        code_id = attrs.get("code_id", "").strip()
        if not code_id:
            raise ValidateErrorException("数据校验失败，缺少code_id进行查询")
        attrs["limit"] = time_interval_limit_builder(attrs.get("interval"))
        for t in ["from_date", "to_date"]:
            tv = attrs.get(t)
            if tv:
                attrs[t] = to_strftime(tv)[:10]

        return attrs
