import logging

from apis.stock.default import AkShareStockResource
from core.tasks.gate.init_update_project import ProjectMerge
from modules.stock.models import StockProject

logger = logging.getLogger("init_update_project")


class StockMerge(ProjectMerge):
    def __init__(self, status, *args, **kwargs):
        super().__init__(status, *args, **kwargs, model=StockProject)

    def get_origin_data(self):
        return AkShareStockResource().stock_list()

    def exist_project(self):
        return (
            set(self.model.objects.values_list("name", flat=True))
            & self.base_project_code_id
        )

    def init_builder(self, resource):
        fields = ["extra_info", "price_dict", "volume_dict", "market_cap_dict"]
        data = {filed: resource[filed] for filed in fields}
        return data

    def init_update_build(self, pm, project):
        [
            self.extra_info_update_json(
                queryset=pm, filed=_, update_data=project.get("extra_info", {}).get(_)
            )
            for _ in self.extra_info_update_fileds
        ]
        [
            self.status_dict_update(
                queryset=pm,
                filed=_[0],
                status=self.status,
                update_data=project.get(_[0], {}).get("spot"),
            )
            for _ in self.status_dict_update_fileds
        ]

    def display_builder(self, project):
        model_data = {
            "name": project["name"],
            "display_name": project["display_name"],
            "code_id": project["code_id"],
            "code_type": project["code_type"],
        }
        return model_data
