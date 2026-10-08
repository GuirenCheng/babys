from rest_framework import serializers
from .models import *
# 定义ModelSerializer类
class TypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Types
        fields = '__all__'

class CommodityInfosSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommodityInfos
        fields = '__all__'


