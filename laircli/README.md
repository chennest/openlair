# laircli

OpenLair 命令行客户端：凭 **API Key** 在终端记账、看待办、查总览。Go 实现，单二进制、无运行时依赖。

与 Web 管理台走同一套 `/api` 契约（`{code, message, data}` 信封 + `X-API-Key` 鉴权），后端无需任何改动。

## 安装

```bash
cd laircli && go install ./cmd/lair     # 装到 $GOPATH/bin/lair(.exe)
lair --help
```

免安装直接跑：`cd laircli && go build -o lair ./cmd/lair && ./lair --help`

## 上手三步

```bash
# 1. Web 管理台「API Key」页创建一把 Key（明文只显示一次），然后：
lair init
#   → 粘贴 ol_ 开头的 Key（输入不回显），回车确认后端地址（默认 https://lair.lcc007.top）
#   → 先拿 Key 打一次 /api/auth/me，校验通过才写 ~/.laircli/config.json

# 2. 记账（分类名会解析成 categoryId，解析不到直接报错，不会静默记成「其他」）
lair ledger add 38.5 -c 餐饮 -n 午饭
lair ledger add 12000 -c 工资          # 收入侧分类会自动反推 type=收入
lair ledger list -t expense -k 午饭 --page-size 10

# 3. 其余模块
lair todo add 写周报 -q 1 && lair todo list -o
lair habit check 1 && lair cal add 体检 -d 明天 -T 09:00 && lair overview
```

## 命令面

| 分组 | 命令 |
|---|---|
| 配置 | `init` `whoami` `config` |
| 记账 | `ledger add\|list\|edit\|rm\|categories\|trend\|budget` |
| 账本 | `book list\|create\|use\|current\|join` |
| 待办 | `todo list\|add\|done\|undo\|edit\|rm` |
| 日程 | `cal list\|add\|done\|undo\|rm` |
| 笔记 | `note list\|show\|add\|rm` |
| 习惯 | `habit list\|add\|check\|uncheck\|rm` |
| 总览 | `overview` |

全局选项可以写在任意位置：`--json`（管道给 jq）、`--base-url`、`--api-key`、`-v`（请求概要走 stderr）。
环境变量 `OPENLAIR_API_KEY` / `OPENLAIR_BASE_URL` / `OPENLAIR_BOOK_ID` / `LAIRCLI_JSON` 与配置文件
的解析优先级是 **flag > env > 文件**。

退出码：`0` 成功 / `1` 接口或业务失败 / `2` 用法错误 / `3` 未配置 API Key。

## 刻意不做的能力

命令面只做「读 + 对自己单条数据的高频写」。以下操作留在 Web 管理台，CLI **不提供等价物，也不留逃生口**：

- `api <METHOD> <path>` 这类直连任意接口的口子（有它上面所有禁令都是纸糊的）
- API Key 的签发与撤销（`keys create/revoke`）——CLI 连自己的 Key 都不能改
- 删账本、清空数据（`book delete/purge/trash/restore`）、成员增删、个人转共享、重置邀请码
- `config set/unset`（会把明文 Key 写进 shell history；改配置统一重新 `lair init`）
- AI 助手对话与截图/语音识别记账

完整理由与契约说明见 [`docs/cli/cli-guide.md`](../docs/cli/cli-guide.md)。

## Windows 说明

Go 版没有 Python 版那两个坑：中文参数不需要 `PYTHONUTF8=1`（Win32 argv 是 UTF-16，直接转 UTF-8），
进程启动时会把控制台代码页切到 UTF-8，表格按显示宽度对齐，管道场景自动不染色。

## 开发与测试

```bash
cd laircli
go build ./... && go vet ./... && gofmt -l .   # 都应当无输出
go test ./...                                  # 83 项，httptest 假后端，不需要起服务
```

包结构：`internal/{config,api,parse,render,cli}` 是基础层，`internal/commands` 是命令面
（测试直接调真实入口 `commands.Run`，断言退出码、输出与**实际发出的 HTTP 调用序列**）。
