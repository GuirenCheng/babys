# babys 母婴商城 —— 微服务 + Redis + 负载均衡 + Consul 服务注册

原为 Django REST framework 单体项目，现已拆分为三个独立可部署的微服务，并引入 Redis、Nginx 负载均衡与 Consul 服务注册发现。

## 架构

```
浏览器/前端
    │
    ▼
Nginx (:80，反向代理 + 负载均衡)
    ├── /api/v1/home/        → gateway 服务（gateway-1 / gateway-2）
    ├── /api/v1/commodity/*  → commodity 服务（commodity-1 / commodity-2）
    └── /api/v1/shopper/*    → user 服务（user-1 / user-2）
    ├── /admin/              → user 服务
    └── /media/              → Nginx 直接提供静态资源
            │
            ▼
    Redis（缓存+Session+锁）  MySQL（共享库）  Consul（服务注册中心）
```

- **微服务**：`gateway`（网关/首页聚合，通过 HTTP 调用 commodity）、`commodity`（商品）、`user`（用户/购物车/订单/支付）。用环境变量 `SERVICE_ROLE` 区分同一份代码跑成不同服务。
- **Redis**：`django-redis` 作为缓存 + Session 后端（跨服务共享登录态/收藏/支付信息），支付接口用 `cache.add`（SET NX）实现分布式锁。
- **负载均衡**：Nginx `upstream` 每个服务 2 个实例 round-robin 分发，响应头 `X-Served-By` 标识处理实例。
- **Consul 服务注册发现**：每个服务实例启动时向 Consul 注册并附健康检查，退出时注销；gateway 调用商品服务时通过 Consul 动态发现健康实例（不再写死地址）。Consul UI：`http://localhost:8500/ui`。

## 启动（Docker Compose）

前置：已安装 Docker Desktop。

1. 准备环境变量（首次）：复制 `.env.example` 为 `.env` 并填入真实密钥/密码（`.env` 已被 gitignore，不会提交）。

```bash
cp .env.example .env   # Windows 可直接复制后重命名
```

> 不创建 `.env` 也能启动，此时数据库密码与 SECRET_KEY 使用占位默认值 `changeme`（仅适合本地演示）。

2. 启动：

```bash
docker compose up --build -d
```

首次启动时 MySQL 会通过 `babys.sql` 自动建表并灌入数据，无需手动 `migrate`。

## 验证

```bash
# 1. 商品接口正常
curl http://localhost/api/v1/commodity/list/

# 2. 负载均衡：连续请求观察 X-Served-By 在 commodity-1 / commodity-2 间轮换
for i in 1 2 3 4; do curl -sI http://localhost/api/v1/commodity/list/ | grep -i x-served-by; done

# 3. 网关聚合：返回商品首页数据，且带 "aggregated-by-gateway" 标记
curl http://localhost/api/v1/home/

# 4. Redis 生效：能看到 session / 缓存 / 锁相关 key
docker compose exec redis redis-cli keys '*'

# 5. Consul 服务注册：三个服务已注册、健康状态可见
curl http://localhost:8500/v1/catalog/services
curl http://localhost:8500/v1/health/service/commodity

# 6. 服务发现 + 故障转移：停掉一个 commodity 实例，首页仍可用（gateway 自动切换到健康实例）
docker compose stop commodity-2
curl http://localhost/api/v1/home/
docker compose start commodity-2

# 7. 分布式锁：支付接口并发重复提交时，后续请求返回"请勿重复提交订单"

# 8. 跨服务 Session：登录后访问商品详情，收藏状态(likes)能跨服务保持
```

## 本地开发（不使用 Docker）

需本地启动 MySQL（库名 `babys`）与 Redis（127.0.0.1:6379），并**分多个终端**跑三个服务：

```bash
pip install -r requirements.txt

# 终端1：商品服务
SERVICE_ROLE=commodity python manage.py runserver 8001
# 终端2：用户/订单服务
SERVICE_ROLE=user python manage.py runserver 8002
# 终端3：网关服务（首页聚合，通过 Consul 发现商品服务）
SERVICE_ROLE=gateway python manage.py runserver 8000
```

`SERVICE_ROLE` 默认 `gateway`；数据库/Redis 连接地址均通过环境变量覆盖，默认值与原项目一致。若只跑单个服务调试，直接 `python manage.py runserver` 即可（角色默认 gateway）。

> 本地想体验 Consul：先 `consul agent -dev` 启动本地 Consul，再设 `CONSUL_HTTP_ADDR=http://127.0.0.1:8500` 运行服务。未起 Consul 时，gateway 会回退到 `COMMODITY_HOME_URL`（默认 http://127.0.0.1:8000/api/v1/commodity/home/），不阻塞本地开发。

## 关键配置说明

| 环境变量 | 说明 | 默认 |
|---|---|---|
| `SERVICE_ROLE` | 服务角色：gateway / commodity / user | gateway |
| `SECRET_KEY` | Django 密钥（建议放 `.env`） | django-insecure-REPLACE-ME-IN-PRODUCTION |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | MySQL 连接（`DB_PASSWORD` 放 `.env`） | 127.0.0.1 / 3306 / babys / root / (见 .env) |
| `REDIS_URL` | Redis 地址 | redis://127.0.0.1:6379/1 |
| `CONSUL_HTTP_ADDR` | Consul 地址 | http://127.0.0.1:8500 |
| `PORT` | 服务对外端口（注册到 Consul 的端口） | 8000 |
| `COMMODITY_HOME_URL` | gateway 的商品首页数据源地址（仅作 Consul 不可用时的回退） | http://127.0.0.1:8000/api/v1/commodity/home/ |

> 提示：`shopper` 服务因购物车外键与序列化嵌套引用了 `commodity` 模型，故 `user` 角色额外安装了 `commodity` app，这是全项目唯一的跨服务模型耦合（`db_constraint=False`，无物理外键）。
