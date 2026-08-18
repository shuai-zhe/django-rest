import logging
import time

from core.base import Resource
from modules.gate.models import Project
from modules.gate.serializers import ProjectKlineSerializer, ProjectSerializer
from modules.gate.service import GateService

logger = logging.getLogger(__name__)

# 回写节流：记录每个 code_id 最近一次成功回写的时间戳（进程内缓存），
# 一分钟内重复请求 K 线不再回写 Project 表，避免前端频繁刷新导致多次写库。
_ANALYSIS_SYNC_INTERVAL = 60  # 秒
_analysis_sync_cache = {}


def _sync_project_analysis(data, code_id):
    """用本次 K 线请求已返回的数据计算 24h 统计并回写 Project.extra_info.analysis。

    不再二次请求 gate，直接使用传入的 data["kline"]。
    前端可能传任意 interval（1m/1h/1d...），因此按「最近 24 小时时间窗口」从返回数据里
    裁剪子集后再统计，保证 24h 统计与 interval 无关。
    一分钟内对同一 code_id 的重复回写会被跳过（见 _analysis_sync_cache）。
    失败时仅记录日志，不影响 K 线接口正常返回。
    """
    try:
        now_ts = time.time()
        last_ts = _analysis_sync_cache.get(code_id)
        if last_ts is not None and now_ts - last_ts < _ANALYSIS_SYNC_INTERVAL:
            return  # 一分钟内已回写，跳过

        klines = (data or {}).get("kline") or []
        if not klines:
            return

        # 裁剪最近 24 小时内的 K 线（t 为秒级时间戳）
        window_start = now_ts - 86400
        window = [
            k
            for k in klines
            if k.get("t") is not None and float(k["t"]) >= window_start
        ]
        if not window:
            # 返回数据可能全在更早（如 to_date 指定在过去），则回退用全部数据
            window = klines

        highs = [float(k["h"]) for k in window if k.get("h") is not None]
        lows = [float(k["l"]) for k in window if k.get("l") is not None]
        # gate candlesticks 的 v 为单根成交量，24h 成交量取窗口内各根之和
        volumes = [float(k["v"]) for k in window if k.get("v") is not None]
        # 收盘价序列（用于最新价与 24h 涨跌幅）
        closes = [float(k["c"]) for k in window if k.get("c") is not None]

        analysis = {
            "high_24h": max(highs) if highs else None,
            "low_24h": min(lows) if lows else None,
            "volume_24h": sum(volumes) if volumes else None,
            "price": closes[-1] if closes else None,
            "change_24h_pct": (
                ((closes[-1] - closes[0]) / closes[0] * 100)
                if len(closes) >= 2 and closes[0] not in (None, 0)
                else None
            ),
        }

        project = Project.objects.filter(code_id=code_id).first()
        if not project:
            return
        analysis["market_cap"] = project.market_cap_dict.get("spot")
        project.extra_info["analysis"] = analysis
        project.save(update_fields=["extra_info"])
        _analysis_sync_cache[code_id] = now_ts
        logger.info(f"已回写 24h 统计 code_id={code_id}")
    except Exception as e:
        logger.warning(f"回写 24h 统计失败 code_id={code_id}: {e}")


class ProjectListResource(Resource):
    RequestSerializer = ProjectSerializer

    def perform_request(self, validated_data):
        """处理业务逻辑"""
        # 这里实现具体的业务逻辑
        return GateService().get_project_all(**validated_data)


class ProjectKlineResource(Resource):
    RequestSerializer = ProjectKlineSerializer

    def perform_request(self, validated_data, **kwargs):
        data = GateService().get_kline_all(validated_data)
        # 每次请求 K 线时，复用本次已返回的 K 线数据更新一次 Project 表的 24h 统计
        code_id = validated_data.get("code_id")
        if code_id:
            _sync_project_analysis(data, code_id)
        return data
