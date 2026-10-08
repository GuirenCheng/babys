import os
from pathlib import Path

import pymysql
pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 从 .env 加载环境变量（真实密钥放 .env，不提交到仓库）
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')


# 微服务角色：gateway(网关/首页聚合) | commodity(商品) | user(用户/购物车/订单/支付)
SERVICE_ROLE = os.environ.get('SERVICE_ROLE', 'gateway')


# SECURITY WARNING: keep the secret key used in production secret!
# 真实密钥从环境变量读取（见 .env.example），此处仅为开发占位默认值
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-REPLACE-ME-IN-PRODUCTION')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '1') == '1'

ALLOWED_HOSTS = ['*']


# 各服务共同依赖的基础应用
BASE_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
]

# 各服务按角色安装自身的业务应用
# user 服务额外安装 commodity：shopper 的购物车外键引用 CommodityInfos（db_constraint=False）
ROLE_APPS = {
    'gateway': ['gateway'],
    'commodity': ['commodity'],
    'user': ['shopper', 'commodity'],
}

INSTALLED_APPS = BASE_APPS + ROLE_APPS.get(SERVICE_ROLE, ['gateway'])

MIDDLEWARE = [
    'babys.middleware.ServerIdentityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 添加中间件LocaleMiddleware
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'babys.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'babys.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'babys'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}


# Redis 缓存
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'babys',
    }
}

# Session 存储到 Redis，实现多服务、多实例之间共享登录态/收藏/支付信息
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# gateway 服务调用商品服务的首页数据源地址（Docker 内走 nginx，本地走直连）
COMMODITY_HOME_URL = os.environ.get(
    'COMMODITY_HOME_URL', 'http://127.0.0.1:8000/api/v1/commodity/home/'
)


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_ROOT = BASE_DIR / 'static'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    # 配置分页器
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # 每页的数据量
    'PAGE_SIZE': 6,
    # 用户认证方式
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}

# 设置跨域访问
# 指定所有域名(IP)都可以访问，默认为False
CORS_ORIGIN_ALLOW_ALL = True
# 设置允许携带Cookie
CORS_ALLOW_CREDENTIALS = True
# 设置允许访问的域名(IP)
# 如果CORS_ORIGIN_ALLOW_ALL=True则无需设置
CORS_ORIGIN_WHITELIST = []
# 允许执行的请求方式
CORS_ALLOW_METHODS = (
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'VIEW',
)
# 允许执行的请求头
CORS_ALLOW_HEADERS = (
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
)
