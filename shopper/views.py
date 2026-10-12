import json
import uuid
from django.contrib.auth import logout, login, authenticate
from django.core.cache import cache
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import *
from .form import *
from .pays_new import get_pay
from .serializers import OrderInfosSerializer, CartInfosSerializer


class MySessionAuthentication(SessionAuthentication):
    '''
    自定义SessionAuthentication，取消CSRF验证
    '''
    def authenticate(self, request):
        user = getattr(request._request, 'user', None)
        if not user or not user.is_active:
            return None
        return (user, None)


class loginView(APIView):
    '''
    用户登录与注册
    '''
    # 取消所有认证
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        context = {'state': 'fail', 'msg': '注册或登录失败'}
        json_str = json.loads(request.body.decode())
        infos = LoginModelForm(data=json_str)
        d = infos.data
        username = d['username']
        password = d['password']
        last_login = ''
        # 用户存在则进行登录验证
        if User.objects.filter(username=username).first():
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                last_login = user.last_login
                context = {'state': 'success', 'msg': '登录成功'}
        else:
            # 用户不存在进行用户注册
            context = {'state': 'success', 'msg': '注册成功'}
            d = dict(username=username, password=password, is_staff=1, is_active=1)
            user = User.objects.create_user(**d)
            user.save()
            login(request, user)
        context['username'] = username
        context['last_login'] = last_login
        return Response(context)


class logoutView(APIView):
    '''
    退出用户登录
    '''
    authentication_classes = [MySessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        context = {'state': 'fail', 'msg': '退出失败'}
        # 使用内置函数logout退出用户登录状态
        if request.user.username:
            logout(request)
            context = {'state': 'success', 'msg': '退出成功'}
        return Response(context)


class shopperView(APIView):
    '''
    个人中心
    '''
    authentication_classes = [MySessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = {'state': 'success', 'msg': '获取成功', 'data': {}}
        t = request.GET.get('t', '')
        payTime = request.session.get('payTime', '')
        # 从Session获取并处理已支付的订单信息，幂等写入订单信息表（out_trade_no 唯一去重）
        if t and payTime and t == payTime:
            payInfo = request.session.get('payInfo', '')
            if payInfo:
                try:
                    OrderInfos.objects.get_or_create(out_trade_no=t, defaults=payInfo)
                except IntegrityError:
                    # 并发下 get_or_create 的竞态兜底：唯一约束已拦截，忽略重复
                    pass
            del request.session['payTime']
            del request.session['payInfo']
        # 根据当前用户查询用户所有订单信息
        orders = OrderInfos.objects.filter(user_id=request.user.id).order_by('-created').all()
        context['data']['orders'] = OrderInfosSerializer(instance=orders, many=True).data
        return Response(context)


class shopcartView(APIView):
    '''
    GET：获取购物车列表
    POST：商品加入购物车
    '''
    authentication_classes = [MySessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = {'state': 'success', 'msg': '获取成功', 'data': []}
        # 根据当前用户信息查找对应购物车信息
        c = CartInfos.objects.filter(user_id=request.user.id).all()
        context['data'] = CartInfosSerializer(instance=c, many=True).data
        return Response(context)

    def post(self, request):
        context = {'state': 'fail', 'msg': '加购失败'}
        json_str = json.loads(request.body.decode())
        id = json_str.get('id', '')
        quantity = json_str.get('quantity', 1)
        userID = request.user.id
        commodityInfos = CommodityInfos.objects.filter(id=id).first()
        # 根据请求信息写入购物车
        if id and commodityInfos and quantity:
            d = dict(commodityInfos_id=commodityInfos, user_id=userID, quantity=quantity)
            f = dict(commodityInfos_id=commodityInfos, user_id=userID)
            CartInfos.objects.update_or_create(d, **f)
            context = {'state': 'success', 'msg': '加购成功'}
        return Response(context)


class paysView(APIView):
    '''
    支付接口
    '''
    authentication_classes = [MySessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        context = {'state': 'fail', 'msg': '支付失败', 'data': ''}
        json_str = json.loads(request.body.decode())
        total = json_str.get('total', 0)
        total = float(str(total).replace('￥', ''))
        if total:
            user_id = request.user.id
            # 基于 Redis 的分布式锁，防止并发重复提交订单（cache.add 底层为 SET NX）
            # 锁靠短 TTL 自动过期做按用户去抖，不手动删除；否则锁会在请求内即释放、形同虚设
            lock_key = f'pay_lock:{user_id}'
            if not cache.add(lock_key, '1', timeout=10):
                context = {'state': 'fail', 'msg': '请勿重复提交订单', 'data': ''}
                return Response(context)
            out_trade_no = uuid.uuid4().hex
            payInfo = dict(price=total, user_id=user_id, state='已支付')
            request.session['payInfo'] = payInfo
            request.session['payTime'] = out_trade_no
            # return_url为前端的路由地址
            # 如果无法确认路由地址，前端可以通过请求参数传递
            return_url = 'http://localhost:8010/#/shopper'
            data = get_pay(out_trade_no, total, return_url)
            context = {'state': 'success', 'msg': '支付成功', 'data': data}
        return Response(context)


class deleteView(APIView):
    '''
    购物车删除商品
    '''
    authentication_classes = [MySessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        context = {'state': 'success', 'msg': '删除成功'}
        json_str = json.loads(request.body.decode())
        username = json_str.get('username', '')
        carId = json_str.get('carId', '')
        # 根据请求信息删除购物车信息
        if username:
            CartInfos.objects.filter(user_id=request.user.id).delete()
        elif carId:
            CartInfos.objects.filter(id=carId).delete()
        else:
            context = {'state': 'fail', 'msg': '删除失败'}
        return Response(context)
