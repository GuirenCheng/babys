import json
from django.core.cache import cache
from django.db.models import F
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *


class homeView(APIView):
    '''
    首页数据源：供 gateway 服务通过 HTTP 调用。
    使用 Redis 缓存聚合结果，避免每次请求都查库。
    '''
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        cache_key = 'commodity:home'
        data = cache.get(cache_key)
        if data is None:
            data = {'state': 'success', 'msg': '获取成功', 'data': {}}
            data['data']['commodityInfos'] = []
            c = CommodityInfos.objects.order_by('-sold')[:8].all()
            data['data']['commodityInfos'].append(CommodityInfosSerializer(instance=c[0:4], many=True).data)
            data['data']['commodityInfos'].append(CommodityInfosSerializer(instance=c[4:8], many=True).data)
            types = Types.objects.all()
            # 儿童服饰
            cl = [x.seconds for x in types if x.firsts == '儿童服饰']
            clothes = CommodityInfos.objects.filter(types__in=cl).order_by('-sold')[:5].all()
            data['data']['clothes'] = CommodityInfosSerializer(instance=clothes, many=True).data
            # 奶粉辅食
            fl = [x.seconds for x in types if x.firsts == '奶粉辅食']
            food = CommodityInfos.objects.filter(types__in=fl).order_by('-sold')[:5].all()
            data['data']['food'] = CommodityInfosSerializer(instance=food, many=True).data
            # 儿童用品
            gl = [x.seconds for x in types if x.firsts == '儿童用品']
            goods = CommodityInfos.objects.filter(types__in=gl).order_by('-sold')[:5].all()
            data['data']['goods'] = CommodityInfosSerializer(instance=goods, many=True).data
            cache.set(cache_key, data, timeout=60)
        return Response(data)


class commodityView(APIView):
    '''
    商品列表页
    '''
    authentication_classes = []
    permission_classes = []

    # GET请求
    def get(self, request):
        types = request.GET.get('types', '')
        search = request.GET.get('search', '')
        sort = request.GET.get('sort', 'sold')
        context = {'state': 'success', 'msg': '获取成功', 'data': {}}
        context['data']['types'] = []
        # 商品类型下拉数据（缓存，基本不变化）
        types_cache_key = 'commodity:types'
        types_data = cache.get(types_cache_key)
        if types_data is None:
            types_data = []
            firsts = Types.objects.values_list('firsts', flat=True).distinct()
            for f in firsts:
                t = Types.objects.filter(firsts=f).values_list('seconds', flat=True).all()
                types_data.append(dict(name=f, value=list(t)))
            cache.set(types_cache_key, types_data, timeout=300)
        context['data']['types'] = types_data
        cf = CommodityInfos.objects.all()
        if types:
            cf = cf.filter(types=types)
        if sort:
            cf = cf.order_by('-' + sort)
        if search:
            cf = cf.filter(name__contains=search)
        count = cf.count()
        # 分页查询，需要在settings.py设置REST_FRAMEWORK属性
        pg = PageNumberPagination()
        p = pg.paginate_queryset(queryset=cf, request=request)
        # 将分页后的数据传递MySerializer，生成JSON数据对象
        c = CommodityInfosSerializer(instance=p, many=True)
        # 获取前一页、后一页和总页的页数
        pageCount = pg.page.paginator.num_pages
        try:
            next = pg.page.next_page_number()
        except:
            next = pageCount
        try:
            previous = pg.page.previous_page_number()
        except:
            previous = 0
        d = dict(data=c.data, previous=previous,
                 next=next, count=count, pageCount=pageCount)
        context['data']['commodityInfos'] = d
        return Response(context)


class detailView(APIView):
    '''
    商品详情页
    '''
    authentication_classes = []
    permission_classes = []

    # GET请求
    def get(self, request, id):
        context = {'state': 'success', 'msg': '获取成功', 'data': {}}
        # 商品与推荐数据缓存（likes 为用户相关，不缓存，每次按 session 计算）
        cache_key = f'commodity:detail:{id}'
        detail_data = cache.get(cache_key)
        if detail_data is None:
            c = CommodityInfos.objects.filter(id=id).first()
            detail_data = {
                'commoditys': CommodityInfosSerializer(instance=c).data,
                'recommend': CommodityInfosSerializer(
                    instance=CommodityInfos.objects.exclude(id=id).order_by('-sold')[:5], many=True
                ).data,
            }
            cache.set(cache_key, detail_data, timeout=60)
        context['data']['commoditys'] = detail_data['commoditys']
        context['data']['recommend'] = detail_data['recommend']
        if id in request.session.get('likes', []):
            context['data']['likes'] = True
        else:
            context['data']['likes'] = False
        return Response(context)


class collectView(APIView):
    '''
    商品收藏
    '''
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        json_str = json.loads(request.body.decode())
        id = json_str.get('id', '')
        context = {'state': 'fail', 'msg': '收藏失败'}
        likes = request.session.get('likes', [])
        if id and not int(id) in likes:
            # 对商品的收藏数量执行自增加1
            CommodityInfos.objects.filter(id=id).update(likes=F('likes') + 1)
            # 根据Session信息判断用户是否已收藏
            request.session['likes'] = likes + [int(id)]
            # 收藏数变化，清理商品相关缓存
            cache.delete_pattern('commodity:*')
            context = {'state': 'success', 'msg': '收藏成功'}
        return Response(context)
