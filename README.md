# Lair · 灵穴

> 一个人的全平台个人AI生活助理

## 项目结构

```
lair/
├── lairservice/    # FastAPI 服务端（核心大脑）
├── lairapp/        # Flutter 客户端（iOS/Android/macOS/Windows）
├── lairweb/        # Web 管理后台
└── docs/           # 项目文档
```

## 模块规划

- **单词** — 间隔重复(SM-2) + 多语言识别 + 对话式背诵
- **记账** — 自然语言记账 + 分类统计
- **日历** — 日程管理 + 提醒
- **笔记** — 快速记录 + 总结
- **习惯** — 打卡追踪
- **主动** — 定时晨间回顾、晚间总结、单词提醒

## 技术栈

| 组件 | 技术 |
|------|------|
| 服务端 | Python / FastAPI |
| 客户端 | Flutter |
| Web | Vue + TypeScript / Vite |
| 数据库 | SQLite |
| LLM | 多供应商 / 多模型，通过统一模型网关接入 |
| LLM 编排 | LangGraph |

后端选型细节见 [`docs/backend-architecture.md`](docs/backend-architecture.md)。

## License

MIT
