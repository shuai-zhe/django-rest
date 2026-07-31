import time
from distutils.log import warn
from idlelib.colorizer import prog_group_name_to_tag
from urllib import request

from rest_framework.serializers import Serializer


def serializer_formatter(serializer: Serializer):
    """
    required_filed:
    {'codeId': [ErrorDetail(string='This field is required.', code='required')]}
    all_filed  = serializer.fields
    {'name': CharField(label='项目名称', max_length=100, required=False), 'display_name': CharField(label='项目显示名称', max_length=100, required=False), 'codeId': CharField(label='项目代码', max_length=100, required=True)}
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
