import requests
from requests.adapters import HTTPAdapter
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from babys.consul import get_service_url

# 复用连接池，避免每次首页聚合请求都新建 TCP 连接
_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=5, pool_maxsize=20, max_retries=1)
_session.mount('http://', _adapter)
_session.mount('https://', _adapter)


class indexView(APIView):
    '''
    首页：网关聚合商品服务的首页数据。
    通过 Consul 服务发现动态获取商品服务实例，体现微服务之间的服务间通信，不直接依赖其模型。
    '''
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # 通过 Consul 服务发现拿一个健康的商品服务实例
        url = get_service_url('commodity', '/api/v1/commodity/home/')
        if url is None:
            # 回退：本地开发未起 Consul 时用固定地址
            url = getattr(settings, 'COMMODITY_HOME_URL', '')
        if not url:
            return Response({'state': 'fail', 'msg': '商品服务不可用'}, status=503)
        try:
            resp = _session.get(url, timeout=5)
        except requests.RequestException as e:
            return Response(
                {'state': 'fail', 'msg': '商品服务不可用', 'error': str(e)},
                status=502,
            )
        if resp.status_code != 200:
            return Response(
                {'state': 'fail', 'msg': '商品服务返回错误', 'status': resp.status_code},
                status=resp.status_code,
            )
        data = resp.json()
        data['gateway'] = 'aggregated-by-gateway'
        return Response(data)


def page_not_found(request, exception):
    data = {'state': 'fail', 'msg': '页面丢失了'}
    return Response(data, status=404)


def page_error(request):
    data = {'state': 'fail', 'msg': '服务器异常'}
    return Response(data, status=500)
