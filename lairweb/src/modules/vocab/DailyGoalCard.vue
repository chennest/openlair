<script setup lang="ts">
// 每日背词目标卡：新词 / 复习两条并列进度（今日已做 N / 目标）+ 各自达标态，
// 「修改目标」就地弹窗改两个数字；卡底是**今日任务入口**（动态文案，见下）。
//
// 数字口径：新词看进度表首学时间（今日新学的词），复习看今日回顾且首次学习更早的老词 ——
// 都是「词数」不是「作答次数」，同一个词一节课里答多次只算 1 个。
import { computed, ref, watch } from 'vue'
import { Check, Pencil, Play, Target } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import BaseModal from '../../components/BaseModal.vue'
import type { VocabDailyGoal } from './api'

const props = defineProps<{
  goal: VocabDailyGoal
  saving: boolean
  error: string
  /** 有没有可练的词书：没有就不摆入口（去词书墙的导入卡更合适） */
  canStart: boolean
}>()

const emit = defineEmits<{
  (e: 'save', patch: { newTarget?: number; reviewTarget?: number }): void
  (e: 'start'): void
}>()

const open = ref(false)
const draftNew = ref('')
const draftReview = ref('')

/** 百分比：达标后封顶 100（今日超额完成也不让条溢出） */
function pct(done: number, target: number): number {
  return target > 0 ? Math.min(100, Math.round((done / target) * 100)) : 0
}

const newPct = computed(() => pct(props.goal.todayNew, props.goal.newTarget))
const reviewPct = computed(() => pct(props.goal.todayReviewed, props.goal.reviewTarget))

/** 今日任务是否全部完成（新词 + 复习两侧都达标）—— 入口文案与语义的唯一判据 */
const allDone = computed(() => props.goal.achieved && props.goal.reviewAchieved)

/** 未完成时列出还差什么；已完成时说明「还能接着学」 */
const footHint = computed(() => {
  if (allDone.value) return '今日任务已完成 · 想多学就接着来，不嫌多'
  const parts: string[] = []
  if (!props.goal.achieved) parts.push(`新词还差 ${props.goal.remaining} 个`)
  if (!props.goal.reviewAchieved) parts.push(`复习还差 ${props.goal.reviewRemaining} 个`)
  return parts.join(' · ')
})

function openEdit() {
  draftNew.value = String(props.goal.newTarget)
  draftReview.value = String(props.goal.reviewTarget)
  open.value = true
}

/** 解析输入：与后端区间一致（1–100），非法返回 null */
function parseTarget(raw: string): number | null {
  const n = Math.trunc(Number(raw))
  return Number.isFinite(n) && n >= 1 && n <= 100 ? n : null
}

function submit() {
  const nextNew = parseTarget(draftNew.value)
  const nextReview = parseTarget(draftReview.value)
  if (nextNew === null || nextReview === null) return

  // 只提交真正变了的字段（后端也是「只更新出现的字段」语义）
  const patch: { newTarget?: number; reviewTarget?: number } = {}
  if (nextNew !== props.goal.newTarget) patch.newTarget = nextNew
  if (nextReview !== props.goal.reviewTarget) patch.reviewTarget = nextReview
  if (!Object.keys(patch).length) {
    open.value = false // 没改动就当取消收起，免得点了「保存」毫无反应
    return
  }
  emit('save', patch)
}

// 目标被父组件回读更新 = 保存成功 → 收起弹窗；失败时值不变，弹窗留着显示错误。
// 只在值真变时才 emit，所以这里不会被无关刷新误触发。
watch(
  () => `${props.goal.newTarget},${props.goal.reviewTarget}`,
  () => {
    open.value = false
  },
)
</script>

<template>
  <section class="goal-card">
    <div class="goal-head">
      <span class="goal-title">
        <Target class="size-4" aria-hidden="true" />
        今日目标
      </span>
      <Button variant="ghost" size="sm" class="goal-edit" @click="openEdit">
        <Pencil class="size-3.5" />
        修改目标
      </Button>
    </div>

    <div class="goal-grid">
      <div class="goal-item" :class="{ done: goal.achieved }">
        <div class="goal-item-head">
          <span class="goal-label">新词</span>
          <span v-if="goal.achieved" class="goal-badge">
            <Check class="size-3" aria-hidden="true" />
            已达标
          </span>
        </div>
        <p class="goal-num">
          <span class="big-num">{{ goal.todayNew }}</span>
          <span class="goal-of">/ {{ goal.newTarget }} 词</span>
        </p>
        <div
          class="goal-bar"
          role="progressbar"
          :aria-valuenow="newPct"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="今日新词目标完成度"
        >
          <span class="goal-fill" :style="{ width: `${newPct}%` }" />
        </div>
        <p class="goal-hint">{{ goal.achieved ? '今日新词已完成' : `还差 ${goal.remaining} 个` }}</p>
      </div>

      <div class="goal-item" :class="{ done: goal.reviewAchieved }">
        <div class="goal-item-head">
          <span class="goal-label">复习</span>
          <span v-if="goal.reviewAchieved" class="goal-badge">
            <Check class="size-3" aria-hidden="true" />
            已达标
          </span>
        </div>
        <p class="goal-num">
          <span class="big-num">{{ goal.todayReviewed }}</span>
          <span class="goal-of">/ {{ goal.reviewTarget }} 词</span>
        </p>
        <div
          class="goal-bar"
          role="progressbar"
          :aria-valuenow="reviewPct"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="今日复习目标完成度"
        >
          <span class="goal-fill" :style="{ width: `${reviewPct}%` }" />
        </div>
        <p class="goal-hint">{{ goal.reviewAchieved ? '今日复习已完成' : `还差 ${goal.reviewRemaining} 个` }}</p>
      </div>
    </div>

    <!-- 今日任务入口：未完成 → 开始学习（今日任务）；已达标 → 继续学习。
         不达标与达标都给出口，永不留「只剩一句完成提示」的死胡同。 -->
    <div v-if="canStart" class="goal-foot">
      <Button class="goal-cta rounded-full px-5 shadow-[var(--sh-cta)]" @click="emit('start')">
        <Play v-if="!allDone" class="size-4" aria-hidden="true" />
        {{ allDone ? '继续学习' : '开始学习（今日任务）' }}
      </Button>
      <span class="goal-cta-hint">{{ footHint }}</span>
    </div>

    <BaseModal v-if="open" title="修改每日目标" @close="open = false">
      <form class="goal-form" @submit.prevent="submit">
        <div class="field">
          <Label for="goal-new">每日新词目标</Label>
          <Input id="goal-new" v-model="draftNew" type="number" min="1" max="100" step="1" inputmode="numeric" />
        </div>
        <div class="field">
          <Label for="goal-review">每日复习目标</Label>
          <Input id="goal-review" v-model="draftReview" type="number" min="1" max="100" step="1" inputmode="numeric" />
        </div>
        <p class="hint">
          取值 1–100。目标是默认配额、不是上限：达标后默认不再发放该类别，但可以用卡片的「继续学习」按组加码；
          错词本与收藏复习不受此限制。
        </p>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="foot">
          <Button type="button" variant="ghost" class="flex-1" :disabled="saving" @click="open = false">取消</Button>
          <Button type="submit" class="flex-1" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</Button>
        </div>
      </form>
    </BaseModal>
  </section>
</template>

<style scoped>
.goal-card {
  margin-top: 18px;
  padding: 18px 22px 20px;
  border-radius: var(--r-card);
  background: var(--surface);
  box-shadow: var(--sh-card);
}

.goal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.goal-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--text-2);
  font-size: 0.84rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.goal-edit {
  flex: none;
  border-radius: var(--r-pill);
  color: var(--text-3);
}
.goal-edit:hover {
  color: var(--accent);
  background: rgba(var(--accent-rgb), 0.07);
}

/* 新词 / 复习两条并列，中间一条 hairline 收口（不再各自描边成两张小卡） */
.goal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 14px;
}
.goal-item + .goal-item {
  padding-left: 26px;
  border-left: 1px solid var(--hairline);
}

.goal-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 20px;
}
.goal-label {
  color: var(--text-2);
  font-size: 0.78rem;
  font-weight: 600;
}
.goal-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: var(--r-pill);
  background: rgba(48, 209, 88, 0.14);
  color: var(--live);
  font-size: 0.68rem;
  font-weight: 600;
}

.goal-num {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 6px 0 0;
}
.goal-of {
  color: var(--text-3);
  font-size: 0.82rem;
  font-weight: 600;
}

.goal-bar {
  margin-top: 10px;
  height: 6px;
  border-radius: var(--r-pill);
  background: var(--track);
  overflow: hidden;
}
.goal-fill {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--accent);
  transition: width 420ms var(--ease-out-quart);
}
.goal-item.done .goal-fill {
  background: var(--live);
}

.goal-hint {
  margin: 7px 0 0;
  color: var(--text-3);
  font-size: 0.76rem;
}

/* 今日任务入口：与上方两条进度用 hairline 分段（信息区 / 操作区分离） */
.goal-foot {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--hairline);
}
.goal-cta {
  flex: none;
}
.goal-cta-hint {
  color: var(--text-3);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 680px) {
  .goal-foot {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .goal-cta-hint {
    text-align: center;
  }
}

.goal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.hint {
  margin: 0;
  color: var(--text-3);
  font-size: 0.78rem;
  line-height: 1.45;
}
.error {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--r-thumb);
  background: rgba(255, 59, 48, 0.08);
  color: var(--destructive);
  font-size: 0.84rem;
}
.foot {
  display: flex;
  gap: 10px;
}

/* 窄屏：两条改成纵向堆叠，hairline 从竖线换横线 */
@media (max-width: 680px) {
  .goal-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .goal-item + .goal-item {
    margin-top: 18px;
    padding: 18px 0 0;
    border-left: 0;
    border-top: 1px solid var(--hairline);
  }
}
</style>
