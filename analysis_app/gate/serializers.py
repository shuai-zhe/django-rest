from rest_framework import serializers


class ProjectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100,required=False,label='项目名称')
    display_name = serializers.CharField(max_length=100,required=False,label='项目显示名称')
    codeId = serializers.CharField(max_length=100,required=True,label='项目代码')