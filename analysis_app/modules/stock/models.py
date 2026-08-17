from django.db import models

# Create your models here.


class StockProject(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="项目名称")
    display_name = models.CharField(max_length=100, verbose_name="项目显示名称")
    code_type = models.CharField(max_length=2, verbose_name="代码类型")  # sz,sh
    code_id = models.CharField(max_length=100, verbose_name="项目代码")
    extra_info = models.JSONField(verbose_name="项目额外信息", default=dict)
    # 使用JSON字段存储不同状态的数据
    price_dict = models.JSONField(
        default=dict, verbose_name="价格字典", help_text='格式: {"SPOT": 100.0}'
    )
    volume_dict = models.JSONField(
        default=dict, verbose_name="交易量字典", help_text='格式: {"SPOT": 50000}'
    )
    market_cap_dict = models.JSONField(
        default=dict, verbose_name="市值字典", help_text='格式: {"SPOT": 1000000}'
    )
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
