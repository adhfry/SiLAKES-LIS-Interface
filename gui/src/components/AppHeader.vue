<script setup>
import IconSettings from './icons/IconSettings.vue'
import ThemeToggle from './ThemeToggle.vue'

defineProps({
  running: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
})
defineEmits(['open-settings'])
</script>

<template>
  <header class="flex items-center justify-between px-6 py-4 border-b border-accent-900/[0.06] dark:border-white/[0.06] shrink-0">
    <div class="flex items-center gap-3">
      <svg class="w-8 h-8" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="hdrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#2bd3c8" />
            <stop offset="100%" stop-color="#00857d" />
          </linearGradient>
        </defs>
        <path
          d="M60 8 C60 8 22 52 22 78 A38 38 0 0 0 98 78 C98 52 60 8 60 8 Z"
          fill="url(#hdrGrad)"
          opacity="0.15"
        />
        <path
          d="M60 8 C60 8 22 52 22 78 A38 38 0 0 0 98 78 C98 52 60 8 60 8 Z"
          fill="none"
          stroke="url(#hdrGrad)"
          stroke-width="3"
        />
        <circle cx="42" cy="72" r="8" fill="#2bd3c8" />
        <circle cx="78" cy="72" r="8" fill="#00857d" />
        <line x1="49" y1="72" x2="71" y2="72" stroke="url(#hdrGrad)" stroke-width="4" stroke-linecap="round" />
        <circle cx="60" cy="72" r="4" fill="#ffffff" />
      </svg>
      <div class="leading-tight">
        <h1 class="text-[15px] font-heading font-bold text-neutral-900 dark:text-neutral-100 tracking-tight">
          SiLAKES <span class="font-normal text-neutral-500 dark:text-neutral-400">LIS Interface</span>
        </h1>
        <p class="text-[11px] text-neutral-400 dark:text-neutral-500">Bridge MC-200 ⇄ SiLAKES API</p>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <div
        class="flex items-center gap-2 px-3 py-1.5 rounded-full text-[12px] font-medium border transition-colors duration-300"
        :class="
          running
            ? 'bg-success-500/10 border-success-500/30 text-success-600 dark:text-success-400'
            : starting
              ? 'bg-warning-500/10 border-warning-500/30 text-warning-600 dark:text-warning-400'
              : 'bg-neutral-500/5 border-neutral-500/20 text-neutral-500 dark:text-neutral-400'
        "
      >
        <span class="relative flex h-2 w-2">
          <span
            v-if="running || starting"
            class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            :class="running ? 'bg-success-500' : 'bg-warning-500'"
          />
          <span
            class="relative inline-flex rounded-full h-2 w-2"
            :class="running ? 'bg-success-500' : starting ? 'bg-warning-500' : 'bg-neutral-400'"
          />
        </span>
        {{ running ? 'Aktif' : starting ? 'Memulai…' : 'Berhenti' }}
      </div>

      <ThemeToggle />

      <button
        class="btn-icon w-9 h-9 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-500/10 active:scale-95"
        title="Pengaturan"
        @click="$emit('open-settings')"
      >
        <IconSettings :size="18" />
      </button>
    </div>
  </header>
</template>
