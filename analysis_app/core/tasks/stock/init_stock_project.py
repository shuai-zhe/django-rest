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
        return {filed: resource[filed] for filed in fields}

    def display_builder(self, project):
        model_data = {
            "name": project["name"],
            "display_name": project["display_name"],
            "code_id": project["code_id"],
        }
        return model_data
