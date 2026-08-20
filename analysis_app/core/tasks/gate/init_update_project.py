import logging

from apis.cryptobubbles.default import _CryptobubblesApi
from modules.gate.models import Project

logger = logging.getLogger("init_update_project")


class ProjectMerge:
    # 筛选数据
    def __init__(
        self,
        status,
        extra_info_update_fileds: dict | list = None,
        status_dict_update_fileds: dict | list = None,
        model=None,
    ):
        self.model = model or Project
        # 需要的交易所
        self.code_id = "gateio"
        # 筛选已存在的数据
        self.base_project = self.get_origin_data()
        self.base_project_code_id = self.base_project_code_id()
        self.exist_project = self.exist_project()
        logger.info(f"已存在的数据：{len(self.exist_project)}")
        # 状态
        self.status = status
        self.extra_info_update_fileds = extra_info_update_fileds or [
            "performance",
            "symbols",
            "id",
            "rank",
        ]
        self.status_dict_update_fileds = status_dict_update_fileds or (
            ("price_dict", "price"),
            ("volume_dict", "volume"),
            ("market_cap_dict", "marketcap"),
        )

    def get_origin_data(self):
        return [
            _
            for _ in _CryptobubblesApi.get_project_all().json()
            if _["symbols"].get("gateio")
        ]

    def base_project_code_id(self):
        return {_["name"] for _ in self.base_project}

    def exist_project(self):
        return (
            set(self.model.objects.values_list("display_name", flat=True))
            & self.base_project_code_id
        )

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

    def init_builder(self, resource):
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
        }

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
            # 减少查询次数
            if project["name"] in self.exist_project:
                pm = self.model.objects.get(**model_data)
                update_project_list.append(pm)
                count_dict["update"] += 1
                [
                    self.extra_info_update_json(
                        queryset=pm, filed=_, update_data=project.get(_)
                    )
                    for _ in self.extra_info_update_fileds
                ]
                [
                    self.status_dict_update(
                        queryset=pm,
                        filed=_[0],
                        status=self.status,
                        update_data=project.get(_[1]),
                    )
                    for _ in self.status_dict_update_fileds
                ]
            else:
                _ = {**model_data, **self.init_builder(project)}
                pm = self.model(**_)
                create_project_list.append(pm)
                count_dict["create"] += 1

        if create_project_list:
            logger.info(f"批量创建：{len(create_project_list)}")
            self.model.objects.bulk_create(create_project_list)

        if update_project_list:
            logger.info(f"批量更新：{len(update_project_list)}")
            self.model.objects.bulk_update(
                update_project_list,
                fields=["extra_info", "price_dict", "volume_dict", "market_cap_dict"],
            )

        logger.info(f"创建：{count_dict['create']}，更新：{count_dict['update']}")
