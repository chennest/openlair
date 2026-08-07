# OpenLair 前端规范（Frontend Guide）

> 本文件是 OpenLair 前端开发的**唯一权威规范**。任何前端改动、新增页面/组件、调整样式、修改 mock，都必须先通读本文件，再动手。所有 AI 代理与协作者默认遵守本规范。

## 〇、设计语言：Apple Liquid Glass

- `lairweb/` 使用 **Apple Liquid Glass** 视觉语言（apple.com / Apple Newsroom / 最新 macOS 的冷静、高级、克制的质感）。
- **权威设计系统 = agent skill**：`agents/skills/apple-design-skill/`（来源 [`naplesblue/apple-design-skill`](https://github.com/naplesblue/apple-design-skill)，MIT，已克隆进仓库）。**风格规则、token、组件、动效规范就是 skill 文件本身**，本文件只做索引与要点浓缩，不维护平行副本；前端工作必须加载并遵循该 skill。
- Skill 是框架无关的：在 Vue 中把 CSS 翻译成 SFC scoped 样式 / 全局 token，但保留**精确 token 值**、panel-not-cards 模式、glass-only-on-overlap 规则。

### Skill 文件索引（实际风格规范）

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 入口：哲学、工作流、anti-slop 清单、自检。先读它。 |
| `design-system.md` | 完整规范：色彩、字号、间距/圆角/阴影层级、玻璃配方、材质深度语法、响应式。 |
| `tokens.css` | `:root` 自定义属性，接入项目后一律 `var(--…)` 引用。 |
| `components.md` | 可复制的 HTML+CSS：玻璃导航、统一面板列表、卡片网格、分段控件、标签、按钮、彩色 CTA、开关、live dot。 |
| `patterns.md` | 页面级配方（阅读 720 / 网格 1080 容器 · detail/index/home/form 原型）+ 决策树。 |
| `motion.md` | 交互层动效：spring、可中断性、同路径进出、materialize、reduced-motion。 |
| `app.md` | App/iOS 壳层：iPhone 设备框、状态栏、大标题折叠导航、Tab 栏、底部 sheet、安全区。 |
| `icons.md` | 线性图标层：Lucide 内联 SVG（24 网格单笔画），灰阶 `currentColor`，仅 action/active 用强调色。 |
| `checklist.md` | 独立"完成"门禁。 |
| `review.md` | 审查模式工作流（审计现有 UI 是否 Apple 风）。 |
| `reference.html` | 渲染版活样式指南（浏览器打开，即基准观感）。 |
| `examples/` | 成品示例页（`account.html`、`wallet.html`）+ 截图。 |

### 核心规则（源自 `SKILL.md`，按优先级）

1. **统一表面 > 碎片化卡片**：同层级的多个条目放进**一个白色面板 + hairline 分割线**，而不是一堆各自描边着色的卡片。
2. **玻璃是调味品不是主菜**：`backdrop-filter` 只用于**层真正重叠**处（sticky 导航、弹窗/popover、彩色 CTA）；普通内容 = 纯白 `#fff` + 柔和阴影。
3. **克制即奢侈**：先用留白与层级解决问题，再考虑边框、填充、图标、数字；拒绝 data-slop。
4. **层级来自字重 + 字号 + 灰阶，而非颜色**：正文世界是黑白灰，颜色只作强调（一个蓝）。
5. **Apple 质感在细节**：大标题负字距、`tabular-nums`、hairline、轻 hover lift、180% 饱和度玻璃、滚动边缘导航。

### 使用流程

- **Build 模式**（来自 `SKILL.md`）：读 `design-system.md` → 引入 `tokens.css` → 从 `patterns.md` 选页面配方 → 按 `components.md` 组装 → 交互层应用 `motion.md`（App/iOS 屏再读 `app.md` + `icons.md`）→ 对照 `reference.html` → 过 `checklist.md` 门禁。
- **Review 模式**（`review.md`）：审计现有 CSS/页面，按系统打分，给出带 `file:line` 的优先级修复清单，映射回 token。
- **触发词**（应加载该 skill）：「Apple 风格」「液态玻璃」「苹果风」「make it look like apple.com」「clean / premium / minimal」。

## 一、目录结构（按业务模块拆分）

前端代码位于 `lairweb/`，**一个业务模块一个目录**，禁止在单一文件里堆大页面。

```
lairweb/
├── mock/                        # mock 数据层（内存态 CRUD）
│   ├── store.ts                 # 共享内存 store + seedable 伪随机（勿直接改初始数据以外的部分）
│   └── <模块>.mock.ts           # 每模块一个 mock 文件（default 对象导出 list/create/update/remove）
├── src/
│   ├── api/
│   │   └── request.ts           # 公共 fetch 封装（request/get/post/put/del），所有请求必须走这里
│   ├── components/              # 跨模块通用组件
│   │   ├── BaseModal.vue        # 通用弹窗（Teleport + 遮罩 + 动画）
│   │   └── Tag.vue              # 通用标签（gold/green/gray/red）
│   ├── modules/                 # ★ 业务模块（一个模块一个目录）
│   │   ├── <模块>/
│   │   │   ├── api.ts           # 该模块的类型定义 + API 函数（基于 src/api/request）
│   │   │   ├── index.vue        # 页面入口：负责数据加载、状态管理、子组件组装
│   │   │   ├── <XX>Card.vue     # 展示型子组件（纯展示，props 进 / emit 出）
│   │   │   └── <XX>Dialog.vue   # 弹窗型子组件（基于 BaseModal）
│   │   ├── overview/  ledger/  calendar/  todo/  notes/  habits/
│   ├── router/
│   │   └── index.ts             # 路由懒加载指向 ../modules/<模块>/index.vue
│   ├── App.vue                  # 布局骨架（左侧导航 + 右侧内容区 RouterView）
│   └── style.css                # 全局样式（设计 token、通用类）
```

**铁律**：
- 新增业务功能 → 在 `src/modules/` 下建（或复用）模块目录，**禁止**在 `index.vue` 里堆超过 300 行
- 通用能力（弹窗/标签/请求）被 2 个以上模块使用 → 提到 `src/components/` 或 `src/api/`
- 每个模块的 `api.ts` 是唯一的 API 出口，组件内**禁止**裸 `fetch`

## 二、命名规范

| 对象 | 规则 | 示例 |
|---|---|---|
| 模块目录 | 小写英文，单数 | `ledger/` `todo/` |
| 页面入口 | `index.vue` | `modules/ledger/index.vue` |
| 子组件 | PascalCase，模块前缀 | `LedgerDialog.vue` `NoteCard.vue` |
| API 文件 | `api.ts`，导出 `xxxApi` 对象 | `ledgerApi.list()` |
| 类型 | PascalCase，`export interface` | `TodoItem` `LedgerData` |
| 路由 path | 小写英文 | `/ledger` `/calendar` |
| 事件 | kebab-case 动词（emit 命名） | `@submit` `@remove` `@toggle` |
| CSS 类 | kebab-case | `.card-grid` `.add-btn` |

## 三、组件规范

### 3.1 展示组件（Card/List 类）
- **props 进、emit 出**：数据通过 props 传入，交互通过 emit 通知父组件
- 组件内部**不直接发请求**（fetch 只在 `index.vue` 或 api.ts 层）
- 示例：

```vue
<script setup lang="ts">
defineProps<{ items: TodoItem[] }>()
const emit = defineEmits<{ (e: 'remove', id: string): void }>()
</script>
```

### 3.2 弹窗组件（Dialog 类）
- 必须基于 `src/components/BaseModal.vue`
- 父组件控制 `open` 状态，子组件 emit `close` / `submit`
- 打开时通过 `watch(props.open)` 重置表单

### 3.3 页面入口（index.vue）
- 职责：数据加载（onMounted）、状态管理、子组件组装
- 用 `loading / error / data` 三态模板：加载中 → 占位符；错误 → 提示；成功 → 内容

## 四、API 封装规范

- 所有请求走 `src/api/request.ts` 的 `get/post/put/del`
- 模块 API 集中在 `modules/<模块>/api.ts`：

```ts
import { get, post, del } from '../../api/request'

export const ledgerApi = {
  list: () => get<LedgerData>('/api/ledger'),
  create: (input: CreateInput) => post<{ ok: boolean; id: string }>('/api/ledger', input),
  remove: (id: string) => del<{ ok: boolean }>(`/api/ledger/${id}`),
}
```

## 五、样式规范

### 5.1 设计 token（全局 `style.css`，来源 `agents/skills/apple-design-skill/tokens.css`，勿另起炉灶）

| Token | 值 | 用途 |
|---|---|---|
| 页面底色 `--bg` | `#f5f5f7` 冷灰白（**绝不**暖/米色） | 页面背景 |
| 表面 `--surface` | `#ffffff` | 面板、卡片 |
| 行 hover `--hover` | `#fbfbfd` | 行悬停 |
| 主文字 `--text` | `#1d1d1f` | 标题、正文主色 |
| 正文/次要 `--text-body` / `--text-2` | `#424245` / `#6e6e73` | 长文 / 摘要、meta |
| 三级/占位 `--text-3` / `--text-4` | `#86868b` / `#aeaeb2` | 说明 / 占位 |
| hairline `--hairline` | `rgba(0,0,0,0.07)` | 全站分割线 |
| 强调 `--accent` | `#0071e3` Apple 蓝 | 主按钮、链接、focus |
| 强调链接 `--accent-link` | `#0066cc` | 着色底上的链接文字 |
| 热力 `--heat` | `#ff6b00` | 支出、热度（仅语义需要时） |
| 在线/成功 `--live` | `#30d158` | 完成、在线（脉动点） |
| 渐变 | `--grad-blue` 等 | 仅 hero / CTA / 占位图 |
| 组件灰 `--track` | `#e8e8ed` | 进度/开关轨道 |

### 5.2 圆角与阴影（语义层级，禁止自创中间值）

| 层级 | 值 | 用途 |
|---|---|---|
| `--r-pill` | `999px` | 按钮、分段控件、标签 |
| `--r-card` | `18px` | 标准卡片 |
| `--r-panel` | `22px` | 大面板/区块容器 |
| `--r-hero` | `26px` | hero / CTA |
| `--r-sheet` | `16px` | 弹窗内全宽堆叠按钮 |
| 阴影 | `--sh-card` / `--sh-panel` / `--sh-overlay` 等 | **一律双层阴影**，禁止单层硬阴影 |

### 5.3 排版

- 字体栈用系统字体（SF Pro / PingFang SC / Microsoft YaHei），**禁止** Inter/Roboto 当品牌字体：
  ```css
  --font: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display',
          'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  ```
- H1 `clamp(27px,5vw,46px)` 700 **负字距 `-0.03em`**，行高 1.1–1.18；H2 `clamp(20px,3.4vw,26px)` 700 `-0.02em`
- 长文正文 `clamp(16px,2.6vw,18px)`，行高 **≥ 1.85**；正文/摘要 15–19px，行高 1.55–1.7
- 标题字号越大负字距越多；数字一律 `font-variant-numeric: tabular-nums`；根元素 `font-optical-sizing: auto`

### 5.4 通用类（`style.css` 全局）

- `.card-grid` `.card` `.card-title` `.big-num` `.row-list` `.row` `.tag` `.placeholder`
- 模块内样式用 `<style scoped>`，**禁止**污染全局
- 布局用 flex/grid + `gap`（禁止 inline + margin）；响应式尺寸用 `clamp()`；触控目标 ≥ 44px

### 5.5 玻璃（Liquid Glass）配方

- **仅**用于：sticky 导航、弹窗/popover、彩色 CTA 上的标签；普通内容块 = 纯白 + 阴影
- 导航玻璃：`background: rgba(245,245,247,0.72); backdrop-filter: saturate(180%) blur(20px);`
- 滚动边缘效果：内容滚动到下方时才显示 hairline（`scrolled` 类切换），不做永久 1px 边框
- 彩色底上的玻璃元素：`rgba(255,255,255,0.16)` + `blur(8px)`，背后需放模糊光斑

### 5.6 动效

- 静态内容小预算：hover lift（`translateY(-2~-3px)` + 加深阴影，`~200ms var(--ease-out-quart)`）
- 交互层（弹窗/sheet/popover）：读 `motion.md` —— pointer-down 反馈、进入 `~400ms var(--ease-spring)`、同路径进出、玻璃 materialize（blur+scale+opacity 同时）、可中断、三个 `prefers-reduced-*` 媒体查询
- 禁止异步内容入场 opacity-fade keyframes（重渲染会卡在 0）

### 5.7 响应式

- Mobile-first，全部 `clamp()`；断点 ~`680px` 两列合一列、隐藏次要信息；触控目标 ≥ 44px

## 六、Mock 约定（开发环境）

- mock 文件在 `lairweb/mock/`，仅开发模式生效（vite-plugin-mock-dev-server）
- **内存态**：运行中增删改查直接改内存，**重启 dev server 即恢复初始数据**（无持久化）
- 初始数据由 `mock/store.ts` 固定 seed 生成，每次启动一致
- mock 文件结构：`export default { list, create, update, remove }`，各接口用 `defineMock({ url, method, body })`
- **共享 store 必须走 `globalThis.__openlair_mock__`**（插件对每个 mock 文件单独 bundle，模块级变量会导致实例隔离、id 冲突、数据不互通）
- 路由匹配：`/api/<模块>`（列表/新增）、`/api/<模块>/:id`（更新/删除）

## 七、新增模块 Checklist

1. `src/modules/<模块>/api.ts`：类型 + API 函数
2. `src/modules/<模块>/index.vue`：页面入口（三态模板）
3. 子组件按需拆分（Card/Dialog），复用 BaseModal / Tag
4. `src/router/index.ts` 加路由（懒加载，meta.title 中文）
5. `App.vue` 导航数组加项（SVG 图标 path）
6. `mock/<模块>.mock.ts` + `mock/store.ts` 加初始数据
7. `pnpm run build` 通过 + 浏览器实测

## 八、License 说明

Skill 文件为 MIT（naplesblue；动效层 MIT © Emil Kowalski；图标 ISC © Lucide Contributors）。它传授视觉语言，不附带任何 Apple 素材；与 Apple Inc. 无隶属或背书关系。
