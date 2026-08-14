from rest_framework import serializers

from core.base_serializers import PageSerializer


class NewSearchSerializer(PageSerializer):
    # 搜索关键字：对 title / content 做 IK 分词检索，传空则匹配全部
    keyword = serializers.CharField(max_length=200, required=False, label="搜索关键字")
    new_type = serializers.ChoiceField(
        choices=(("new", "new"), ("stock", "stock")),
        required=False,
        label="新闻类型",
        default="new",
    )


class NewDetailSerializer(serializers.Serializer):
    # 新闻详情：按 ES 文档 id 查询单条
    id = serializers.CharField(required=True, label="新闻ID")
