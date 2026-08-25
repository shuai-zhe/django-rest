import datetime
import logging
import re
import time

from rest_framework.serializers import Serializer

logger = logging.getLogger(__name__)

_ANALYSIS_SYNC_INTERVAL = 60  # 秒
_analysis_sync_cache = {}


def sync_project_analysis(data, code_id, model_class):
    """用本次 K 线请求已返回的数据计算 24h 统计并回写 Project/StockProject.extra_info.analysis。"""
    try:
        now_ts = time.time()
        # 缓存 key 加上 model_class 的名字，避免不同模块的 code_id 冲突
        cache_key = f"{model_class.__name__}_{code_id}"
        last_ts = _analysis_sync_cache.get(cache_key)
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
        volumes = [float(k["v"]) for k in window if k.get("v") is not None]
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

        project = model_class.objects.filter(code_id=code_id).first()
        if not project:
            return
        analysis["market_cap"] = project.market_cap_dict.get("spot")
        project.extra_info["analysis"] = analysis
        project.save(update_fields=["extra_info"])
        _analysis_sync_cache[cache_key] = now_ts
        logger.info(f"已回写 24h 统计 {model_class.__name__} code_id={code_id}")
    except Exception as e:
        logger.warning(f"回写 24h 统计失败 {model_class.__name__} code_id={code_id}: {e}")


def serializer_formatter(serializer: Serializer):
    """
    required_filed:
    {'codeId': [ErrorDetail(string='This field is required.', code='required')]}
    all_filed  = serializer.fields
    {'name': CharField(label='项目名称', max_length=100, required=False), 'display_name': CharField(label='项目显示名称',
     max_length=100, required=False), 'codeId': CharField(label='项目代码', max_length=100, required=True)}
    params
    {'name': 'a'}
    """
    required_filed = serializer.errors
    all_filed = serializer.fields
    params = serializer.get_initial()
    for filed_name, filed_value in required_filed.items():
        filed = all_filed[filed_name]
        label = filed.label or filed.field_name
        message = ""
        if filed_name not in params:
            if isinstance(filed_value, list):
                message = "".join([str(error) for error in filed_value])
            else:
                message = str(filed_value)

        return "{label}:{message}".format(label=label, message=message)
    return None


class GetSetBuild(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value


def io_error_reset(reset=0, sleep=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            error = ""
            for cnt in range(reset):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = e
                time.sleep(sleep)
            raise ValueError(error)

        return wrapper

    return decorator


def to_datetime(v):
    """统一把 ISO 字符串 / 时间戳(秒|毫秒) 转成 datetime；无法解析返回 None"""
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, (int, float)):
        # 毫秒级时间戳长度 ~13 位，秒级 ~10 位
        return datetime.datetime.fromtimestamp(v / 1000 if v > 1e11 else v)
    if isinstance(v, str):
        s = v.strip()
        # 去掉尾部的 Z，dateutil 也能解析，但保险起见统一处理
        try:
            return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def to_strftime(v, is_hms=False):
    """统一把 datetime 转成 strftime"""
    if is_hms:
        # 如果只是时分秒部分;自动填补当前日期；考虑如果数据发生延迟可能导致在0点左右的事项，如果补充的时间大于当前时间那么应该时间-1
        t = time.strftime(f"%Y-%m-%d {v}")
        now_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if t > now_time:
            t = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(
                days=1
            )
        return t.strftime("%Y-%m-%d %H:%M:%S")
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, str):
        if v.isdigit() or re.findall(r"\d+\.\d+", v):
            return to_strftime(float(v))
        # 检查是否日期格式
        vs = re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", v)
        if vs:
            return vs[0]
        raise ValueError("无法解析时间格式")

    return v
