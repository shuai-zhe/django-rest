import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analysis_app.settings")
django.setup()

from apis.cryptobubbles.default import _CryptobubblesApi
from gate.models import Project
from core.constants import ProjectStatus

# 筛选数据
base_project = [_ for _ in _CryptobubblesApi.get_project_all().json() if _["symbols"].get("gateio")]
# 筛选已存在的数据
base_project_code_id = {_["name"] for _ in base_project}
exist_project = set(Project.objects.values_list("display_name",flat=True)) & base_project_code_id
# 状态
status = ProjectStatus.SPOT.value
extra_info_update_fileds = ["performance", "symbols", "id", "rank"]
status_dict_update_fileds = (("price_dict", "price"), ("volume_dict", "volume"), ("market_cap_dict", "marketcap"))
def extra_info_update_json(queryset, filed, update_data):
    query_value = queryset.extra_info.get(filed)
    if update_data is None or query_value == update_data:
        return
    queryset.extra_info[filed] = update_data

def status_dict_update(queryset, filed, status, update_data):
    filed_value = getattr(queryset, filed)
    if update_data is None or filed_value.get(status) == update_data:
        return
    filed_value[status] = update_data
    setattr(queryset, filed, update_data)

def init_builder(resource):
    return {
        "extra_info": {
            "performance": resource["performance"],
            "symbols": resource["symbols"],
            "id": resource["id"],
            "rank": resource["rank"]
        },
        "price_dict": {
            status: resource["price"]
        },
        "volume_dict": {
            status: resource["volume"]
        },
        "market_cap_dict": {
            status: resource["marketcap"]
        }
    }


create_project_list = []
update_project_list = []
count_dict = {"create": 0, "update": 0}
print(f"当前总数：{len(base_project)}")
n = 0
for project in base_project:
    n+=1
    print(f"\r总数:{count_dict}",end="")
    model_data = {
        "name": project["symbol"],
        "display_name": project["name"],
        "code_id": project["symbols"]["gateio"],
    }
    # 减少查询次数
    if project["name"] in exist_project:
        pm = Project.objects.get(**model_data)
        update_project_list.append(pm)
        count_dict["update"] += 1
    else:
        _ ={**model_data, **init_builder(project)}
        pm = Project.objects.create(**_)
        create_project_list.append(pm)
        count_dict["create"] += 1
        continue

    [extra_info_update_json(queryset=pm, filed=_, update_data=project.get(_)) for _ in extra_info_update_fileds]
    [status_dict_update(queryset=pm, filed=_[0], status=status, update_data=project.get(_[1])) for _ in
     status_dict_update_fileds]


print("")
if create_project_list:
    print(f"批量创建：{len(create_project_list)}")
    Project.objects.bulk_create(create_project_list)

if update_project_list:
    print(f"批量更新：{len(update_project_list)}")
    Project.objects.bulk_update(update_project_list, fields=["extra_info", "price_dict", "volume_dict", "market_cap_dict"])

