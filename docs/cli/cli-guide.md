# 命令行客户端 laircli 指南

## 一、概述

`laircli/` 是 OpenLair 的命令行客户端，可执行命令名为 **`lair`**。它不引入任何新协议：走的还是
后端那套 `/api`（`{code, message, data}` 信封），鉴权用**用户级 API Key**（`X-API-Key: ol_xxx`），
与 Web 管理台的 JWT 完全等价。后端为此**不需要任何改动**。

设计边界：

- 只做「全模块只读 + 高频写入」。终端里最常干的事：记一笔、看流水、勾待办、打卡、看总览。
- 未封装的能力一律用 `lair api <METHOD> <path>` 逃生口直连，不为低频接口膨胀命令面。
- 首次配置只接受**手动粘贴** API Key（CLI 不收集账号密码），粘贴后落盘到用户目录一个文件里。

## 二、安装

```bash
uv tool install ./laircli          # 或 pipx install ./laircli
lair --help

# 不安装直接跑：
cd laircli && uv sync --extra dev && uv run lair --help
```

`requires-python >= 3.11`（有意低于后端的 3.14，便于装到普通开发机上；`tomllib` 自 3.11 起是标准库）。
依赖只有 `typer` + `rich` + `httpx`。

## 三、首次配置

1. 在 Web 管理台「API Key」页（或 `lair keys create <名称>`，需已有可用 Key）创建一把 Key，
   **明文只显示这一次**。
2. 粘贴给 CLI：

```bash
lair init                       # 交互式：粘贴 Key → 确认后端地址
lair init --api-key ol_xxx --base-url http://127.0.0.1:8001   # 非交互
```

`lair init` 会先拿这把 Key 打一次 `GET /api/auth/me`，**校验通过才写文件**；失败则一个字节都不落盘。
写入位置：

```
C:\Users\<你>\.laircli\config.toml        # Windows
~/.laircli/config.toml                    # POSIX（或 $XDG_CONFIG_HOME/laircli/config.toml）
```

```toml
api_key = "ol_xxxxxxxxxxxx…"
base_url = "http://127.0.0.1:8001"
user = "我"
book_id = 1          # 可选：lair book use 后写入
```

解析优先级：**命令行 flag > 环境变量 > 配置文件**。

| 环境变量 | 等价 flag |
|---|---|
| `OPENLAIR_API_KEY` | `--api-key` |
| `OPENLAIR_BASE_URL` | `--base-url` |
| `OPENLAIR_BOOK_ID` | 子命令的 `--book` / `-b` |
| `LAIRCLI_JSON=1` | 全局 `--json` |
| `LAIRCLI_CONFIG` | （指定配置文件路径，多环境/测试用） |

`base_url` 缺省为生产站点 `https://lair.lcc007.top`——部署里只有一个 web origin，`/api` 由 nginx 反代到
后端，**没有独立的后端域名**；本地开发才填 `http://127.0.0.1:8001`。

## 四、命令速查

| 命令 | 作用 |
|---|---|
| `lair init` / `lair whoami` | 配置并校验 Key / 看当前用户 |
| `lair config show\|set\|unset` | 查看与改配置项（`show` 只打印 Key 前 12 字符） |
| `lair book list\|create\|use\|current\|join\|invite\|delete\|trash\|restore` | 账本与默认账本 |
| `lair ledger add\|list\|edit\|rm\|categories\|trend\|budget` | 记账主干 |
| `lair todo list\|add\|done\|undo\|edit\|rm` | 待办 |
| `lair cal list\|add\|done\|undo\|rm` | 日程 |
| `lair note list\|show\|add\|rm` | 笔记 |
| `lair habit list\|add\|check\|uncheck\|rm` | 习惯打卡 |
| `lair overview` | 总览看板 |
| `lair keys list\|create\|revoke` | API Key 管理 |
| `lair api GET /api/assistant/sessions` | 逃生口：直连任意接口 |

常用示例：

```bash
lair ledger add 38.5 -c 餐饮 -n 午饭          # 分类名会解析成 categoryId
lair ledger add 12000 -c 工资                 # 收入侧分类会自动反推 type=收入
lair ledger list -t expense -k 午饭 --page-size 10
lair ledger trend && lair ledger budget 6000
lair --json ledger list | jq '.summary'
lair todo add 写周报 -q 1 -d 今天 && lair todo done 9
lair habit check 1 && lair cal add 体检 -d 明天 -T 09:00
```

全局 flag 必须写在子命令**之前**：`lair --json ledger list`（typer 的回调参数不向叶子命令传播）。

## 五、命令面背后的三条契约

这三条是 CLI 侧代码存在的理由，改后端接口时请一并核对（实现见 `laircli/src/laircli/resolver.py`）：

1. **后端没有隐式默认账本**。`/api/ledger` 系列缺 `bookId` 直接 400「缺少账本」。CLI 按
   `--book` → `OPENLAIR_BOOK_ID` → 配置 `book_id` → 首个 personal 账本 的顺序解析，**自动兜底时会在输出里
   注明是哪个账本**，避免静默记错账本。
2. **`POST /api/ledger` 不读 `category`（名字）字段**，只认 `categoryId`；省略 `categoryId` 会**静默落到
   「其他」**。所以 CLI 必须先 `GET /api/ledger/categories` 把名字解析成 id，解析不到就报错、
   **绝不发出写请求**。
3. **`type` 是中文枚举** `收入`/`支出`，且写入时任何非 `收入` 的值都被归一成 `支出`。CLI 接受
   `expense|income|+|-|支出|收入` 别名并显式映射，非法值直接拒绝，防止「想记收入记成了支出」。

另外：成功信封的 `code` 是 `200` 而不是 `0`；**422 是唯一的裸响应**（FastAPI 默认 `{"detail":[...]}`，
没有信封）。两者都会被归一成一个人类可读错误 + 退出码（`laircli/src/laircli/client.py`）。

## 六、退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 接口或业务失败（stderr 打印后端 `message`，前缀带 HTTP 状态） |
| 2 | 命令用法错误（typer/click 负责） |
| 3 | 未配置 API Key（提示 `lair init`） |

## 七、Windows 上的编码坑

- 输出侧：CLI 入口统一把 stdout/stderr 重设为 UTF-8（`render.ensure_utf8()`），所以中文表格与
  `--json` 输出在任何代码页下都正确。
- **输入侧无法由 CLI 兜底**：Git Bash（MSYS2）传非 ASCII 参数时，`sys.argv` 可能在解释器启动阶段
  就被按 GBK 解码成 PEP 383 代理转义字符，中文备注会**静默变成脏数据**。CLI 会在检测到这类字符时
  报警并拒绝发请求，但正确做法是执行前设 `PYTHONUTF8=1`：

```bash
PYTHONUTF8=1 lair ledger add 30 -c 餐饮 -n "终端午饭"
```

- `lair api` 的 path 参数会被 Git Bash 当成 POSIX 路径改写（`/api/x` → `D:/Program Files/Git/api/x`），
  报错信息会提示改用：

```bash
MSYS2_ARG_CONV_EXCL='*' lair api GET /api/assistant/sessions
```

## 八、安全约定

- 一把 API Key 等同该账号的**全部写权限**（凭证没有 scope 概念），别提交进仓库、别贴到 issue。
- 配置文件明文存 Key，POSIX 下写完后 `chmod 600`；**Windows 的 `chmod` 只切只读位（ACL 不变）**，
  所以真正的保护是「CLI 从不打印明文」：`lair config show` 与 `lair keys list` 都只给前 12 字符前缀。
- 撤销立即生效：正在用的 Key 被撤销后，`lair` 会以退出码 1 + 401 提示失败。`lair keys revoke` 命中
  本机正在用的那把时会先警告。
- `/api/auth/logout` 只拉黑 JWT，**不撤销 API Key**；要让 Key 失效必须 `lair keys revoke <id>`。

## 九、未覆盖能力与后续

明确留在 v1 之外（需要时用 `lair api`）：

- `lair ask`（AI 助手对话）：`POST /api/assistant/chat` **只有 SSE 流式**，且 HTTP 恒 200、错误以
  `{"type":"error"}` 帧下发，需要绕开信封解包单开一条码路。
- `lair snap`（截图识别记账）与 `/api/assistant/transcribe`：multipart 上传 + 依赖上游视觉/语音模型配置。
- 账本成员增删、`convert`（个人转共享）、`purge`（硬删）、`leave`，以及助手会话管理。

## 十、开发与测试

```bash
cd laircli
uv sync --extra dev
uv run pytest            # 70 项，全部走 httpx.MockTransport 假后端，不依赖起服务的用例
```

测试的注入点是 `laircli/src/laircli/state.py` 的模块级 `_transport`；`tests/conftest.py` 的 `invoke`
夹具会把 `LAIRCLI_CONFIG` 指到 tmp 目录并走真实控制台入口 `main()`，因此退出码与错误文案都是端到端校验的。
