<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  accent: { type: String, default: 'primary' }, // primary | accent | success | danger
})

const accentMap = {
  primary: 'text-primary-600 dark:text-primary-400',
  accent: 'text-accent-700 dark:text-accent-300',
  success: 'text-success-600 dark:text-success-400',
  warning: 'text-warning-600 dark:text-warning-400',
  danger: 'text-danger-600 dark:text-danger-400',
}
</script>

<template>
  <div class="glass-panel px-4 py-3.5 flex flex-col gap-1 hover:border-accent-900/[0.12] dark:hover:border-white/[0.12] transition-colors duration-200">
    <span class="text-[11px] uppercase tracking-wider text-neutral-500 dark:text-neutral-400 font-medium">{{ label }}</span>
    <Transition name="fade-slide" mode="out-in">
      <span :key="value" class="text-2xl font-heading font-bold tabular-nums" :class="accentMap[accent] || accentMap.primary">
        {{ value }}
      </span>
    </Transition>
  </div>
</template>
