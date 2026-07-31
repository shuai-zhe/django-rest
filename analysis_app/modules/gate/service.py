from modules.gate.models import Project

from .data_build.kline_build import _Kline


class GateService:
    def formatter(self, obj):
        return obj.values()

    def get_project_all(self, **kwargs):
        return self.formatter(Project.objects.all())

    def get_kline_all(self, validated_data, **kwargs):
        # 后续封装自动查找和错误切换
        return _Kline.gate(validated_data, **kwargs)
