from core.base_serializers import *

class ProjectSerializer(PageSerializer):
    name = serializers.CharField(max_length=100,required=False,label='项目名称')
    display_name = serializers.CharField(max_length=100,required=False,label='项目显示名称')
    code_id = serializers.CharField(max_length=100,required=False,label='项目代码')