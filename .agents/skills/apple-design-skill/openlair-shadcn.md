# OpenLair — shadcn + Apple Liquid Glass 融合规范

> 本文件是 apple-design-skill 在 OpenLair 项目（`lairweb/`）的**落地桥接**。
> 视觉语言（token/面板/玻璃/动效）仍以本 skill 的 `design-system.md`、`tokens.css`、`motion.md` 为准；
> **组件层改用 shadcn-vue**，本文件描述如何融合。开发 `lairweb` 前必读。

## 一、现实技术栈

| 层 | 技术 | 位置 |
|---|---|---|
| 框架 | Vue 3 + TypeScript + Vite | `lairweb/` |
| 样式 | **Tailwind CSS v4** | `vite.config.ts` 挂 `@tailwindcss/vite` |
| 组件 | **shadcn-vue**（源码复制模式，非 npm 包） | `lairweb/src/components/ui/` |
| 图标 | `@lucide/vue` 命名导出 | —— |
| 弹窗 | 项目自研 `BaseModal.vue`（Apple 玻璃 modal，保留使用） | `lairweb/src/components/` |
| 字体 | 系统字体栈（**禁止** Google Fonts / Inter） | `style.css --font` |

## 二、三层融合模型（改样式前先定位属于哪层）

1. **Token 层（色彩/圆角/阴影）**
   - `src/style.css` `:root` = Apple token 的**唯一来源**（`--bg/--surface/--text/--accent/--hairline/--r-card/--sh-card/--ease-spring` …）
   - `src/assets/tailwind.css` = shadcn 语义变量 **`var()` 引用**上述 token（`--primary→var(--accent)`、`--border→var(--hairline)`、`--background→var(--bg)`、`--radius:0.75rem`）
   - **规则：组件里永远用 shadcn 语义类**（`bg-card/text-muted-foreground/border-border/rounded-xl`）**或 Apple token**（`var(--accent)`），禁止硬编码 hex/px。

2. **组件层（交互控件）** — `src/components/ui/`
   - 已有：button / card / input / label / textarea / select / tabs / switch / progress / table / badge / alert / avatar / dialog / popover / dropdown-menu / tooltip / skeleton / separator / scroll-area / message / bubble / message-scroller / calendar / native-select / sonner…
   - **优先用 shadcn 组件**，不要手写按钮/输入/下拉/开关/日历。
   - 组件是**源码在项目里**的：需要时可改 `src/components/ui/` 下的实现（加插槽、调样式），改完属于项目代码。

3. **布局层（Apple 面板/容器）** — `style.css` 全局类 + `patterns.md`
   - 页面骨架：`.workspace/.sidebar/.content`、`.m-*` 手机壳（App.vue）
   - 内容容器：`.card-grid/.card/.row-list/.row/.tag/.placeholder`（Apple 面板 + hairline 分割，**panel-not-cards**）
   - 展示结构用这些类；**内部的交互控件**（按钮/输入/开关/标签徽章）换 shadcn 组件。

## 三、使用规则

1. **交互控件 → shadcn**：`Button / Input / Textarea / Select / Tabs / Switch / Progress / Table / Badge / Alert`；图标一律 `@lucide/vue`。
2. **展示结构 → Apple 类**：`.card-grid/.card/.row-list/.row`；卡片标题区 = `.card-title`。
3. **弹窗 → BaseModal**（保留），弹窗内部表单控件用 shadcn；（新的独立浮层可用 shadcn `Dialog/Popover` + Apple token）。
4. **日历 → shadcn Calendar**：`#calendar-cell` 插槽可自定义格子内容（日程条/圆点），`#calendar-heading` 可定制月份标题；传 `locale="zh-CN"`、`weekday-format="short"`（表头显示周一~周日）。
5. **颜色/圆角/阴影**：shadcn 语义类（映射 Apple token）或 `var(--…)`；禁止硬编码。
6. **字体**：系统栈，禁止 Google Fonts / Inter 品牌字体。

## 四、常用命令

```bash
# 新增 shadcn 组件（⚠ 必须带 COREPACK_ENABLE_STRICT=0，否则 corepack 报错）
COREPACK_ENABLE_STRICT=0 pnpm dlx shadcn-vue@latest add <组件名> -y
# add 之后必须做两件事：
#   1) 删掉 src/assets/tailwind.css 顶部被塞入的 @import url('fonts.googleapis...')（项目禁用外网字体）
#   2) 检查 @internationalized/date 等 peer 依赖是否装好（CLI 有时漏装，手动 pnpm add）

# 验证（类型检查 + 构建）
pnpm run build
```

## 五、已知坑（踩过，别重踩）

1. **`--accent` 撞名（严重）**：`style.css` 的 `--accent` = Apple 蓝 `#0071e3`；shadcn 变量的 `--accent` = 浅灰 hover。`tailwind.css` 后加载会覆盖，**必须保持 `--accent: #0071e3` 同值**（shadcn 的 accent hover 语义随之弱化为蓝底白字，可接受）。若被改成浅灰 → 全局 primary 按钮变白字浅底，必坏。
2. **scoped 样式命中不了 shadcn 子组件根**：shadcn 组件把 `class` 作为 prop 接收时，子组件根元素不带父的 `data-v`（如给 `<Calendar class="cal-root">` 写 `.cal-root :deep(...)` 会失效）。**改用页面根穿透**（`.calendar :deep([data-slot=...])`）或直接给组件传 Tailwind class。
3. **CLI add 塞 Google Fonts**：每次 `add` 都会往 `tailwind.css` 顶部插 `@import url('fonts.googleapis...')`，记得删。
4. **reka 网格空位**：`Calendar` 的 `month.rows` 在部分月份最后一行不足 7 格；自定义 `#calendar-cell` 时对 `date` 判空（`v-if="date"`），`dayKey()` 之类函数入参判空。
5. **`as any`/`@ts-ignore`**：禁止。

## 六、完成门禁

- `pnpm run build` 通过（含 vue-tsc 类型检查，**类型错误会直接失败**）
- 无 Google Fonts、无硬编码色值、无 `as any`
- 交互控件用 shadcn、展示结构用 Apple 面板类、图标用 lucide
- 移动端（≤860px）布局可用（`m-*` 手机壳 + 响应式）
