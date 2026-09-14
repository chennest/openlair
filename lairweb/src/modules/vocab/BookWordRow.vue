<script setup lang="ts">
// 词书详情列表行：发音 + 状态 + 对错/复习 + 模式覆盖 + 行内操作；点击行展开释义例句短语
import { computed, ref } from 'vue'
import { Volume2 } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { playSentence, playWord } from './audio'
import {
  MASTER_LABEL,
  UNMASTER_LABEL,
  reviewDueText,
  statusMeta,
  tone,
  wordMeaning,
} from './status'
import type { BookWordItem } from './api'

const props = defineProps<{ item: BookWordItem }>()
const emit = defineEmits<{
  collect: [wordId: number]
  master: [wordId: number]
  dismissWrong: [wordId: number]
}>()

const expanded = ref(false)

const progress = computed(() => props.item.progress)

/** 状态标签：未学 / 学习中 / 已记住（文案与配色统一在 status.ts） */
const status = computed(() => statusMeta(progress.value?.status))
const isMastered = computed(() => progress.value?.status === 'mastered')

const meaning = computed(() => wordMeaning(props.item.translations))

const dueText = computed(() => reviewDueText(progress.value?.due))

/** 模式覆盖 chip：练过的显示次数，没练过的显示「–」并置灰 */
const modeChips = computed(() => {
  const p = props.item.practice
  return [
    { key: 'follow', label: '跟打', count: p.follow },
    { key: 'dictation', label: '听写', count: p.dictation },
    { key: 'self_test', label: '自测', count: p.selfTest },
    { key: 'spell', label: '默写', count: p.spell },
  ]
})

const hasDetail = computed(
  () => props.item.translations.length > 1 || props.item.sentences.length > 0 || props.item.phrases.length > 0,
)
</script>

<template>
  <div class="word-row">
    <div class="row-main" role="button" tabindex="0" @click="expanded = !expanded" @keydown.enter="expanded = !expanded">
      <Button
        variant="ghost"
        size="icon-sm"
        class="rounded-full text-[var(--accent)] hover:bg-[rgba(var(--accent-rgb),0.08)] hover:text-[var(--accent)]"
        aria-label="播放发音"
        @click.stop="playWord(item.word)"
      >
        <Volume2 class="size-4" />
      </Button>

      <div class="word-main">
        <div class="word-line">
          <span class="w">{{ item.word }}</span>
          <span v-if="item.phoneticUs || item.phoneticUk" class="p">/{{ item.phoneticUs || item.phoneticUk }}/</span>
          <Badge variant="ghost" :class="tone(status.tone)">{{ status.label }}</Badge>
          <Badge v-if="progress?.wrongActive" variant="ghost" :class="tone('red')">错词本</Badge>
          <Badge v-if="progress?.collected" variant="ghost" :class="tone('gold')">收藏</Badge>
        </div>
        <p class="m">{{ meaning || '暂无释义' }}</p>
      </div>

      <div class="metric">
        <span v-if="progress" class="counts">
          对 <b>{{ progress.rightCount }}</b> 错 <b>{{ progress.wrongCount }}</b>
        </span>
        <span v-else class="counts none">尚无练习记录</span>
        <span v-if="dueText" class="due">{{ dueText }}</span>
      </div>

      <div class="modes" title="练习次数为全局口径：该词在全部练习里的练过次数（含错词本/收藏练习）">
        <span v-for="m in modeChips" :key="m.key" class="chip" :class="{ on: m.count > 0 }">
          {{ m.label }} {{ m.count > 0 ? m.count : '–' }}
        </span>
      </div>

      <div class="actions" @click.stop>
        <Button
          :variant="progress?.collected ? 'outline' : 'ghost'"
          size="sm"
          class="rounded-full"
          :class="progress?.collected ? '' : 'text-[var(--text-2)]'"
          @click="emit('collect', item.id)"
        >
          {{ progress?.collected ? '取消收藏' : '收藏' }}
        </Button>
        <Button
          v-if="progress?.wrongActive"
          variant="ghost"
          size="sm"
          class="rounded-full text-[var(--text-2)]"
          @click="emit('dismissWrong', item.id)"
        >移出错词本</Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-full"
          @click="emit('master', item.id)"
        >{{ isMastered ? UNMASTER_LABEL : MASTER_LABEL }}</Button>
      </div>
    </div>

    <div v-if="expanded" class="row-detail">
      <div v-if="item.translations.length" class="detail-block">
        <h4>释义</h4>
        <p v-for="(t, i) in item.translations" :key="`t${i}`">{{ t.pos }} {{ t.cn }}</p>
      </div>
      <div v-if="item.sentences.length" class="detail-block">
        <h4>例句</h4>
        <p v-for="(s, i) in item.sentences" :key="`s${i}`" class="sent" @click="playSentence(s.en)">
          {{ s.en }}<span class="cn">{{ s.cn }}</span>
        </p>
      </div>
      <div v-if="item.phrases.length" class="detail-block">
        <h4>短语</h4>
        <p>{{ item.phrases.join(' · ') }}</p>
      </div>
      <p v-if="!hasDetail" class="detail-empty">该词暂无更多释义数据</p>
    </div>
  </div>
</template>

<style scoped>
.word-row {
  border-bottom: 1px solid var(--hairline);
}
.word-row:last-child {
  border-bottom: none;
}
.row-main {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.row-main:hover {
  background: var(--hover);
}
.row-main:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.word-main {
  flex: 1;
  min-width: 0;
}
.word-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.w {
  font-weight: 700;
  font-size: 1rem;
}
.p {
  color: var(--text-3);
  font-size: 0.8rem;
}
.m {
  margin: 3px 0 0;
  color: var(--text-2);
  font-size: 0.84rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: 0.74rem;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.metric b {
  color: var(--text-2);
}
.counts.none {
  color: var(--text-4);
}
.due {
  color: var(--heat);
  font-weight: 600;
}

.modes {
  flex: none;
  display: flex;
  gap: 4px;
}
.chip {
  padding: 2px 6px;
  border-radius: var(--r-chip);
  font-size: 0.68rem;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.chip.on {
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--accent);
  font-weight: 600;
}

.actions {
  flex: none;
  display: flex;
  gap: 6px;
}

.row-detail {
  padding: 4px 16px 16px 60px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-block h4 {
  margin: 0 0 4px;
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-4);
  letter-spacing: 0.02em;
}
.detail-block p {
  margin: 0;
  font-size: 0.86rem;
  color: var(--text-body);
  line-height: 1.6;
}
.sent {
  cursor: pointer;
}
.sent:hover {
  color: var(--accent);
}
.sent .cn {
  margin-left: 8px;
  color: var(--text-3);
}
.detail-empty {
  margin: 0;
  font-size: 0.82rem;
  color: var(--text-4);
}

@media (max-width: 1100px) {
  .modes {
    display: none;
  }
}
@media (max-width: 860px) {
  .metric {
    display: none;
  }
  .row-main {
    flex-wrap: wrap;
  }
  .actions {
    width: 100%;
    padding-left: 44px;
  }
  .row-detail {
    padding-left: 16px;
  }
}
</style>
