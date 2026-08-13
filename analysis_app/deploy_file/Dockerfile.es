# Elasticsearch + IK 中文分词插件
# 版本必须与 ES 主版本严格一致，否则启动失败
FROM docker.elastic.co/elasticsearch/elasticsearch:8.13.4

# 使用 infinilabs 官方插件 CDN 下载与 ES 同版本的 analysis-ik 预编译包
# （已验证该地址返回 200；若服务器访问此域名受限，可改用
#  GitCode 镜像：https://gitcode.net/mirrors/infinilabs/analysis-ik/-/releases/download/v8.13.4/elasticsearch-analysis-ik-8.13.4.zip）
# --batch 非交互自动同意许可
RUN elasticsearch-plugin install --batch \
    https://release.infinilabs.com/analysis-ik/stable/elasticsearch-analysis-ik-8.13.4.zip
