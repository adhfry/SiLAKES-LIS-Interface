<script setup>
defineProps({
  entry: { type: Object, required: true },
})

const levelStyle = {
  info: { dot: 'bg-info-500', text: 'text-neutral-700 dark:text-neutral-200' },
  debug: { dot: 'bg-neutral-400', text: 'text-neutral-500 dark:text-neutral-400' },
  warning: { dot: 'bg-warning-500', text: 'text-warning-700 dark:text-warning-300' },
  error: { dot: 'bg-danger-500', text: 'text-danger-600 dark:text-danger-300' },
  success: { dot: 'bg-success-500', text: 'text-success-700 dark:text-success-300' },
}

function timeLabel(ts) {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('id-ID', { hour12: false })
  } catch {
    return ''
  }
}
</script>

<template>
  <div class="group flex items-start gap-2.5 px-3 py-1 rounded hover:bg-accent-900/[0.03] dark:hover:bg-white/[0.03] font-mono text-[12.5px] leading-relaxed">
    <span class="shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full" :class="(levelStyle[entry.level] || levelStyle.info).dot" />
    <span class="shrink-0 text-neutral-400 dark:text-neutral-500 tabular-nums w-[74px]">{{ timeLabel(entry.ts) }}</span>
    <span class="whitespace-pre-wrap break-all selectable" :class="(levelStyle[entry.level] || levelStyle.info).text">{{
      entry.message
    }}</span>
  </div>
</template>
