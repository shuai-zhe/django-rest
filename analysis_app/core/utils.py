import datetime
import re
import time

from rest_framework.serializers import Serializer


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
