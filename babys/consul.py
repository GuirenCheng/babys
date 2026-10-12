import itertools
import json
import os
import threading
import time
import urllib.request

# Consul 地址，默认本地，Docker 内为 http://consul:8500
CONSUL_HTTP_ADDR = os.environ.get('CONSUL_HTTP_ADDR', 'http://127.0.0.1:8500')


def _request(method, path, payload=None, timeout=5):
    url = CONSUL_HTTP_ADDR + path
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8')


def register(service, service_id, host, port, health_path='/health/'):
    '''向 Consul 注册一个服务实例，并附带 HTTP 健康检查'''
    payload = {
        'ID': service_id,
        'Name': service,
        'Address': host,
        'Port': int(port),
        'Tags': ['django', service],
        'Check': {
            'HTTP': f'http://{host}:{port}{health_path}',
            'Interval': '10s',
            'Timeout': '3s',
            # 放宽到 2 分钟，避免首次启动时 MySQL 还在初始化导致实例被过早注销
            'DeregisterCriticalServiceAfter': '2m',
        },
    }
    _request('PUT', '/v1/agent/service/register', payload)


def deregister(service_id):
    '''服务退出时向 Consul 注销'''
    try:
        _request('PUT', f'/v1/agent/service/deregister/{service_id}')
    except Exception:
        pass


_instances_cache = {}          # service_name -> (monotonic_time, [host:port, ...])
_INSTANCES_CACHE_TTL = 30      # 健康实例列表缓存时长（秒），避免每次请求都打 Consul


def get_healthy_instances(service_name):
    '''从 Consul 获取某服务的所有健康实例，返回 ['host:port', ...]；带短 TTL 缓存。'''
    now = time.monotonic()
    cached = _instances_cache.get(service_name)
    if cached and now - cached[0] < _INSTANCES_CACHE_TTL:
        return cached[1]
    url = f'{CONSUL_HTTP_ADDR}/v1/health/service/{service_name}?passing=true'
    with urllib.request.urlopen(url, timeout=5) as resp:
        entries = json.loads(resp.read().decode('utf-8'))
    instances = [f"{e['Service']['Address']}:{e['Service']['Port']}" for e in entries]
    _instances_cache[service_name] = (now, instances)
    return instances


_rr_lock = threading.Lock()
_rr_cycles = {}


def get_service_url(service_name, path):
    '''服务发现 + 简单轮询，返回一个可用的服务 URL；无健康实例时返回 None'''
    try:
        instances = get_healthy_instances(service_name)
    except Exception:
        return None
    if not instances:
        return None
    key = tuple(sorted(instances))
    with _rr_lock:
        cycle = _rr_cycles.get(key)
        if cycle is None:
            cycle = itertools.cycle(instances)
            _rr_cycles[key] = cycle
        return f'http://{next(cycle)}{path}'
