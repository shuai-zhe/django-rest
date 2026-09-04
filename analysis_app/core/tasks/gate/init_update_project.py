import logging

from django.utils import timezone

from apis.cryptobubbles.default import _CryptobubblesApi
from modules.gate.models import Project

logger = logging.getLogger("init_update_project")


class ProjectMerge:
    # 筛选数据
    def __init__(
        self,
        status,
        extra_info_update_fields: dict | list = None,
        status_dict_update_fields: dict | list = None,
        model=None,
    ):
        self.model = model or Project
        # 需要的交易所
        self.code_id = "gateio"
        self.fields = []
        self.base_fields = {"update_at": timezone.now(), "active": 1}
        self.no_active_data = []
        # 筛选已存在的数据
        self.base_project = self.get_origin_data()
        self.base_project_code_id = self.base_project_code_id()
        self.exist_project = self.exist_project()
        logger.info(f"已存在的数据：{len(self.exist_project)}")
        # 状态
        self.status = status
        self.extra_info_update_fields = extra_info_update_fields or [
            "performance",
            "symbols",
            "id",
            "rank",
            "display_name"
        ]
        self.status_dict_update_fields = status_dict_update_fields or (
            ("price_dict", "price"),
            ("volume_dict", "volume"),
            ("market_cap_dict", "marketcap"),
        )

    def base_filed_build_update(self, model):
        for field, value in self.base_fields.items():
            if getattr(model, field):
                setattr(model, field, value)

    def get_origin_data(self):
        return [
            _
            for _ in _CryptobubblesApi.get_project_all().json()
            if _["symbols"].get("gateio")
        ]

    def base_project_code_id(self):
        return {_["name"] for _ in self.base_project}

    def exist_project(self):
        all_data = set(self.model.objects.values_list("display_name", flat=True))
        active_data = all_data & self.base_project_code_id
        self.no_active_data = all_data - self.base_project_code_id

        return active_data

    def extra_info_update_json(self, queryset, filed, update_data):
        query_value = queryset.extra_info.get(filed)
        if update_data is None or query_value == update_data:
            return
        queryset.extra_info[filed] = update_data

    def status_dict_update(self, queryset, filed, status, update_data):
        filed_value = getattr(queryset, filed)
        if update_data is None or filed_value.get(status) == update_data:
            return
        filed_value[status] = update_data
        setattr(queryset, filed, filed_value)

    def fields_update(self, queryset, filed, update_data):
        if update_data is None or getattr(queryset, filed) == update_data:
            return
        setattr(queryset, filed, update_data)

    def init_builder(self, resource:dict):
        return {
            "extra_info": {
                "performance": resource["performance"],
                "symbols": resource["symbols"],
                "id": resource["id"],
                "rank": resource["rank"],
            },
            "price_dict": {self.status: resource["price"]},
            "volume_dict": {self.status: resource["volume"]},
            "market_cap_dict": {self.status: resource["marketcap"]},
            "active":resource.get("active",1)
        }

    def init_update_build(
        self,
        pm,
        project,
    ):
        [
            self.extra_info_update_json(
                queryset=pm, filed=_, update_data=project.get(_)
            )
            for _ in self.extra_info_update_fields
        ]
        [
            self.status_dict_update(
                queryset=pm,
                filed=_[0],
                status=self.status,
                update_data=project.get(_[1]),
            )
            for _ in self.status_dict_update_fields
        ]
        [
            self.fields_update(
                queryset=pm,
                filed=_,
                update_data=project.get(_),
            )
            for _ in self.fields
        ]

    def display_builder(self, project):
        # 构造不会变的数据列
        model_data = {
            "name": project["symbol"],
            "display_name": project["name"],
            "code_id": project["symbols"].get(self.code_id, project["symbol"]),
        }
        return model_data

    def save(self):
        create_project_list = []
        update_project_list = []
        count_dict = {"create": 0, "update": 0}
        logger.info(f"当前总数：{len(self.base_project)}")
        for project in self.base_project:
            model_data = self.display_builder(project)
            try:
                # 减少查询次数
                if project["name"] in self.exist_project:
                    pm = self.model.objects.get(**model_data)
                    update_project_list.append(pm)
                    self.base_filed_build_update(pm)
                    self.init_update_build(pm, project)
                    count_dict["update"] += 1
                else:
                    _ = {**model_data, **self.init_builder(project),"display_name": project.get("display_name","")}
                    pm = self.model(**_)
                    create_project_list.append(pm)
                    count_dict["create"] += 1
            except Exception as e:
                logger.error(f"Stock数据：创建项目失败：{e}")
                continue

        if create_project_list:
            logger.info(f"批量创建：{len(create_project_list)}")
            self.model.objects.bulk_create(create_project_list)

        if update_project_list:
            logger.info(f"批量更新：{len(update_project_list)}")
            self.model.objects.bulk_update(
                update_project_list,
                fields=[
                    "extra_info",
                    "price_dict",
                    "volume_dict",
                    "market_cap_dict",
                    "update_at",
                ]
                + self.fields,
            )

        # 关闭无效数据
        no_active_list = self.model.objects.filter(
            display_name__in=self.no_active_data, active=1
        )
        no_active_count = 0
        if no_active_list.exists():
            no_active_count = no_active_list.count()
            logger.info(f"批量关闭：{no_active_count}")
            no_active_list.update(active=0)

        logger.info(
            f"创建：{count_dict['create']}，更新：{count_dict['update']};关闭：{no_active_count}"
        )


if __name__ == "__main__":
    """定时更新项目数据的Celery任务"""
    project_merge = ProjectMerge(status="spot")
    project_merge.save()


if __name__ == "__main__":
    ProjectMerge("spot").save()
