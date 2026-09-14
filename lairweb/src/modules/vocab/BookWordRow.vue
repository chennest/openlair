<script setup lang="ts">
// 词书详情列表行：发音 + 状态 + 对错/复习 + 模式覆盖 + 行内操作；点击行展开释义例句短语
import { computed, ref } from 'vue'
import { Volume2 } from '@lucide/vue'
import { playSentence, playWord } from './audio'
import type { BookWordItem } from './api'

const props = defineProps<{ item: BookWordItem }>()
const emit = defineEmits<{
  collect: [wordId: number]
  master: [wordId: number]
  dismissWrong: [wordId: number]
}>()

const expanded = ref(false)

const progress = computed(() => props.item.progress)

const statusText = computed(() => {
  const p = progress.value
  if (!p) return '未学'
  return p.status === 'mastered' ? '已掌握' : '学习中'
})
const statusKind = computed(() => {
  const p = progress.value
  if (!p) return 'none'
  return p.status === 'mastered' ? 'done' : 'learning'
})

const meaning = computed(() =>
  props.item.translations
    .slice(0, 2)
    .map((t) => `${t.pos} ${t.cn}`)
    .join('；'),
)

const dueText = computed(() => {
  const due = progress.value?.due
  if (!due) return ''
  const days = Math.ceil((new Date(due).getTime() - Date.now()) / 86400000)
  if (days <= 0) return '待复习'
  if (days === 1) return '明天复习'
  return `${days} 天后复习`
})

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
  <div class="word-row" :class="{ expanded }">
    <div class="row-main" role="button" tabindex="0" @click="expanded = !expanded" @keydown.enter="expanded = !expanded">
      <button class="sound" type="button" aria-label="播放发音" @click.stop="playWord(item.word)">
        <Volume2 class="size-4" />
      </button>

      <div class="word-main">
        <div class="word-line">
          <span class="w">{{ item.word }}</span>
          <span v-if="item.phoneticUs || item.phoneticUk" class="p">/{{ item.phoneticUs || item.phoneticUk }}/</span>
          <span class="badge" :class="statusKind">{{ statusText }}</span>
          <span v-if="progress?.wrongActive" class="badge wrong">错词本</span>
          <span v-if="progress?.collected" class="badge collect">收藏</span>
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
        <button class="act-btn" type="button" @click="emit('collect', item.id)">
          {{ progress?.collected ? '取消收藏' : '收藏' }}
        </button>
        <button v-if="progress?.wrongActive" class="act-btn" type="button" @click="emit('dismissWrong', item.id)">
          移出错词本
        </button>
        <button class="act-btn" type="button" @click="emit('master', item.id)">
          {{ progress?.status === 'mastered' ? '取消掌握' : '已掌握' }}
        </button>
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
  gap: 14px;
  padding: 13px 16px;
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

.sound {
  flex: none;
  display: inline-flex;
  padding: 8px;
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
}
.sound:hover {
  background: rgba(0, 113, 227, 0.08);
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
.badge {
  flex: none;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-3);
}
.badge.learning {
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
}
.badge.done {
  background: rgba(48, 209, 88, 0.14);
  color: #1a7f37;
}
.badge.wrong {
  background: rgba(255, 59, 48, 0.1);
  color: #d70015;
}
.badge.collect {
  background: rgba(255, 149, 0, 0.14);
  color: #a05a00;
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
  border-radius: 6px;
  font-size: 0.68rem;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-4);
  font-variant-numeric: tabular-nums;
}
.chip.on {
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
  font-weight: 600;
}

.actions {
  flex: none;
  display: flex;
  gap: 8px;
}
.act-btn {
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: transparent;
  padding: 6px 12px;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-2);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.act-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
}
.act-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.row-detail {
  padding: 4px 16px 16px 58px;
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

@media (max-width: 900px) {
  .modes {
    display: none;
  }
}
@media (max-width: 680px) {
  .metric {
    display: none;
  }
  .row-main {
    flex-wrap: wrap;
  }
  .actions {
    width: 100%;
  }
  .row-detail {
    padding-left: 16px;
  }
}
</style>
