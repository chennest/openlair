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
│   ├── models/               # 14 张 ORM 表，一表一文件
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
- **唯一的例外**：参数校验失败（422）走 FastAPI 默认的裸 `{"detail": [...]}`，不带信封——`envelope.py` 只注册了 `ApiError`/`HTTPException`/`Exception` 三个 handler，没有 `RequestValidationError`。客户端（`laircli/`）必须同时处理两种形状。
- 鉴权：两类等价凭证，任一即可（`api/v1/deps.py`）：`Authorization: Bearer <token>`（登录态，7 天，可登出撤销）与 `X-API-Key: ol_xxx`（用户级长效凭证，可独立撤销）。`X-API-Key` 优先，且它无效时**不会**回退去解 Bearer。未登录 / token 无效 / 过期 / 已登出 / Key 已撤销 → 401「未登录或登录已过期，请重新登录」。
- 字段命名 camelCase（`bookId`、`categoryId`、`pageSize`），与 mock 层逐字段对齐。

## 认证与安全（core/security.py）

- **JWT HS256**（PyJWT，RFC 7519）：签发 claims `{ sub: 用户id, iat, exp: now+7天, jti }`；验签 `jwt.decode(token, secret, algorithms=["HS256"])`。
- **登出黑名单**：登出时把 `jti` 写入 `revoked_tokens` 表（等价于 Redis 黑名单方案），后续携带该 token 的请求一律 401。
- **密码哈希**：`hashlib.scrypt`（n=2^14, r=8, p=1, dklen=64），存储格式 `scrypt$salt$hash`，比较用 `hmac.compare_digest`。
- **API Key**（`core/security.py` + `services/api_keys.py`）：明文 `ol_` + `secrets.token_urlsafe(32)`（共 46 字符，256bit 熵）；库中只存 SHA-256 十六进制，明文仅在 `POST /api/keys` 响应里下发一次；列表 DTO 只给 `prefix`（前 12 字符）供识别。每人最多 20 把有效 Key，撤销是软删（`revoked_at`）且立即生效；每次用 Key 认证成功都会刷 `last_used_at`。注意登出（`/api/auth/logout`）只拉黑 JWT，**不会**撤销 API Key。
- **密钥来源**：`OPENLAIR_JWT_SECRET`（进程环境 → `backend/.env` → 开发默认值），HS256 要求 ≥ 32 字节；生产必须显式配置。
- 鉴权依赖 `get_current_user`（api/v1/deps.py）执行：验签 → 过期检查 → 黑名单检查 → 用户存在性检查，任一失败统一 401。

## 数据模型（23 张表，models/）

| 表 | 说明 |
|---|---|
| `users` | 用户：id（自增 int）、name、email（唯一）、password_hash |
| `api_keys` | 用户级 API Key：user_id、name、key_hash（SHA-256）、prefix（前 12 字符）、last_used_at、revoked_at（软删即撤销） |
| `settings` | 系统设置 KV：key、value（如 `allow_register`，缺省按 `"0"` 处理） |
| `books` | 账本：name、type（personal/shared）、invite_code（共享账本邀请码，NULL=未生成，重置即覆盖失效） |
| `book_members` | 账本成员：book_id + user_id，多对多，role（owner/editor） |
| `categories` | 分类：16 个固定项——支出 id 1-10（餐饮/交通/购物/居住/娱乐/医疗/学习/人情/通讯/其他），收入 id 11-16（工资/奖金/理财/礼金/退款/其他） |
| `transactions` | 流水：book_id、type（**中文枚举 `收入`/`支出`**，写入时任何非「收入」的值都归一为「支出」）、category、amount、date、note |
| `budgets` | 月预算：book_id + amount（每月一条） |
| `todos` | 待办：text、quadrant（四象限）、done、due |
| `events` | 日历日程：title、date、time、location、done |
| `notes` | 笔记：title、summary、tags（JSON） |
| `habits` | 习惯打卡：name、streak、week（7 天布尔数组） |
| `revoked_tokens` | JWT 登出黑名单：jti |
| `assistant_sessions` | AI 助手会话（每用户单持久线程）：title、summary（压缩检查点）、summary_through_id |
| `assistant_messages` | AI 助手消息（transcript）：role(user/assistant)、type(text/confirm_request/tool_result)、content、meta |
| `assistant_plans` | AI 记账计划执行日志：plan_id、args、status(pending/executed/cancelled/failed) |
| `days` | 倒数日 / 纪念日：title、emoji、date、repeat(once/yearly/monthly)、pinned |
| `vocab_books` | 词书：`owner_id=NULL` 为系统级（所有用户可见），非空为导入者私有；slug（唯一）、name、lang、word_count、sort；系统全量数据仍可由 `app/scripts/import_vocab.py` 从 ECDICT 导入 |
| `vocab_words` | 单词（全局去重，word 唯一）：音标、translations/sentences/phrases/synos/rel_words（JSON）、freq 词频 |
| `vocab_book_words` | 词书↔单词多对多：book_id + word_id（唯一），sort 词书内顺序 |
| `vocab_word_progress` | 学习进度（FSRS 卡片，每用户每词一条）：status(learning/mastered)、collected、wrong/right_count、wrong_active（错词本）、due（排课索引）+ FSRS 平铺字段 stability/difficulty/state/step/last_review |
| `vocab_practice_sessions` | 练习会话：book_id、mode(follow/dictation/self_test/spell)、total/correct/wrong_count、duration_sec、finished_at |
| `vocab_practice_logs` | 练习明细（只插入）：session_id、word_id、is_correct、wrong_times、duration_ms |

## API 端点清单（全部挂 `/api`；除 `/api/auth/register|login` 外均需凭证，`Bearer` 与 `X-API-Key` 等价）

### /api/auth
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /register | 注册（name/email/password） |
| POST | /login | 登录，返回 `{ token, user }` |
| POST | /logout | 登出，撤销当前 token（jti 入黑名单） |
| GET | /me | 当前用户信息 |

### /api/keys（API Key 管理，仅本人）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | 有效 Key 列表，返回 `{ keys: [{ id, name, prefix, createdAt, lastUsedAt }] }` |
| POST | / | 创建（`{ name }`，1-30 字），返回 `{ apiKey（明文，仅此一次）, item }`；有效 Key 达 20 把 → 400 |
| DELETE | /{key_id} | 撤销（软删，立即失效）；非本人或不存在的 id → 404 |

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
| GET | / | 我的账本列表（邀请码不下发，防成员转分享） |
| POST | / | 创建账本（name/type） |
| POST | /join | 输入邀请码加入共享账本（任意登录用户，成为 editor） |
| GET | /{book_id}/invite | 查看邀请码（仅 owner；null=未生成） |
| POST | /{book_id}/invite | 生成/重置邀请码（仅 owner；旧码立即失效） |
| DELETE | /{book_id}/invite | 关闭邀请（仅 owner；置空码，停止新成员加入） |
| POST | /{book_id}/leave | 成员自助退出（owner 不可） |
| POST | /{book_id}/members | 添加成员（userId 或 name 查找，兼容旧契约） |
| DELETE | /{book_id}/members/{user_id} | 移除成员 |
| POST | /{book_id}/convert | 个人账本 → 共享（单向，自动生成邀请码） |
| GET | /trash | 回收站列表 |
| DELETE | /{book_id} | 删除账本 → 回收站（软删除） |
| POST | /{book_id}/restore | 从回收站恢复 |
| DELETE | /{book_id}/purge | 彻底删除（级联清流水/预算/成员/邀请码） |

> 邀请码为 8 位大写字母数字（剔除易混字符 `0/O/1/I/L`，约 8.5e11 组合），长期有效、靠「重置」失效；码只经 `/invite` 接口对 owner 下发，不出现在账本列表 DTO 中。

### /api/todo · /api/calendar · /api/notes · /api/habits
统一模式：`GET ""` 列表、`POST ""` 创建、`PUT /{id}` 更新、`DELETE /{id}` 删除（数据按用户隔离）。

### /api/overview
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | 首页总览：流水/待办/日程/习惯聚合数据 |

### /api/vocab（词汇打字练习）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /books | 可见词书列表（系统级 + 本人私有），附每本我的进度 learning/mastered/due |
| POST | /books/import | 文本导入词书 `{name?, scope: user/system, lang?, text}`；用户级仅导入者可见，系统级所有人可见且仅首位用户可导入 |
| DELETE | /books/{book_id} | 删除本人私有词书；系统级仅首位用户可删。仅删除词书与映射，保留全局词条和学习进度 |
| GET | /books/{book_id}/words?limit=&offset=&status=&keyword=&sort= | 可见词书的单词分批拉取（详情页用）→ `{total(筛选后), totalAll(词书总词数), words:[{word..., progress?, practice}]}`。status：all/unlearned/learning/mastered/wrong/collected；keyword 按拼写模糊搜；sort：order(词书顺序)/freq/wrong(错次最多)/recent(最近练习过)。非法值回退默认 |
| GET | /books/{book_id}/summary | 词书详情页头部汇总 → `{book, total, learned, learning, mastered, due, wrong, collected, unlearned}`（未学 = 总词数 − 已学；按词书成员资格归桶） |
| POST | /practice/sessions | 开课+智能排课 `{bookId, mode, source?, newLimit?, reviewLimit?}` → `{id, bookId, bookName, source, mode, queue:[{word..., progress?}]}`；source=book（默认）复习池 = due≤now 且 learning（按 due 升序）+ 新词池；source=wrong/collect 直接练错词本/收藏（bookId 忽略，session.book_id=0） |
| POST | /practice/sessions/{id}/answers | 逐词上报 `{wordId, correct, wrongTimes, durationMs}` → 更新进度返回 item；错次自动映射 Rating：答错=Again / 答对但打错过=Hard / 一次全对=Good（py-fsrs v6，空学习步按天排课） |
| POST | /practice/sessions/{id}/finish | 结束会话 `{durationSec}`，落 finished_at |
| GET | /review/wrong | 错词本（wrong_active 且 learning） |
| GET | /review/collect | 收藏列表 |
| PUT | /progress/{word_id} | 标记 `{status?/collected?/dismissWrong?}`；未学过的词也可直接标记（自动建进度行） |
| GET | /stats | 今日 + 累计统计（`tzOffset` 为本地相对 UTC 分钟差，按客户端本地零点算“今日”；由 sessions/progress 聚合，无日表） |

- **FSRS 调度**：进度按 (user, word) 全局唯一（跨词书不重复学），book_id 只记首次来源；FSRS 字段平铺进 `vocab_word_progress`（排课需 `WHERE due <= now` 索引）；SQLite 读回的 datetime 无 tzinfo，服务层统一按 UTC 归一化。
- **词书详情**：单词行带 `progress`（本人进度，跨词书共享——同一词在不同词书里是同一份状态）与 `practice`（模式覆盖 `{follow, dictation, selfTest, spell, totalCount, lastAt}`）。模式覆盖由 `vocab_practice_logs` 按 (word_id, mode) 聚合，口径是**全局**的（不按词书/来源过滤：错词本与收藏练习的 `session.book_id` 记为 0，按词书过滤反而会漏）。
- **词书导入**：页面可导入 ECDICT CSV、简单文本（`word` / `word,释义` / `word<TAB>释义`）和 Anki 的 **Notes in Plain Text** 文本导出（支持 `#separator`、`#deck`、`#html`，首列为单词、第二列为释义，`<br>` 拆为多条释义）。`.apkg` 二进制牌组暂不支持；需要先在 Anki 中导出为文本。大规模完整 ECDICT 仍建议运行 `uv run python -m app.scripts.import_vocab --csv <ecdict.csv> --book cet4`。词条按小写拼写全局去重，已有释义不会被导入覆盖。

### /api/assistant · /api/transcribe
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /assistant/sessions | 创建会话（幂等：每用户单持久线程，已存在则返回） |
| GET | /assistant/sessions | 会话列表（有消息才返回，单线程通常至多一条） |
| GET | /assistant/sessions/{id}/messages | 会话消息（transcript，含 tool_result） |
| DELETE | /assistant/sessions/{id} | 删除会话 |
| POST | /assistant/chat | SSE 流式对话：多轮历史 + 结构化记账计划 → confirm_request |
| POST | /assistant/confirm | 确认/取消记账计划（approved 落库，追加 tool_result 消息） |
| POST | /assistant/transcribe | 语音转写（DashScope / OpenAI 兼容） |

- **聊天流转框架**：对话是一条平铺有序的 transcript，每轮 = `user → assistant → tool_result`；tool_result（工具执行结果）是聊天流的一等公民，既持久化也回放进模型上下文（带 `[工具结果]` 前缀）。
- **多轮记忆 + 自动压缩（compaction）**：每轮把近期 transcript（含 tool_result）喂给 LLM；当历史 token 估算超过 `LLM_COMPACT_THRESHOLD_TOKENS`（默认 4000）时，把较早轮次摘要成检查点写入 `assistant_sessions.summary`，近期原文（`LLM_COMPACT_RETAIN_TOKENS`，默认 1200）保留，原始消息仍在 DB 可回放。压缩失败降级、不阻塞本轮。

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

- `backend/tests/`，命令 `uv run pytest`（当前 49 项全绿）。
- `test_business_api.py`（23 项）：全链路业务测试——注册/登录/登出、账本创建与成员、邀请码生成/重置/关闭、邀请码加入/退出、账本数据隔离、流水 CRUD、分类、趋势、预算、todo/calendar/notes/habits/overview；每项测试用独立临时 SQLite 文件，`create_app(database_url=...)` 注入。
- `test_assistant.py`（23 项）：AI 助手多轮/压缩/计划确认/取消/转写。
- `test_security.py`（3 项）：JWT 密钥解析优先级（环境变量 > .env > 默认）与 `.env.example` 键完整性。
- 手工验收：`uv run uvicorn app.main:app --host 127.0.0.1 --port 8001` 后按契约调 `/api/auth/login` 等端点核对信封格式。

## 演进约束

- **契约同步**：任何接口变更必须 mock 层（`lairweb/mock/`）与后端同步修改，两端契约以本文档 + 测试为准。
- **schema 变更必须走 Alembic 迁移**，`create_all` 只负责新库兜底。
- 保持分层纪律：services 不含 HTTP 依赖，repositories 是唯一数据访问路径（换库不动业务层）。
- SQLite 适用早期单用户本地部署；未来多 worker 或写密集场景再评估 WAL/服务数据库。
- 后续方向（未实现）：主动提醒/每日总结等定时调度基础设施、生产环境密钥强制校验、多用户并发与锁行为。
