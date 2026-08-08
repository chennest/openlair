# 后端架构（backend/）

## 概述

- 技术栈：FastAPI + SQLAlchemy 2 + SQLite（可通过 `DATABASE_URL` 换 MySQL/PostgreSQL）+ PyJWT + Alembic + pydantic-settings，`uv` 管理（CPython 3.14）。
- 目录结构对齐官方 [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)：`backend/app`（flat layout，包名 `app`）+ `backend/migrations` + `backend/tests`。
- 核心原则：**后端与前端 mock 层（`lairweb/mock/`）的 API 契约完全一致**——统一信封、字段命名（camelCase）、错误语义，切换 Vite proxy 目标即可在 mock 与真实后端之间切换。

## 目录结构

```text
backend/
├── pyproject.toml            # uv 项目（openlair-backend，hatchling packages=["app"]）
├── alembic.ini
├── .env / .env.example       # OPENLAIR_JWT_SECRET、DATABASE_URL（模板含 3 种数据库示例）
├── app/                      # 源码包（包名 app）
│   ├── main.py               # create_app()：组装 engine/seed/仓储/服务，挂 /api 路由
│   ├── seed.py               # 幂等 seed：3 测试账号、2 账本、16 分类、演示数据
│   ├── api/v1/
│   │   ├── router.py         # APIRouter(prefix="/api")，汇总 8 个子路由
│   │   ├── deps.py           # get_current_user：Bearer 验签 + 过期 + 黑名单
│   │   ├── schemas.py        # Pydantic 请求模型（camelCase，与前端契约一致）
│   │   └── endpoints/        # auth / books / ledger / modules（薄 HTTP 层）
│   ├── core/
│   │   ├── config.py         # Settings(BaseSettings)：OPENLAIR_JWT_SECRET / DATABASE_URL
│   │   ├── envelope.py       # {code, message, data} 统一信封 + 异常处理器
│   │   └── security.py       # JWT 签发/验签 + scrypt 密码哈希
│   ├── db/
│   │   ├── base.py           # Base(DeclarativeBase)
│   │   └── session.py        # engine / session_factory 工厂
│   ├── models/               # 11 张 ORM 表，一表一文件
│   ├── repositories/         # SQLAlchemy 持久化（唯一数据访问路径）
│   └── services/             # 业务逻辑 + DTO（auth / books / ledger / modules）
├── migrations/               # Alembic（versions/ 下每变更一个迁移文件）
├── tests/                    # test_business_api.py（17 项全链路）+ test_security.py（3 项）
└── data/                     # SQLite 数据文件（本地，gitignore）
```

## 分层架构

```text
HTTP 请求
  -> api/v1/endpoints     薄层：取参、调用服务、包信封
  -> services             业务逻辑 + DTO，可脱离 HTTP 直接单测
  -> repositories         SQLAlchemy 持久化（唯一数据访问路径）
  -> models               ORM 表定义
```

- **endpoints 只做转发**：参数校验交给 Pydantic schema，业务规则全部下沉到 services。
- **services 可脱离 HTTP 调用**：构造注入 repositories，不依赖 FastAPI Request（单测友好）。
- **repositories 是唯一数据访问路径**：禁止在 endpoints/services 里直接写 SQL/ORM 查询，保证未来换数据库只改这一层。
- **组装在 main.py**：`create_app(database_url=None)` 创建 engine → seed → 实例化仓储与服务 → 挂到 `app.state.*`；endpoints 通过 `request.app.state` 取服务，FastAPI 依赖只承担鉴权（`get_current_user`）。测试通过传 `database_url` 注入隔离数据库。

## API 契约（与前端 mock 完全一致）

统一信封，所有接口（含错误）都包一层：

```json
{ "code": 200, "message": "成功", "data": { ... } }
```

- 成功：`code=200`，`data` 为业务数据。
- 失败：`code` = HTTP 状态码（401/403/404/409/422/500...），`message` 为人类可读错误，`data=null`。
- **HTTP 状态码与 `code` 保持一致**。
- 错误处理链（`core/envelope.py`）：`ApiError(status, message)` 业务错误（401 自动带 `WWW-Authenticate: Bearer`）→ `HTTPException` 转换 → 未捕获异常兜底 500「服务器内部错误」。
- 鉴权：`Authorization: Bearer <token>`；未登录 / token 无效 / 过期 / 已登出 → 401「未登录或登录已过期，请重新登录」。
- 字段命名 camelCase（`bookId`、`categoryId`、`pageSize`），与 mock 层逐字段对齐。

## 认证与安全（core/security.py）

- **JWT HS256**（PyJWT，RFC 7519）：签发 claims `{ sub: 用户id, iat, exp: now+7天, jti }`；验签 `jwt.decode(token, secret, algorithms=["HS256"])`。
- **登出黑名单**：登出时把 `jti` 写入 `revoked_tokens` 表（等价于 Redis 黑名单方案），后续携带该 token 的请求一律 401。
- **密码哈希**：`hashlib.scrypt`（n=2^14, r=8, p=1, dklen=64），存储格式 `scrypt$salt$hash`，比较用 `hmac.compare_digest`。
- **密钥来源**：`OPENLAIR_JWT_SECRET`（进程环境 → `backend/.env` → 开发默认值），HS256 要求 ≥ 32 字节；生产必须显式配置。
- 鉴权依赖 `get_current_user`（api/v1/deps.py）执行：验签 → 过期检查 → 黑名单检查 → 用户存在性检查，任一失败统一 401。

## 数据模型（11 张表，models/）

| 表 | 说明 |
|---|---|
| `users` | 用户：id（自增 int）、name、email（唯一）、password_hash |
| `books` | 账本：name、type（personal/shared）、owner_id |
| `book_members` | 账本成员：book_id + user_id，多对多 |
| `categories` | 分类：16 个固定项——支出 id 1-10（餐饮/交通/购物/居住/娱乐/医疗/学习/人情/通讯/其他），收入 id 11-16（工资/奖金/理财/礼金/退款/其他） |
| `transactions` | 流水：book_id、type（expense/income）、category、amount、date、note |
| `budgets` | 月预算：book_id + amount（每月一条） |
| `todos` | 待办：text、quadrant（四象限）、done、due |
| `events` | 日历日程：title、date、time、location、done |
| `notes` | 笔记：title、summary、tags（JSON） |
| `habits` | 习惯打卡：name、streak、week（7 天布尔数组） |
| `revoked_tokens` | JWT 登出黑名单：jti |

## API 端点清单（全部挂 `/api`，除 auth 均需 Bearer token）

### /api/auth
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /register | 注册（name/email/password） |
| POST | /login | 登录，返回 `{ token, user }` |
| POST | /logout | 登出，撤销当前 token（jti 入黑名单） |
| GET | /me | 当前用户信息 |

### /api/ledger
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /categories | 分类列表（带 type） |
| GET | /?bookId=&page=&pageSize= | 流水分页列表（按账本隔离，带 total） |
| POST | / | 记一笔（type/categoryId|category/amount/date/note/bookId） |
| PUT | /{transaction_id} | 改流水 |
| DELETE | /{transaction_id} | 删流水 |
| GET | /trend | 趋势统计（按日/月聚合支出收入） |
| GET | /budget?bookId= | 当月预算 |
| PUT | /budget | 设置预算 |

### /api/books
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | 我的账本列表 |
| POST | / | 创建账本（name/type） |
| POST | /{book_id}/members | 添加成员（userId 或 name 查找） |
| DELETE | /{book_id}/members/{user_id} | 移除成员 |

### /api/todo · /api/calendar · /api/notes · /api/habits
统一模式：`GET ""` 列表、`POST ""` 创建、`PUT /{id}` 更新、`DELETE /{id}` 删除（数据按用户隔离）。

### /api/overview
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | 首页总览：流水/待办/日程/习惯聚合数据 |

## 配置（pydantic-settings，core/config.py）

- `Settings(BaseSettings)` 字段：`jwt_secret`（别名 `OPENLAIR_JWT_SECRET`）、`database_url`（别名 `DATABASE_URL`）。
- 读取优先级：**进程环境 → `backend/.env` → 默认值**；`env_file` 指向项目根 `.env`（不读 `~/` 下的全局配置）。
- `.env.example` 提供 SQLite / MySQL（`mysql+pymysql://`）/ PostgreSQL（`postgresql+psycopg://`）三种连接串示例。

## 数据库与迁移

- **启动兜底**：`create_app` 内 `init_database`（create_all）+ 幂等 `seed`——新建空库自动建表并灌入测试账号（`test1/2/3@openlair.dev`，密码 `test123456`）与演示数据。
- **schema 演进走 Alembic**（`backend/migrations/`，env.py 从 Settings 读连接串、注册全部 ORM metadata）：
  - 生成：`uv run alembic revision --autogenerate -m "..."`（从 backend/ 执行）
  - 应用：`uv run alembic upgrade head`；回退：`uv run alembic downgrade -1`
  - 初始迁移 `7435700fd27f_initial_schema` 已包含全部 11 张表。
- 换库只需改 `DATABASE_URL`；Alembic 迁移同样适用 MySQL/PostgreSQL。

## 测试

- `backend/tests/`，命令 `uv run pytest`（当前 20 项全绿）。
- `test_business_api.py`（17 项）：全链路业务测试——注册/登录/登出、账本创建与成员、账本数据隔离、流水 CRUD、分类、趋势、预算、todo/calendar/notes/habits/overview；每项测试用独立临时 SQLite 文件，`create_app(database_url=...)` 注入。
- `test_security.py`（3 项）：JWT 密钥解析优先级（环境变量 > .env > 默认）与 `.env.example` 键完整性。
- 手工验收：`uv run uvicorn app.main:app --host 127.0.0.1 --port 8001` 后按契约调 `/api/auth/login` 等端点核对信封格式。

## 演进约束

- **契约同步**：任何接口变更必须 mock 层（`lairweb/mock/`）与后端同步修改，两端契约以本文档 + 测试为准。
- **schema 变更必须走 Alembic 迁移**，`create_all` 只负责新库兜底。
- 保持分层纪律：services 不含 HTTP 依赖，repositories 是唯一数据访问路径（换库不动业务层）。
- SQLite 适用早期单用户本地部署；未来多 worker 或写密集场景再评估 WAL/服务数据库。
- 后续方向（未实现）：主动提醒/每日总结等定时调度基础设施、生产环境密钥强制校验、多用户并发与锁行为。
