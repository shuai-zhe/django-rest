import abc
import datetime
import re
import time
import akshare as ak
from typing import Any
import baostock as bs
import pandas as pd
from pandas import DataFrame

from core.constants import StockProjectStatus, StockType
from core.utils import to_datetime

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
            "rank": origin_data.get("rank", 0),
            "symbols": symbols,
            "position": origin_data.get("持仓量"),
            "performance": {
                "day": origin_data.get("涨跌幅", 0),
                "abs_day": origin_data.get("振幅", 0),
            },
        }

    def future_format(self, data: dict, *args, **kwargs):
        """
        单条格式化数据
        :param data:原始数据
        :return:
        """
        code_type = data.get("交易所", "")
        code_value = data.get("合约代码", "")
        format_data = {
            "name": code_value,
            "display_name": data.get("品种名称"),
            "code_id": code_value,
            "code_type": code_type,
            "price_dict": {
                StockProjectStatus.SPOT.value: data.get("最新价"),
            },
            "volume_dict": {
                StockProjectStatus.SPOT.value: data.get("成交量"),
            },
            "market_cap_dict": {
                StockProjectStatus.SPOT.value: data.get("持仓量", 0) * data.get("最新价", 0),
                "market": data.get("持仓量", 0)
            },
            "active": data.get("active", 1)
        }
        format_data["extra_info"] = self.extra_info(format_data, origin_data=data)
        return format_data

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
            "datetime": "t",
            "时间": "t",
            "最高": "h",
            "最低": "l",
            "收盘": "c",
            "开盘": "o",
        }
        extra_columns = {
            "amount": "amount",
            "pctChg": "pctChg",
            "成交量": "amount",
            "涨跌幅": "pctChg"
        }
        if kwargs.get("applay_extra_columns"):
            # 暂时不展示即可
            have_columns.update(extra_columns)

        if isinstance(data, list) or isinstance(data, dict):
            if not data:
                return []

        if isinstance(data, DataFrame):
            df = data.rename(columns=have_columns)[
                list(set(have_columns.values()))
            ]
            df["t"] = df["t"].map(lambda x: to_datetime(x).timestamp())
            return df.sort_values("t", ascending=True).to_dict(orient="records")

    @abc.abstractmethod
    def stock_list(self) -> list:
        return []

    @abc.abstractmethod
    def stock_kline(self, *args, **kwargs) -> list:
        return []

    @abc.abstractmethod
    def future_list(self, *args, **kwargs) -> list:
        return []

    @abc.abstractmethod
    def future_kline(self, *args, **kwargs) -> list:
        return []


class AkShareStockResource(StockResource):
    def stock_list(self) -> list:
        df = ak.stock_zh_a_spot()
        # 根据涨跌幅排序
        df["rank"] = df["涨跌幅"].rank(ascending=False, method="first").astype("int")
        df = df.to_dict(orient="records")
        return [self.stock_format(row) for row in df]

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

    def future_list(self, *args, **kwargs):
        # 根据涨跌幅排序
        df = ak.futures_fees_info()
        # 前天无数据的新项目暂时不进行采集展示
        df_active = \
        df.groupby("品种名称").apply(lambda x: x.sort_values(by=['成交量', '持仓量'], ascending=False).head(1))[
            ["合约代码", "合约名称"]]
        df_active['active'] = 1
        df = df.merge(df_active, on=["合约代码", "合约名称"], how='left')
        df['active'] = df['active'].fillna(0)
        df = df[df["上日结算价"].notna()]
        df["涨跌幅"] = (df["最新价"] - df["上日结算价"]) / df["上日结算价"] * 100
        df["rank"] = df["涨跌幅"].rank(ascending=False, method="first").astype("int")
        df = df.to_dict(orient="records")

        return [self.future_format(row) for row in df]

    def future_kline(self, code_id, interval, *args, **kwargs):
        if kwargs.get("error_ct", 0) == 2:
            return []
        code_id = code_id.upper().strip()
        try:
            if interval in ["daily"]:
                # try:
                df = ak.futures_zh_daily_sina(symbol=code_id)
                # except:
            elif interval in ["weekly", "monthly"]:
                df = ak.futures_hist_em(symbol=code_id, period=interval,**kwargs)
            else:
                df = ak.futures_zh_minute_sina(symbol=code_id, period=interval)
        except ValueError as e:
            if "Length mismatch: Expected axis has 0 elements, new values have" in str(e):
                code_id = ''.join(re.findall("(\D+)", code_id))
                if not code_id:
                    return []
                code_id += "0"
                kwargs["error_ct"] = kwargs.get("error_ct", 0) + 1
                return self.future_kline(code_id=code_id, interval=interval, *args, **kwargs)
            return []
        if df.empty:
            return []
        return self.stock_kline_format(df)


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

        # BaoStock 返回的数据本身已是 日期升序，且同一天的多条 bar 在原始顺序中即
        # 从早到晚排列，无需再做降序/升序反转。
        result = pd.DataFrame(data_list, columns=rs.fields)

        # BaoStock 无论何种周期，date 字段都只返回 年月日。需要按真实交易时段构造时间轴。
        # A股交易时段：上午 09:30-11:30、下午 13:00-15:00（午休 11:30-13:00 不交易）。
        # 日/周/月线每天仅一根，保留当天日期即可；分钟/小时线按真实开盘时间分段累加。
        _freq_seconds = {
            "5": 5 * 60,
            "15": 15 * 60,
            "30": 30 * 60,
            "60": 60 * 60,
            "d": 24 * 60 * 60,
            "w": 7 * 24 * 60 * 60,
            "m": 30 * 24 * 60 * 60,
        }
        _interval_sec = _freq_seconds.get(frequency, 24 * 60 * 60)

        # 当天 00:00:00 的秒级时间戳（基准日）
        result["_day_ts"] = result["date"].map(
            lambda x: int(time.mktime(time.strptime(x, "%Y-%m-%d")))
        )

        if frequency in ("5", "15", "30", "60"):
            # 组内从 0 开始的顺序索引（升序，从早到晚）
            result["_seq"] = result.groupby("date", sort=False).cumcount()
            # 当天总 bar 数：前一半为上午（09:30 起），后一半为下午（13:00 起）
            _day_count = result.groupby("date")["_seq"].transform("max") + 1
            _am_count = _day_count // 2
            _am_base = 9 * 3600 + 30 * 60  # 09:30:00 距午夜秒数
            _pm_base = 13 * 3600  # 13:00:00 距午夜秒数
            # 上午：从 09:30 起按 _seq 累加；下午：从 13:00 起按 (_seq-上午数) 累加
            _offset = (
                    result["_seq"].where(
                        result["_seq"] < _am_count,
                        result["_seq"] - _am_count,
                    )
                    * _interval_sec
                    + _am_base
            )
            _offset = _offset.where(
                result["_seq"] < _am_count, _offset + (_pm_base - _am_base)
            )
            result["date"] = result["_day_ts"] + _offset
        else:
            # 日/周/月线：当天日期，时分归零
            result["date"] = result["_day_ts"]

        result = result.drop(columns=["_day_ts", "_seq"], errors="ignore")
        if result.empty:
            return []
        return self.stock_kline_format(result)

    def future_list(self, *args, **kwargs):
        return []

    def future_kline(self, *args, **kwargs):
        return []


if __name__ == "__main__":
    # data = BaoStockResource().stock_kline(
    #     "sh.600000", "15", start_date="2024-07-01", end_date="2024-12-31"
    # )
    get_futures_daily_df = ak.get_futures_daily(start_date="20260904", end_date="20260904", market="DCE")
    print(get_futures_daily_df)
