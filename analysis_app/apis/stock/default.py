import abc
import datetime
import re
import time
from typing import Any

import akshare as ak
import baostock as bs
import pandas as pd
from pandas import DataFrame

from core.constants import StockProjectStatus, StockType

DEFAULT_DIFF_INTERVAL = {
    "d": 100,
    "h": 5,
    "30m": 10,
    "15m": 20,
    "5m": 30,
    "1m": 60,
}


class StockResource(abc.ABC):
    def extra_info(self, data, **kwargs) -> dict:
        symbols = {}
        origin_data = kwargs.get("origin_data", {}) or data
        code_type = data.get("code_type")
        if code_type:
            code_type = getattr(StockType, str(code_type).upper(), None)

            if code_type:
                symbols[code_type.value] = code_type.translate

        return {
            "rank": "-",
            "symbols": symbols,
            "performance": {
                "day": origin_data.get("涨跌幅", 0),
                "abs_day": origin_data.get("振幅", 0),
            },
        }

    def stock_format(self, data: dict, *args, **kwargs):
        """
        单条格式化数据
        :param data:原始数据
        :return:
        """
        code = data.get("代码", "")
        code_split = re.findall("[a-z]{2}\\d+", code)
        if len(code_split) != 1:
            raise ValueError("代码格式错误")
        code_type, code_value = code[:2], code[2:]
        format_data = {
            "name": data.get("代码"),
            "display_name": data.get("名称"),
            "code_id": code_value,
            "code_type": code_type,
            "price_dict": {
                StockProjectStatus.SPOT.value: data.get("最新价"),
            },
            "volume_dict": {
                StockProjectStatus.SPOT.value: data.get("成交量"),
            },
            "market_cap_dict": {
                StockProjectStatus.SPOT.value: data.get("成交额"),
            },
        }
        format_data["extra_info"] = self.extra_info(format_data, origin_data=data)
        return format_data

    def stock_kline_format(self, data: list | dict | DataFrame, *args, **kwargs):
        """
        格式化k线数据
        :param data:原始数据
        :return:
        """
        have_columns = {
            "date": "t",
            "open": "o",
            "high": "h",
            "low": "l",
            "close": "c",
            "volume": "v",
        }
        extra_columns = {
            "amount": "amount",
            "pctChg": "pctChg",
        }
        if kwargs.get("applay_extra_columns"):
            have_columns.update(extra_columns)

        if isinstance(data, list) or isinstance(data, dict):
            if not data:
                return []

        if isinstance(data, DataFrame):
            return data.rename(columns=have_columns)[
                list(have_columns.values())
            ].to_dict(orient="records")

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


class BaoStockResource(StockResource):
    def stock_list(self, *args, **kwargs) -> list:
        return []

    def stock_kline(
        self, code, frequency, start_date, end_date, adjustflag: str = "3"
    ) -> list[Any] | None | Any:
        """
        code：股票代码，sh或sz.+6位数字代码，或者指数代码，如：sh.601398。sh：上海；sz：深圳。此参数不可为空；
        fields：指示简称，支持多指标输入，以半角逗号分隔，填写内容作为返回类型的列。详细指标列表见历史行情指标参数章节，日线与分钟线参数不同。此参数不可为空；
        start：开始日期（包含），格式“YYYY-MM-DD”，为空时取2015-01-01；
        end：结束日期（包含），格式“YYYY-MM-DD”，为空时取最近一个交易日；
        frequency：数据类型，默认为d，日k线；d=日k线、w=周、m=月、5=5分钟、15=15分钟、30=30分钟、60=60分钟k线数据，不区分大小写；指数没有分钟线数据；周线每周最后一个交易日才可以获取，月线每月最后一个交易日才可以获取。
        adjustflag：复权类型，默认不复权：3；1：后复权；2：前复权。已支持分钟线、日线、周线、月线前后复权。 BaoStock提供的是涨跌幅复权算法复权因子，具体介绍见BaoStock复权因子简介。
        """
        # start_date不存在默认使用当前日期； end_date不存在，默认100个周期
        if not start_date:
            start_date = time.strftime("%Y-%m-%d")
        if not end_date:
            end_date = (
                datetime.datetime.now()
                - datetime.timedelta(days=DEFAULT_DIFF_INTERVAL.get(frequency, 3))
            ).strftime("%Y-%m-%d")

        bs.login()
        rs = bs.query_history_k_data_plus(
            code=code,
            fields="date,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )
        data_list = []
        while (rs.error_code == "0") & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())

        if not data_list:
            return []

        result = pd.DataFrame(data_list, columns=rs.fields).sort_values(
            "date", ascending=False
        )
        result["date"] = result["date"].map(
            lambda x: int(time.mktime(time.strptime(x, "%Y-%m-%d")))
        )
        bs.logout()

        if result.empty:
            return []
        return self.stock_kline_format(result)


if __name__ == "__main__":
    data = BaoStockResource().stock_kline(
        "sh.600000", "15", start_date="2024-07-01", end_date="2024-12-31"
    )
    print(data)
    # df = pd.DataFrame(AkShareStockResource().stock_list())#.to_csv("./tests.csv")
    # print(AkShareStockResource().stock_list())

    # print(ak.stock_zh_a_spot())
