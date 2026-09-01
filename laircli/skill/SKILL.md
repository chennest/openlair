---
name: laircli
description: 通过 lair 命令行客户端（OpenLair 的 Go 版 CLI，X-API-Key 鉴权）代用户操作 OpenLair 数据。当用户要求「记一笔账/看流水/查预算/收支趋势」「勾待办/加待办」「查日程/加日程」「记笔记/看笔记」「习惯打卡」「看总览」「切账本/建账本」「lair 命令怎么用/报错排错」时使用。也适用于 laircli 的安装、初始化配置与排错。涉及删账本、签发/撤销 API Key、成员管理等高危操作时，明确告知用户去 Web 管理台操作。
agent_created: true
---

# laircli — OpenLair 命令行客户端使用指南

## Overview

`lair` 是 OpenLair 的官方命令行客户端（Go 单二进制，仓库 `laircli/`），通过用户级 API Key（`X-API-Key: ol_xxx`，与 Web 端 JWT 等价）调用后端 `/api`，只做「全模块只读 + 高频写入」。AI 代理在对话中需要读写 OpenLair 数据时，优先用 `lair` 而不是直接 curl 后端。

命令解析优先级：**命令行 flag > 环境变量 > 配置文件 `~/.laircli/config.json`**。

## Quick Start

1. **安装**（在 `laircli/` 目录下，Go ≥ 1.26）：
   ```bash
   cd laircli && go install ./cmd/lair && lair --help
   # 或本地直跑：go build -o lair ./cmd/lair && ./lair --help
   ```
2. **配置 API Key**（Key 在 Web 管理台「API Key」页创建，明文只显示一次；CLI 不签发 Key）：
   ```bash
   lair init    # 交互式粘贴（不回显），或：
   lair --api-key ol_xxx --base-url http://127.0.0.1:8002 init   # 非交互（注意 Key 会进 shell history）
   ```
   `lair init` 先打 `GET /api/auth/me` 校验，通过才写 `~/.laircli/config.json`。
3. **验证**：`lair whoami` 看当前用户；`lair config` 看配置（Key 只显示前 12 字符）。
4. **连接目标**：默认 `https://lair.lcc007.top`（生产）；本地开发用 `--base-url http://127.0.0.1:8001`，或环境变量 `OPENLAIR_BASE_URL`。

## 命令速查

| 命令 | 作用 |
|---|---|
| `lair init` / `whoami` / `config` | 配置并校验 Key / 看当前用户 / 看配置 |
| `lair book list\|create\|use\|current\|join` | 账本列表、建账本、切换默认账本、当前账本、邀请码加入 |
| `lair ledger add\|list\|edit\|rm\|categories\|trend\|budget` | 记账主干：记一笔、流水、改删、分类、趋势、预算 |
| `lair todo list\|add\|done\|undo\|edit\|rm` | 待办 |
| `lair cal list\|add\|done\|undo\|rm` | 日程 |
| `lair note list\|show\|add\|rm` | 笔记 |
| `lair habit list\|add\|check\|uncheck\|rm` | 习惯打卡 |
| `lair overview` | 总览看板（收入/支出/结余/待办/打卡等） |

## 记账 SOP（AI 代记账必守流程）

用户要求记一笔账时，按顺序执行，账本与分类一律以命令实时返回为准，禁止凭记忆猜测：

1. **确认账本**：`lair book current`（或 `lair book list`）。当前账本不明确、或要记到别的账本时，先 `lair book use <id>` 切换。
2. **拉取分类**：`lair ledger categories`，拿到真实分类名。
3. **记录**：`lair ledger add <金额> -c <分类名> [-n 备注] [-t type] [-d 日期]`。`-c` 按第 2 步拿到的分类名传，CLI 自动解析成 categoryId；解析不到会报错并拒绝发写请求。

## 高频示例

```bash
lair ledger add 38.5 -c 餐饮 -n 午饭          # 记一笔：分类名自动解析成 categoryId
lair ledger add 12000 -c 工资                 # 收入侧分类自动反推 type=收入
lair ledger list -t expense -k 午饭 --page-size 10   # 过滤类型+关键词分页
lair ledger trend                              # 收支趋势
lair ledger budget 6000                        # 设当月预算
lair --json ledger list | jq '.summary'       # JSON 输出（--json 全局 flag，可放任意位置）
lair todo add 写周报 -q 1 -d 今天 && lair todo done 9   # 加待办（优先级1、今天）并完成 9 号
lair habit check 1                             # 习惯打卡
lair cal add 体检 -d 明天 -T 09:00             # 加日程
```

每个子命令都支持 `--help`；不带参数运行分组命令（`lair ledger`）直接打帮助。全局 flag（`--json`/`--base-url`/`--api-key`/`-v`）可写在任意位置。

## 关键契约与坑（改代码或排错前必读）

1. **账本解析**：后端没有隐式默认账本，缺 `bookId` 直接 400「缺少账本」。`lair` 按 `--book` → `OPENLAIR_BOOK_ID` → 配置 `book_id` → 首个 personal 账本解析，自动兜底时输出会注明用的是哪个账本。
2. **分类必须解析成 id**：`POST /api/ledger` 只认 `categoryId` 不认名字，省略会静默落到「其他」。CLI 先查 `GET /api/ledger/categories` 把名字解析成 id，解析不到就报错、**绝不发写请求**。
3. **type 是中文枚举** `收入`/`支出`：非「收入」的值写入时被后端归一成「支出」。CLI 接受 `expense|income|+|-|支出|收入` 别名并显式映射，非法值直接拒绝。
4. **信封与退出码**：成功 `code=200`（不是 0）；422 是 FastAPI 唯一裸响应（`{"detail":[...]}`），无信封。退出码：`0` 成功、`1` 接口/业务失败（stderr 带 HTTP 状态+后端 message）、`2` 用法错误、`3` 未配置 Key（提示 `lair init`）。
5. **Windows 编码已解决**：Go 版不再需要 `PYTHONUTF8=1` / `MSYS2_ARG_CONV_EXCL`，中文参数在 Git Bash/cmd/PowerShell 下原样送达。

## 安全边界（严格遵守）

- **不做**：`lair api <METHOD> <path>` 逃生口、`keys create/revoke`、`book delete/purge`、成员管理、邀请码重置、`config set/unset`。这些刻意留在 Web 端，用户要求时明确引导去 Web 管理台。
- API Key 等同账号全部写权限，不打印明文、不写进 git/仓库、不贴到对话里（`lair config` 只显示前 12 字符）。
- 写操作前先确认用户意图；删除类操作（`ledger rm`/`todo rm` 等）影响单条数据，执行前向用户复核。

## 排错

| 现象 | 处理 |
|---|---|
| 退出码 3 | 未配置 Key → 引导 `lair init` |
| 401 / 退出码 1 | Key 被撤销或无效 → 提示重新 `lair init` |
| 400 缺账本 | 指定 `--book <id>` 或先 `lair book list`/`lair book use <id>` |
| 分类解析失败 | 先 `lair ledger categories` 确认分类名，不要跳过校验发写请求 |
| 本地连不上后端 | 检查 `--base-url`：开发用 `http://127.0.0.1:8001`，生产默认 `https://lair.lcc007.top` |

详细命令参考（含每个子命令参数、环境变量、契约细节）见 `references/commands.md`。
