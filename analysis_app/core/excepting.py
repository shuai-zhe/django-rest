from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class BaseException(Exception):
    """
    基础异常类
    :param code: 错误码
    :param message: 错误信息
    :param data: 错误数据
    """
    status_code = 500 # 默认http状态码
    code =100 # 默认错误码
    default_message = _("服务器未知错误")  # 默认错误信息
    def __init__(self, message=None, code=None,data=None):
        """
        :param message: 错误信息
        :param code: 错误码
        :param data: 错误数据
        """
        if message is None:
            message = self.default_message
        self.detail = message
        self.message = message
        if code is not None:
            self.code = code

        if data is not None:
            self.data = data


    def __str__(self):
        return str(self.message)



class CommonException(BaseException):
    status_code = 500
    default_detail = _("服务器错误")
    code = 500

class ValidateErrorException(BaseException):
    status_code = 400
    default_detail = _("数据校验失败")
    code = 400