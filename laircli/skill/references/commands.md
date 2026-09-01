# lair 命令详细参考

laircli 是 OpenLair 的 Go 版命令行客户端，走后端 `/api`（`{code, message, data}` 信封），鉴权用用户级 API Key（`X-API-Key: ol_xxx`）。本文件是 SKILL.md 的补充参考，按需加载。

## 配置

- 配置文件：`~/.laircli/config.json`（Windows：`C:\Users\<你>\.laircli\config.json`；或 `$XDG_CONFIG_HOME/laircli/config.json`）
- 字段：`api_key`、`base_url`、`user`（备注）、`book_id`（`lair book use` 后写入，可选）
- 解析优先级：命令行 flag > 环境变量 > 配置文件

### 环境变量

| 环境变量 | 等价 flag |
|---|---|
| `OPENLAIR_API_KEY` | `--api-key` |
| `OPENLAIR_BASE_URL` | `--base-url` |
| `OPENLAIR_BOOK_ID` | 子命令 `--book` / `-b` |
| `LAIRCLI_JSON=1` | 全局 `--json` |
| `LAIRCLI_CONFIG` | 指定配置文件路径（多环境/测试） |

## 完整命令面

### 配置与身份
- `lair init` — 交互式粘贴 Key（不回显）→ 校验 `GET /api/auth/me` → 落盘
- `lair whoami` — 当前用户
- `lair config` — 打印配置（Key 只显示前 12 字符）

### 账本 book
- `lair book list` — 账本列表
- `lair book create <名称>` — 建账本
- `lair book use <id>` — 设为默认账本（写入 config 的 book_id）
- `lair book current` — 当前默认账本
- `lair book join <邀请码>` — 用邀请码加入共享账本

### 记账 ledger
- `lair ledger add <金额> -c <分类名> [-n 备注] [-t type] [-d 日期] [--book id]` — 记一笔；`-t` 接受 `expense|income|+|-|支出|收入`；`-d` 支持「今天/昨天/明天/YYYY-MM-DD」
- `lair ledger list [-t type] [-k 关键词] [--page-size N] [--page N] [--book id]` — 流水
- `lair ledger edit <id> [...]` — 改单条
- `lair ledger rm <id>` — 删单条（不可逆，先复核）
- `lair ledger categories [--book id]` — 分类列表
- `lair ledger trend [--book id]` — 收支趋势
- `lair ledger budget <金额> [--book id]` — 设当月预算

### 待办 todo
- `lair todo list [--status open|done|all]`
- `lair todo add <标题> [-q 优先级1-4] [-d 日期]` — `-d` 支持「今天/明天/YYYY-MM-DD」
- `lair todo done <id>` / `lair todo undo <id>`
- `lair todo edit <id> [...]` / `lair todo rm <id>`

### 日程 cal
- `lair cal list [-d 日期]`
- `lair cal add <标题> -d <日期> [-T HH:MM]`
- `lair cal done <id>` / `undo` / `rm <id>`

### 笔记 note
- `lair note list` / `lair note show <id>` / `lair note add <文本>` / `lair note rm <id>`

### 习惯 habit
- `lair habit list`
- `lair habit add <名称>` — 建习惯
- `lair habit check <id>` / `uncheck <id>` — 打卡/取消
- `lair habit rm <id>`

### 总览 overview
- `lair overview` — 一屏总览：本月支出+预算进度 / 最近 10 笔流水 / 待办 / 即将开始 / 习惯打卡

## 契约细节

1. 成功信封 `code=200`；失败归一为「HTTP 状态 + 后端 message」输出到 stderr，退出码 1。
2. `422` 是唯一裸响应（FastAPI 默认 `{"detail":[...]}`，无信封）。
3. `type` 中文枚举 `收入`/`支出`，写入时非「收入」一律归一成「支出」；CLI 显式映射别名并拒绝非法值。
4. 分类按名字解析为 `categoryId`；解析不到就报错，绝不发写请求。
5. 账本缺省解析：`--book` → `OPENLAIR_BOOK_ID` → config `book_id` → 首个 personal 账本；自动兜底会在输出注明账本。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 接口或业务失败（stderr 前缀带 HTTP 状态） |
| 2 | 命令用法错误（未知选项/子命令/缺参数） |
| 3 | 未配置 API Key（提示 `lair init`） |

## 安全边界（不做清单）

CLI 刻意不提供以下能力（要这些去 Web 管理台）：
- `lair api <METHOD> <path>` 逃生口
- `keys create/revoke`（不签发/撤销凭证）
- `book delete/trash/restore/purge`（账本级删除、硬删）
- 账本成员增删、`convert`、`leave`、`invite --rotate`（邀请码重置）
- `config set/unset`（改配置统一走 `lair init`）
- AI 助手类命令（`ask`/snap/transcribe，SSE 流式，终端不复刻）

## 开发与测试（laircli/ 目录下）

```bash
go build ./...    # 编译全部包
go test ./...     # 83 项，httptest 假后端，无需起服务
go vet ./...      # 静态检查
gofmt -l .        # 提交前应无输出
```

分层：`internal/config`（配置三级解析）、`internal/api`（信封解包）、`internal/parse`（中文枚举/日期/金额）、`internal/render`（CJK 宽度表格）、`internal/cli`（手写子命令解析）、`internal/commands`（业务命令，测试钉住退出码+HTTP 调用序列）。
