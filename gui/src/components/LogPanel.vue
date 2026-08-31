<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import LogLine from './LogLine.vue'
import IconTerminal from './icons/IconTerminal.vue'
import IconTrash from './icons/IconTrash.vue'
import IconDownload from './icons/IconDownload.vue'

const props = defineProps({
  logs: { type: Array, required: true },
})
const emit = defineEmits(['clear'])

const filterLevel = ref('all')
const search = ref('')
const autoScroll = ref(true)
const scrollEl = ref(null)

const levels = [
  { key: 'all', label: 'Semua' },
  { key: 'info', label: 'Info' },
  { key: 'success', label: 'Sukses' },
  { key: 'warning', label: 'Peringatan' },
  { key: 'error', label: 'Error' },
]

const filtered = computed(() => {
  let list = props.logs
  if (filterLevel.value !== 'all') {
    list = list.filter((l) => l.level === filterLevel.value)
  }
  if (search.value.trim()) {
    const q = search.value.trim().toLowerCase()
    list = list.filter((l) => l.message.toLowerCase().includes(q))
  }
  // render maksimal 600 baris terakhir supaya DOM tetap ringan
  return list.length > 600 ? list.slice(-600) : list
})

const errorCount = computed(() => props.logs.filter((l) => l.level === 'error').length)

function scrollToBottom() {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

function jumpToBottom() {
  autoScroll.value = true
  scrollToBottom()
}

function handleScroll() {
  if (!scrollEl.value) return
  const el = scrollEl.value
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  autoScroll.value = nearBottom
}

watch(
  () => props.logs.length,
  () => {
    if (autoScroll.value) scrollToBottom()
  }
)

onMounted(scrollToBottom)

function exportLogs() {
  const text = props.logs.map((l) => `[${l.ts}] [${l.level.toUpperCase()}] ${l.message}`).join('\n')
  const blob = new Blob([text], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `bridge-log-${new Date().toISOString().replace(/[:.]/g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="glass-panel relative flex flex-col min-h-0 flex-1">
    <div class="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-accent-900/[0.06] dark:border-white/[0.06] shrink-0">
      <IconTerminal :size="16" class="text-neutral-400" />
      <h3 class="text-sm font-heading font-semibold text-neutral-900 dark:text-neutral-100 mr-1">Log Real-time</h3>

      <div class="flex items-center gap-1 ml-1">
        <button
          v-for="lv in levels"
          :key="lv.key"
          class="px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors duration-150"
          :class="
            filterLevel === lv.key
              ? 'bg-primary-500/15 text-primary-700 dark:text-primary-400 border border-primary-500/30'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200 hover:bg-accent-900/5 dark:hover:bg-white/5 border border-transparent'
          "
          @click="filterLevel = lv.key"
        >
          {{ lv.label }}
          <span v-if="lv.key === 'error' && errorCount > 0" class="ml-1 text-danger-500">({{ errorCount }})</span>
        </button>
      </div>

      <input
        v-model="search"
        type="text"
        placeholder="Cari log…"
        class="selectable ml-auto w-40 md:w-56 bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-md px-2.5 py-1 text-[12px] text-neutral-800 dark:text-neutral-200 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50"
      />

      <button
        class="btn-icon w-7 h-7 text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-100 hover:bg-accent-900/5 dark:hover:bg-white/5"
        title="Export log ke file .txt"
        @click="exportLogs"
      >
        <IconDownload :size="15" />
      </button>
      <button
        class="btn-icon w-7 h-7 text-neutral-400 hover:text-danger-500 hover:bg-danger-500/10"
        title="Bersihkan log"
        @click="emit('clear')"
      >
        <IconTrash :size="15" />
      </button>
    </div>

    <div ref="scrollEl" class="flex-1 min-h-0 overflow-y-auto py-2 relative" @scroll="handleScroll">
      <div v-if="filtered.length === 0" class="flex flex-col items-center justify-center h-full text-neutral-400 dark:text-neutral-500 text-sm gap-2 py-16">
        <IconTerminal :size="28" class="opacity-40" />
        <p>Belum ada aktivitas. Klik "Start" untuk mulai memantau.</p>
      </div>
      <TransitionGroup v-else name="log-line" tag="div">
        <LogLine v-for="entry in filtered" :key="entry.id" :entry="entry" />
      </TransitionGroup>
    </div>

    <Transition name="fade-slide">
      <button
        v-if="!autoScroll"
        class="absolute bottom-24 right-8 px-3 py-1.5 rounded-full bg-primary-600 text-white text-[12px] font-medium shadow-glow"
        @click="jumpToBottom"
      >
        ↓ Log baru
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.log-line-enter-active {
  transition: all 0.25s ease;
}
.log-line-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
