from apis.base import RequestBase

host = "https://cryptobubbles.net"
prefix = "/"

class CryptobubblesApi:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
            "Referer":"https://cryptobubbles.net/"
        }
        self.get_project_all = RequestBase(url=host+prefix+"/backend/data/bubbles1000.usd.json",headers=self.headers)

_CryptobubblesApi = CryptobubblesApi()