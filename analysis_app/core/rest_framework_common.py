from rest_framework.response import Response
# 自定义序列化器校验错误信息

def exception_handler(exc, context):
    return Response(data=exc.detail,status=exc.code)
