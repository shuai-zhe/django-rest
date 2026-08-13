import datetime
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
