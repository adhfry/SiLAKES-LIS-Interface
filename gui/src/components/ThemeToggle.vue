<script setup>
import { useTheme } from '../composables/useTheme'

const { isDark, toggle } = useTheme()
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="isDark"
    title="Ganti tema terang/gelap"
    class="relative inline-flex items-center w-14 h-7 rounded-full shrink-0 transition-colors duration-500 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/60"
    :class="isDark ? 'bg-neutral-700' : 'bg-primary-100'"
    @click="toggle"
  >
    <!-- bintang kecil dekoratif, muncul cuma di mode gelap -->
    <span
      class="absolute left-2 top-1.5 w-[3px] h-[3px] rounded-full bg-white transition-opacity duration-300"
      :class="isDark ? 'opacity-70' : 'opacity-0'"
    />
    <span
      class="absolute left-4 top-3.5 w-[2px] h-[2px] rounded-full bg-white transition-opacity duration-500 delay-100"
      :class="isDark ? 'opacity-50' : 'opacity-0'"
    />

    <!-- knob -->
    <span
      class="relative z-10 flex items-center justify-center w-6 h-6 rounded-full bg-white shadow-md transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      :class="isDark ? 'translate-x-7' : 'translate-x-0.5'"
    >
      <Transition name="icon-morph" mode="out-in">
        <!-- MOON -->
        <svg
          v-if="isDark"
          key="moon"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="currentColor"
          class="text-accent-700"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
        </svg>
        <!-- SUN -->
        <svg
          v-else
          key="sun"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          class="text-warning-500"
        >
          <circle cx="12" cy="12" r="4.5" fill="currentColor" stroke="none" />
          <line x1="12" y1="1.5" x2="12" y2="3.5" />
          <line x1="12" y1="20.5" x2="12" y2="22.5" />
          <line x1="4.2" y1="4.2" x2="5.6" y2="5.6" />
          <line x1="18.4" y1="18.4" x2="19.8" y2="19.8" />
          <line x1="1.5" y1="12" x2="3.5" y2="12" />
          <line x1="20.5" y1="12" x2="22.5" y2="12" />
          <line x1="4.2" y1="19.8" x2="5.6" y2="18.4" />
          <line x1="18.4" y1="5.6" x2="19.8" y2="4.2" />
        </svg>
      </Transition>
    </span>
  </button>
</template>

<style scoped>
.icon-morph-enter-active,
.icon-morph-leave-active {
  transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
}
.icon-morph-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.4);
}
.icon-morph-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.4);
}
</style>
