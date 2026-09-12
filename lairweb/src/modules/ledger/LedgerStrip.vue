<script setup lang="ts">
// 摘要条：本月支出/收入/结余/预算剩余 + 近6月趋势迷你图
// 单行紧凑白面板，hairline 分格（panel-not-cards：同层级信息进一个表面）
// 预算支持内联编辑（原 LedgerBudget 的能力收敛到这一格）
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { LedgerSummary, TrendPoint } from './api'
import { money } from './format'

const props = defineProps<{
  summary: LedgerSummary
  budget: number
  trend: TrendPoint[]
}>()

const emit = defineEmits<{
  (e: 'save-budget', amount: number): void
}>()

// ---------- 预算内联编辑 ----------
const editing = ref(false)
const draft = ref('')

const over = computed(() => props.budget > 0 && props.summary.expense > props.budget)
const left = computed(() => Number((props.budget - props.summary.expense).toFixed(2)))
const percent = computed(() =>
  props.budget > 0 ? Math.min(100, (props.summary.expense / props.budget) * 100) : 0,
)

function startEdit() {
  draft.value = String(props.budget)
  editing.value = true
}

function save() {
  const n = Number(draft.value)
  if (Number.isFinite(n) && n >= 0) emit('save-budget', n)
  editing.value = false
}

function cancel() {
  editing.value = false
}

// ---------- 近6月迷你趋势（无图表库，纯 CSS 细柱；当前月高亮与左侧「本月」数字呼应） ----------
const trendMax = computed(() => {
  let m = 0
  for (const p of props.trend) m = Math.max(m, p.expense, p.income)
  return m || 1
})

const now = new Date()
const curMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

const monthLabel = (m: string) => `${Number(m.split('-')[1])}月`
</script>

<template>
  <section class="strip" aria-label="收支摘要条">
    <div class="cell">
      <span class="lbl">本月支出</span>
      <span class="val num">{{ money(summary.expense) }}</span>
    </div>
    <div class="cell">
      <span class="lbl">本月收入</span>
      <span class="val num income">{{ money(summary.income) }}</span>
    </div>
    <div class="cell">
      <span class="lbl">本月结余</span>
      <span class="val num">{{ money(summary.balance) }}</span>
    </div>

    <div class="cell budget">
      <template v-if="editing">
        <Input
          v-model="draft"
          type="number"
          min="0"
          step="100"
          class="h-8 flex-1 min-w-0 px-3 border-[var(--hairline)]! rounded-[var(--r-thumb)]! bg-white shadow-none! text-[0.9rem]"
          autofocus
          @keyup.enter="save"
          @keyup.esc="cancel"
        />
        <Button size="sm" class="h-8 rounded-full! px-3 text-[12px]" @click="save">保存</Button>
        <Button variant="outline" size="sm" class="h-8 rounded-full! px-3 text-[12px]" @click="cancel">取消</Button>
      </template>
      <template v-else>
        <span class="lbl">
          本月预算
          <Button
            variant="ghost"
            size="sm"
            class="h-auto min-w-0 px-1.5 py-0 text-[11.5px] font-semibold text-primary bg-transparent rounded-full! hover:bg-primary/6"
            @click="startEdit"
          >调整</Button>
        </span>
        <span class="val num" :class="{ over }">
          <template v-if="over">超支 {{ money(Math.abs(left), 0) }}</template>
          <template v-else>剩余 {{ money(left, 0) }}</template>
        </span>
        <div class="meter" :class="{ over }">
          <i :style="{ width: percent + '%' }"></i>
        </div>
      </template>
    </div>

    <div class="cell trend">
      <span class="lbl">近 6 月</span>
      <div v-if="trend.length === 0" class="trend-empty">暂无</div>
      <div v-else class="mini-bars" role="img" aria-label="近 6 月收支趋势">
        <div
          v-for="p in trend"
          :key="p.month"
          class="mini-col"
          :class="{ cur: p.month === curMonthKey }"
          :title="`${monthLabel(p.month)} 收入 ¥${p.income.toFixed(0)} · 支出 ¥${p.expense.toFixed(0)}`"
        >
          <div class="mini-pair">
            <i class="inc" :style="{ height: Math.max(2, (p.income / trendMax) * 100) + '%' }"></i>
            <i class="exp" :style="{ height: Math.max(2, (p.expense / trendMax) * 100) + '%' }"></i>
          </div>
          <span class="mini-lbl">{{ monthLabel(p.month) }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.strip {
  display: flex;
  align-items: stretch;
  padding: 12px 6px;
  border-radius: var(--r-panel);
  background: var(--surface);
  box-shadow: var(--sh-panel);
}
.cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  padding: 4px 18px;
  min-width: 0;
}
.cell + .cell {
  border-left: 1px solid var(--hairline);
}
.lbl {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.02em;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
}
.val {
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--text);
  white-space: nowrap;
}
.val.income {
  color: var(--live);
}
.val.over {
  color: var(--heat);
}

/* 预算格 */
.budget {
  flex: 1 1 0;
  min-width: 170px;
}
.budget .meter {
  width: 100%;
  max-width: 150px;
  height: 4px;
  border-radius: var(--r-pill);
  background: var(--track);
  overflow: hidden;
}
.budget .meter i {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--accent);
  transition: width 400ms var(--ease-out-quart), background 300ms ease;
}
.budget .meter.over i {
  background: var(--heat);
}

/* 趋势格：贴右收尾 */
.trend {
  flex: 0 1 auto;
  margin-left: auto;
  align-items: flex-end;
}
.trend-empty {
  font-size: 12px;
  color: var(--text-4);
  padding: 6px 0;
}
.mini-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 34px;
}
.mini-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  height: 100%;
}
.mini-pair {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 2px;
}
.mini-pair i {
  display: block;
  width: 4px;
  border-radius: 2px;
  transition: height 400ms var(--ease-out-quart);
}
.mini-pair .inc {
  background: var(--live);
  opacity: 0.85;
}
.mini-pair .exp {
  background: var(--text);
  opacity: 0.65;
}
/* 当前月柱体提亮，与左侧「本月」数字呼应 */
.mini-col.cur .mini-pair i {
  opacity: 1;
}
.mini-col.cur .mini-lbl {
  color: var(--text-2);
  font-weight: 600;
}
.mini-lbl {
  font-size: 9.5px;
  color: var(--text-3);
  white-space: nowrap;
}

@media (max-width: 960px) {
  .strip {
    flex-wrap: wrap;
    row-gap: 12px;
  }
  .cell + .cell {
    border-left: 0;
  }
  .trend {
    margin-left: 0;
    width: 100%;
    align-items: flex-start;
  }
}

/* 窄屏：两列网格对齐，预算/趋势各占整行 */
@media (max-width: 680px) {
  .strip {
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 4px 0;
  }
  .cell {
    padding: 10px 16px;
  }
  .budget,
  .trend {
    grid-column: 1 / -1;
  }
  .trend {
    align-items: flex-start;
  }
}
</style>
