import requests


class RequestBase:
    def __init__(self, url: str, headers: dict = None, method: str = "GET"):
        self.url = url
        self.headers = headers or {'Accept': 'application/json', 'Content-Type': 'application/json'}
        self.method = method
        self.params = {}

    def request(self, params=None, method=None, **kwargs):
        method = method or self.method
        _request_params = {
            "url": self.url,
            "headers": self.headers,
            "method": method,
            **kwargs
        }
        if method == "GET":
            _request_params["params"] = params
        elif method == "POST":
            _request_params["data"] = params

        return requests.request(**_request_params)

    @staticmethod
    def set_params(params, exclude_none=True, exclude_empty=True):
        """
        过滤参数中的空值
        :param params: 参数字典
        :param exclude_none: 是否排除None值
        :param exclude_empty: 是否排除空字符串、0等空值
        :return: 过滤后的参数字典
        """
        if not params:
            return {}
        filtered_params = {}
        for key, value in params.items():
            # 排除None值
            if exclude_none and value is None:
                continue
            # 排除空值（空字符串、0等）
            if exclude_empty and value in ("", 0, [], {}, ()):
                continue
            filtered_params[key] = value
        return filtered_params

    def __call__(self, params: dict = None, *args, **kwargs):
        self.params = self.set_params(params)
        return self.request(*args, params=self.params, **kwargs)
