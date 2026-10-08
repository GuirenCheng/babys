import socket


class ServerIdentityMiddleware:
    '''
    给响应加 X-Served-By 响应头，标识本次请求由哪个容器/实例处理。
    用于验证 Nginx 负载均衡是否在多个实例间轮询分发。
    '''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Served-By'] = socket.gethostname()
        return response
