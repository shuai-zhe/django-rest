from apis.base import RequestBase



host = "https://api.gateio.ws"
prefix = "/api/v4"

class GetApi:
    def __init__(self):
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.get_spot_currency_pairs = RequestBase(url=host+prefix+"/spot/currency_pairs",headers=self.headers)
        self.get_spot_kline = RequestBase(url=host+prefix+"/spot/candlesticks",headers=self.headers)

    # def get_spot_kline(self, currency_pair, interval: str = "15m", limit: int = None, from_: int = None, to_: int = None):
    #     # 构建参数字典
    #     params = {
    #         "currency_pair": "{}_USDT".format(currency_pair),
    #         "interval": interval,
    #         "limit": limit,
    #         "from": from_,
    #         "to": to_
    #     }
    #
    #     # 使用set_params过滤空值
    #     filtered_params = self.set_params(params)
    #
    #     return self.request(
    #         url= "/spot/candlesticks",
    #         params=filtered_params
    #     )


_GetApi = GetApi()

