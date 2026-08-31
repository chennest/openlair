# 命令行客户端 laircli 指南

## 一、概述

`laircli/` 是 OpenLair 的命令行客户端，可执行命令名为 **`lair`**，Go 实现、单二进制、无运行时依赖。
它不引入任何新协议：走的还是后端那套 `/api`（`{code, message, data}` 信封），鉴权用**用户级 API Key**
（`X-API-Key: ol_xxx`），与 Web 管理台的 JWT 完全等价。后端为此**不需要任何改动**。

设计边界：

- 只做「全模块只读 + 高频写入」。终端里最常干的事：记一笔、看流水、勾待办、打卡、看总览。
- **刻意不做**高危与不可逆操作（删账本、清空数据、成员管理、邀请码重置、API Key 签发与撤销），
  也不提供"直连任意接口"的逃生口。理由见第九节。
- 不做 AI 助手：`/api/assistant/*` 只有 SSE 流式，且属于对话产品能力，不在终端里复刻。
- 首次配置只接受**手动粘贴** API Key（CLI 不收集账号密码），粘贴后落盘到用户目录一个文件里。

## 二、安装

```bash
cd laircli && go install ./cmd/lair     # 装到 $GOPATH/bin/lair(.exe)
lair --help

# 或不安装直接跑：
cd laircli && go build -o lair ./cmd/lair && ./lair --help
```

`main` 包在 `cmd/lair/` 下（不是仓库根 Go 模块，安装命令必须在 `laircli/` 里执行），
这样 `go install` 产出的二进制就叫 `lair`。

`go.mod` 只要求 Go 1.26，唯一外部依赖是 `golang.org/x/term`（隐藏输入用）。子命令解析、
信封解包、CJK 表格对齐都是本仓库内的小实现，没有引 cobra/urfave 之类的框架。

## 三、首次配置

1. 在 **Web 管理台「API Key」页**创建一把 Key，**明文只显示这一次**（命令行不签发 Key）。
2. 粘贴给 CLI：

```bash
lair init                      # 交互式：粘贴 Key（不回显）→ 确认后端地址
lair --api-key ol_xxx --base-url http://127.0.0.1:8002 init   # 非交互
```

`lair init` 会先拿这把 Key 打一次 `GET /api/auth/me`，**校验通过才写文件**；失败则一个字节都不落盘。
写入位置：

```
C:\Users\<你>\.laircli\config.json        # Windows
~/.laircli/config.json                    # POSIX（或 $XDG_CONFIG_HOME/laircli/config.json）
```

```json
{
  "api_key": "ol_xxxxxxxxxxxx…",
  "base_url": "http://127.0.0.1:8002",
  "user": "我",
  "book_id": 1
}
```

`book_id` 可选（`lair book use` 后写入），`user` 只是给人看的备注。

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
| `lair init` / `lair whoami` / `lair config` | 配置并校验 Key / 看当前用户 / 看配置（Key 只打印前 12 字符） |
| `lair book list\|create\|use\|current\|join` | 账本与默认账本 |
| `lair ledger add\|list\|edit\|rm\|categories\|trend\|budget` | 记账主干 |
| `lair todo list\|add\|done\|undo\|edit\|rm` | 待办 |
| `lair cal list\|add\|done\|undo\|rm` | 日程 |
| `lair note list\|show\|add\|rm` | 笔记 |
| `lair habit list\|add\|check\|uncheck\|rm` | 习惯打卡 |
| `lair overview` | 总览看板 |

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

全局 flag（`--json` / `--base-url` / `--api-key` / `-v`）**可以写在任意位置**，
`lair ledger list --json` 与 `lair --json ledger list` 等价。每个命令都支持 `--help`，
不带参数运行分组命令（`lair ledger`）会直接打帮助。

## 五、命令面背后的三条契约

这三条是 CLI 侧代码存在的理由，改后端接口时请一并核对（实现见 `laircli/internal/commands/resolver.go`
与 `laircli/internal/parse/parse.go`）：

1. **后端没有隐式默认账本**。`/api/ledger` 系列缺 `bookId` 直接 400「缺少账本」。CLI 按
   `--book` → `OPENLAIR_BOOK_ID` → 配置 `book_id` → 首个 personal 账本 的顺序解析，**自动兜底时会在输出里
   注明是哪个账本**，避免静默记错账本。
2. **`POST /api/ledger` 不读 `category`（名字）字段**，只认 `categoryId`；省略 `categoryId` 会**静默落到
   「其他」**。所以 CLI 必须先 `GET /api/ledger/categories` 把名字解析成 id，解析不到就报错、
   **绝不发出写请求**（测试里用"写请求数为 0"钉死这条）。
3. **`type` 是中文枚举** `收入`/`支出`，且写入时任何非 `收入` 的值都被归一成 `支出`。CLI 接受
   `expense|income|+|-|支出|收入` 别名并显式映射，非法值直接拒绝，防止「想记收入记成了支出」。

另外：成功信封的 `code` 是 `200` 而不是 `0`；**422 是唯一的裸响应**（FastAPI 默认 `{"detail":[...]}`，
没有信封）。两者都会被归一成一个人类可读错误 + 退出码（`laircli/internal/api/client.go`）。

## 六、退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 接口或业务失败（stderr 打印后端 `message`，前缀带 HTTP 状态） |
| 2 | 命令用法错误（未知选项/子命令、缺参数、`--category` 没配 `--type` 等） |
| 3 | 未配置 API Key（提示 `lair init`） |

## 七、Windows 编码：Go 版已经不是问题

Python 版在 Windows 上有两个坑（要 `PYTHONUTF8=1`、要 `MSYS2_ARG_CONV_EXCL='*'`），Go 版都消掉了：

- **输入侧**：Go 运行库直接把 Win32 的 UTF-16 argv 转成 UTF-8 字符串，不经过本地代码页，所以
  `lair ledger add 30 -c 餐饮 -n 午饭` 在 Git Bash / cmd / PowerShell 下都是原样送达，
  不需要任何前置环境变量，也就不存在「中文备注静默变脏数据」。
- **输出侧**：进程启动时把控制台代码页切到 UTF-8（`SetConsoleCP/SetConsoleOutputCP(65001)`）并打开
  ANSI 转义支持，见 `laircli/console_windows.go`。管道/重定向时自动不染色，`NO_COLOR=1` 可强制关闭。
- 表格列宽按**显示宽度**算（中文与全角标点记 2 列），所以中英混排能对齐；`✓ ▰ ▱ █` 这类
  East Asian Ambiguous 字符按 1 列计，个别终端会渲染成 2 列，可能有一格视觉错位，只影响观感。

## 八、安全约定

- 一把 API Key 等同该账号的**全部写权限**（凭证没有 scope 概念），别提交进仓库、别贴到 issue。
- 配置文件明文存 Key，POSIX 下写完后收紧到 `0600`；**Windows 的 chmod 只切只读位（ACL 不变）**，
  所以真正的保护是「CLI 从不打印明文」：`lair config` 与报错文案里都只出现前 12 字符前缀。
- **Key 的签发与撤销都在 Web 端**：CLI 既不创建也不撤销 Key，因此不存在"把自己的当前 Key 撤掉导致自锁"
  这条路。撤销立即生效，正在用的 Key 被撤后 `lair` 会以退出码 1 + 401 提示重新 `lair init`。
- 非交互写 Key 时（`lair --api-key ... init`）Key 会进 shell history，共享机器上优先用交互式粘贴。
- `/api/auth/logout` 只拉黑 JWT，**不撤销 API Key**。

## 九、命令行刻意不做的能力

这些不是"还没来得及做"，而是有意从命令面上拿掉的——**CLI 不给自己留后门**，否则精简的命令面会被
一个逃生口整体击穿：

| 能力 | 为什么不做 |
|---|---|
| `lair api <METHOD> <path>` 逃生口 | 一旦有它，下面所有禁令都是纸糊的（可以直接打 `purge`、改成员） |
| `lair keys create/revoke` | CLI 不该能签发凭证；撤销自己正在用的 Key 会立刻自锁 |
| `lair book delete/trash/restore` | 账本级删除，且回收站语义在 Web 端才有完整上下文 |
| `lair book purge`（硬删级联流水） | 不可逆 |
| `lair book invite --rotate` | 重置邀请码会让已分享的成员拿不到入口；GET 邀请码本身也是敏感值 |
| 账本成员增删、`convert`（个人转共享）、`leave` | 影响他人；`members` 还能把从未登录过的用户塞进账本 |
| `lair config set/unset` | 把 Key 写进 argv 会留在 shell history；改配置统一走 `lair init` |
| `lair ask` / snap / transcribe（AI 助手） | 助手是对话产品能力，`/api/assistant/chat` 只有 SSE 流式，终端复刻价值低 |

需要这些能力时去 Web 管理台操作。CLI 侧唯一保留的"写"是对**自己单条数据**的日常增删改
（流水/待办/日程/笔记/习惯）+ 建账本 + 用邀请码加入账本 + 设当月预算。

## 十、开发与测试

```bash
cd laircli
go build ./...     # 编译全部包
go test ./...      # 83 项，全部走 httptest 假后端，不需要起服务
go vet ./...
```

分层与注入点：

- `internal/config` 配置三级解析与落盘；`internal/api` 信封解包 + 两种失败形状归一；
  `internal/parse` 中文枚举/象限/相对日期/金额分组；`internal/render` CJK 宽度表格与颜色开关；
  `internal/cli` 手写的子命令与选项解析（含帮助文本）。
- `internal/commands` 的用例直接调真实入口 `commands.Run(args, ctx, color)`，断言的是**退出码 +
  stdout/stderr 文本 + 实际发出的 HTTP 调用序列**（`harness_test.go` 里的 `fake` 会记录每次
  method/path/body），所以「分类解析失败绝不发写请求」这类语义是被钉住的，而不是只测了纯函数。
- 用例用 `t.Setenv("LAIRCLI_CONFIG", ...)` 把配置文件指到 tmp 目录，不碰真实 `~/.laircli`。
