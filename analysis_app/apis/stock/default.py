import abc
import re

import akshare as ak

from core.constants import KlineInterval, StockProjectStatus, StockType


class StockResource(abc.ABC):
    def extra_info(self, data, **kwargs) -> dict:
        return {
            "rank": "-",
            "symbols": {kwargs.get("code_type", kwargs.get("code_type", StockType))},
            "performance": {
                KlineInterval.D1.value: data.get("涨跌幅", 0),
                KlineInterval.D1.value.upper(): data.get("振幅", 0),
            },
        }

    def stock_format(self, data: dict, *args, **kwargs):
        """
        单条格式化数据
        :param data:原始数据
        :return:
        """
        code = data.get("代码", "")
        code = re.findall("[a-z]{2}\\d+", code)
        if len(code) != 1:
            raise ValueError("代码格式错误")
        code_type, code_value = code[0][:2], code[0][2:]
        format_data = {
            "name": data.get("代码"),
            "display_name": data.get("名称"),
            "code_id": code_value,
            "code_type": code_type,
            "price_dict": {
                StockProjectStatus.SPOT.name: data.get("最新价"),
            },
            "volume_dict": {
                StockProjectStatus.SPOT.name: data.get("成交量"),
            },
            "market_cap_dict": {
                StockProjectStatus.SPOT.name: data.get("成交额"),
            },
            "extra_info": self.extra_info(data, format_data=self.extra_info(data)),
        }
        return format_data

    def stock_kline_format(self, data: list | dict, *args, **kwargs):
        """
        格式化k线数据
        :param data:原始数据
        :return:
        """
        if not data:
            return []

    @abc.abstractmethod
    def stock_list(self) -> list:
        return []

    @abc.abstractmethod
    def stock_kline(self, *args, **kwargs) -> list:
        return []


class AkShareStockResource(StockResource):
    def stock_list(self) -> list:
        return [
            self.stock_format(data)
            for data in ak.stock_zh_a_spot().to_dict(orient="records")
        ]

    def stock_kline(
        self, symbol, period, start_date, end_date, adjust: str = ""
    ) -> list:
        """
        symbol str 股票代码
        period str 周期， period='daily'; choice of {'daily', 'weekly', 'monthly'}
        start_date str 开始日期 '2021-01-01'
        end_date str 结束日期 '2021-01-01'
        adjust str 调整 'qfq', 'hfq', 'qfq-factor', 'hfq-factor' 默认返回不复权的数据；qfq: 返回前复权后的数据；hfq: 返回后复权后的数据
        timeout int 超时时间，默认10秒
        """
        return ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        ).to_dict(orient="records")
