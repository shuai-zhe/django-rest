from core.tasks.stock.init_stock_project import AkShareStockResource,StockMerge
from modules.stock_future.models import FutureProject

class FutureMerge(StockMerge):
    def __init__(self, status,model=None, *args, **kwargs):
        super().__init__(status=status, *args, **kwargs, model=model or FutureProject)
        self.fields = ["display_name","active"]
        self.extra_info_update_fields += ["position"]

    def get_origin_data(self):
        # 数据实时统计主力
        return AkShareStockResource().future_list()



if __name__ == '__main__':
    FutureMerge(status="spot").save()