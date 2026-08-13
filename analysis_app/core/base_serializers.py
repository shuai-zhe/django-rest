from rest_framework import serializers


class PageSerializer(serializers.Serializer):
    page = serializers.IntegerField(default=1, label="页码")
    page_size = serializers.IntegerField(default=20, label="每页数量")
