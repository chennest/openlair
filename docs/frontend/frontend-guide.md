# OpenLair 前端规范（Frontend Guide）

> 本文件是 OpenLair 前端开发的**唯一权威规范**。任何前端改动、新增页面/组件、调整样式、修改 mock，都必须先通读本文件，再动手。所有 AI 代理与协作者默认遵守本规范。

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

### 5.1 设计 token（全局 `style.css` 已定义，勿另起炉灶）
| Token | 值 | 用途 |
|---|---|---|
| 背景 | `#14120f` 系深棕黑 | 页面底色 |
| 主色 | `#f6d37a` 金色 | 主按钮、强调、激活态 |
| 成功 | `#8ee6a5` 青绿 | 完成、收入、在线 |
| 警示 | `#ffac8b` 橙红 | 支出、删除、警告 |
| 文字 | `#f2eadf` 暖白 | 正文 |
| 次要文字 | `rgba(242,234,223,0.5)` | 说明、占位 |

### 5.2 通用类（`style.css` 全局）
- `.card-grid` `.card` `.card-title` `.big-num` `.row-list` `.row` `.tag` `.placeholder`
- 模块内样式用 `<style scoped>`，**禁止**污染全局

### 5.3 排版
- 卡片圆角 18–26px，按钮圆角 12–14px
- 标题字号 clamp 响应式，正文 0.88–0.95rem
- 金额/数字用 `font-variant-numeric: tabular-nums`

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
