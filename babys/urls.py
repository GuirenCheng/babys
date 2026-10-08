import socket

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.db import connections
from django.core.cache import cache
from django.http import JsonResponse


def health(request):
    '''
    健康检查：供 Consul 轮询，检查数据库与 Redis 是否可用。
    任一依赖不可用时返回 503，Consul 据此将实例标记为不健康。
    '''
    db_ok, redis_ok = True, True
    try:
        connections['default'].ensure_connection()
    except Exception:
        db_ok = False
    try:
        cache.set('health_check', '1', timeout=10)
    except Exception:
        redis_ok = False
    status = 200 if (db_ok and redis_ok) else 503
    return JsonResponse({
        'status': 'ok' if status == 200 else 'degraded',
        'service': settings.SERVICE_ROLE,
        'host': socket.gethostname(),
        'db': db_ok,
        'redis': redis_ok,
    }, status=status)


urlpatterns = [
    path('admin/', admin.site.urls),
    # 健康检查端点（所有服务共享，供 Consul 探活）
    path('health/', health),
    # 配置媒体资源的路由信息
    re_path('media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}, name='media'),
    # 定义静态资源的路由信息
    re_path('static/(?P<path>.*)', serve, {'document_root': settings.STATIC_ROOT}, name='static'),
]

# 根据 SERVICE_ROLE 挂载对应服务的路由，实现微服务拆分
if settings.SERVICE_ROLE == 'gateway':
    urlpatterns += [path('api/v1/', include(('gateway.urls', 'gateway'), namespace='gateway'))]
elif settings.SERVICE_ROLE == 'commodity':
    urlpatterns += [path('api/v1/commodity/', include(('commodity.urls', 'commodity'), namespace='commodity'))]
elif settings.SERVICE_ROLE == 'user':
    urlpatterns += [path('api/v1/shopper/', include(('shopper.urls', 'shopper'), namespace='shopper'))]

# 设置404和500
from gateway.views import page_not_found, page_error

handler404 = page_not_found
handler500 = page_error
