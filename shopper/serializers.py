from rest_framework import serializers
from .models import *
# 定义ModelSerializer类
class CartInfosSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartInfos
        fields = '__all__'
        # 参数depth是根据外键关联实现序列化嵌套功能
        depth = 1

class OrderInfosSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfos
        fields = '__all__'
