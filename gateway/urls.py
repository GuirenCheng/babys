from django.urls import path
from .views import indexView

urlpatterns = [
    path('home/', indexView.as_view(), name='index'),
]
