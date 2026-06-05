from apis.cryptobubbles.default import _CryptobubblesApi
from gate.models import Project
# 筛选数据
base_project = [_ for _ in _CryptobubblesApi.get_project_all().json() if _["symbols"].get("gateio")]
for project in base_project:
    name = project["symbol"]
    display_name = project["name"]
    code_id = project["symbols"]["gateio"]