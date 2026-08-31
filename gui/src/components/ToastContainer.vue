<script setup>
import ToastItem from './ToastItem.vue'

defineProps({
  toasts: { type: Array, required: true },
})
const emit = defineEmits(['dismiss'])
</script>

<template>
  <div class="fixed top-5 right-5 z-50 flex flex-col gap-2 items-end pointer-events-none">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" class="pointer-events-auto">
        <ToastItem :toast="t" @dismiss="emit('dismiss', $event)" />
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast-leave-active {
  transition: all 0.25s ease;
  position: absolute;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
.toast-move {
  transition: transform 0.25s ease;
}
</style>
