<script setup>
import IconCheck from './icons/IconCheck.vue'
import IconAlert from './icons/IconAlert.vue'
import IconX from './icons/IconX.vue'

defineProps({
  toast: { type: Object, required: true },
})
defineEmits(['dismiss'])

const styles = {
  success: { border: 'border-success-500/30', bg: 'bg-success-500/10', icon: 'text-success-600 dark:text-success-400' },
  error: { border: 'border-danger-500/30', bg: 'bg-danger-500/10', icon: 'text-danger-600 dark:text-danger-400' },
  warning: { border: 'border-warning-500/30', bg: 'bg-warning-500/10', icon: 'text-warning-600 dark:text-warning-400' },
  info: { border: 'border-info-500/30', bg: 'bg-info-500/10', icon: 'text-info-600 dark:text-info-400' },
}
</script>

<template>
  <div
    class="glass-panel flex items-start gap-2.5 pl-3 pr-2 py-2.5 min-w-[280px] max-w-sm border"
    :class="[(styles[toast.level] || styles.info).border, (styles[toast.level] || styles.info).bg]"
  >
    <IconCheck v-if="toast.level === 'success'" :size="16" class="mt-0.5 shrink-0" :class="styles.success.icon" />
    <IconAlert v-else :size="16" class="mt-0.5 shrink-0" :class="(styles[toast.level] || styles.info).icon" />
    <p class="text-[12.5px] text-neutral-700 dark:text-neutral-200 leading-snug flex-1">{{ toast.message }}</p>
    <button class="btn-icon w-5 h-5 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 shrink-0" @click="$emit('dismiss', toast.id)">
      <IconX :size="13" />
    </button>
  </div>
</template>
