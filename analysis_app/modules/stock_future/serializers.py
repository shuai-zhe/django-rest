from rest_framework import serializers

from core.base_serializers import BaseProjectSerializer
from core.constants import KlineInterval, StockTrade, time_interval_limit_builder
from core.excepting import ValidateErrorException
from core.utils import to_strftime


class StockFutureProjectSerializer(BaseProjectSerializer):
    is_main = serializers.BooleanField(required=False,default=True,label="是否主力")
    code_type = serializers.CharField(max_length=2, required=False, label="代码类型")
    dtype = serializers.CharField(max_length=20,required=False,default="stock")


class StockFutureKlineSerializer(StockFutureProjectSerializer):
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

        # interval特殊处理
        interval = attrs.get("interval",None)
        attrs["interval"] = KlineInterval.value_to_self(interval).translate_to_future()
        return attrs
