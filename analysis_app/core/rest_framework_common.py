from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from core.excepting import CommonException, ValidateErrorException


# 自定义序列化器校验错误信息
def exception_handler(exc, context):
    """
    自定义异常处理
    :param exc: 异常对象 继承 BaseException
    :param context: 请求上下文  # {'view': <gate.views.ProjectResource object at 0x00000198C5D873D0>, 'args': (), 'kwargs': {}, 'request': <rest_framework.request.Request: GET '/gate/project'>}
    :return: Response
    """
    common_exception = CommonException(message=str(exc))
    code = getattr(exc, "code", common_exception.code)
    detail = getattr(exc, "detail", common_exception.detail)
    message = getattr(exc, "default_detail", common_exception.default_detail)

    error = {"detail": detail, "message": message}
    return Response(data=error, status=code)


class APIRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        :param data: 响应数据
        :param accepted_media_type: 接受的媒体类型
        :param renderer_context: 渲染上下文
        :return: 响应数据
        """
        # 重写render方法
        response = renderer_context["response"]
        response_format = {
            "code": response.status_code,
            "data": data,
            "success": True,
            "message": "",
        }
        if response.status_code == 200:
            response_format["success"] = True
        else:
            response_format["success"] = False
            response_format["message"] = (
                response.data.get("message", "系统异常") + ":" + response.data.get("detail")
            )
            response_format["data"] = []
        return super(APIRenderer, self).render(
            response_format, accepted_media_type, renderer_context
        )
