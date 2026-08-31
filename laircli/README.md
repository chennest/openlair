# laircli

OpenLair 命令行客户端：凭 **API Key** 在终端记账、看待办、查总览。与 Web 管理台走同一套
`/api` 契约（`{code, message, data}` 信封 + `X-API-Key` 鉴权），后端无需任何改动。

## 安装

```bash
uv tool install ./laircli        # 或 pipx install ./laircli
lair --help
```

免安装直接跑：`cd laircli && uv run lair --help`

## 上手三步

```bash
# 1. Web 管理台「API Key」页创建一把 Key（明文只显示一次），然后：
lair init
#   → 粘贴 ol_ 开头的 Key，回车确认后端地址（默认 https://lair.lcc007.top）
#   → 校验通过后写入 ~/.laircli/config.toml

# 2. 记账（分类名会自动解析成 categoryId，解析不到直接报错而不是记成「其他」）
lair ledger add 38.5 -c 餐饮 -n 午饭
lair ledger list -t expense --page-size 10

# 3. 别的模块
lair overview
lair todo add 写周报 -q 1
lair habit check 1
```

## 命令速查

| 命令 | 作用 |
|---|---|
| `lair init` / `lair whoami` | 配置 Key 并校验 / 看当前用户 |
| `lair config show\|set\|unset` | 查看与改配置（Key 只显示前缀） |
| `lair book list\|create\|use\|current\|join\|invite\|delete\|trash\|restore` | 账本与默认账本 |
| `lair ledger add\|list\|edit\|rm\|categories\|trend\|budget` | 记账主干 |
| `lair todo list\|add\|done\|undo\|edit\|rm` | 待办 |
| `lair cal list\|add\|done\|undo\|rm` | 日程 |
| `lair note list\|show\|add\|rm` | 笔记 |
| `lair habit list\|add\|check\|uncheck\|rm` | 习惯打卡 |
| `lair overview` | 总览看板 |
| `lair keys list\|create\|revoke` | API Key 管理 |
| `lair api GET /api/books` | 逃生口：直接调任意接口 |

## 全局参数与环境变量

- 全局参数写在子命令**之前**：`lair --json ledger list`
- `--json` / `LAIRCLI_JSON=1`：输出纯 JSON，便于管道给 `jq`
- `--base-url` / `OPENLAIR_BASE_URL`、`--api-key` / `OPENLAIR_API_KEY`、`OPENLAIR_BOOK_ID`
- 优先级：命令行 flag > 环境变量 > `~/.laircli/config.toml`

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 接口或业务失败（stderr 给出后端 `message`） |
| 2 | 命令用法错误 |
| 3 | 未配置 API Key（提示 `lair init`） |

## 注意

- API Key 等同你的账号写权限，**别提交进仓库、别贴到 issue**。配置文件明文存放，POSIX 下
  会 `chmod 600`；Windows 的 `chmod` 只切只读位，保护靠的是「CLI 从不打印明文」。
- ledger 系列接口要求 `bookId`，后端没有隐式默认账本；未设默认时 CLI 取首个个人账本并在输出里
  注明，可用 `lair book use <id>` 固定。
