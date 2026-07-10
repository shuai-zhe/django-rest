from django.contrib import admin
from core.number_tools import supper_float_n
# Register your models here.

from modules.gate.models import Project

class ProjectAdmin(admin.ModelAdmin):
    list_display  = ["id","code_id","name","display_name","price_operate","volume_operate","market_cap_operate","update_at"]

    def price_operate(self,obj):
        return supper_float_n(obj.price_dict['spot'])

    def volume_operate(self,obj):
        return obj.volume_dict['spot']

    def market_cap_operate(self,obj):
        return obj.market_cap_dict['spot']

    price_operate.short_description  = "价格（现货）"
    volume_operate.short_description  = "交易量（现货）"
    market_cap_operate.short_description  = "市值（现货）"

admin.site.register(Project,ProjectAdmin)