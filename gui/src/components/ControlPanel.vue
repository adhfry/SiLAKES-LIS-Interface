<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import IconPlay from './icons/IconPlay.vue'
import IconStop from './icons/IconStop.vue'
import IconAlert from './icons/IconAlert.vue'
import IconSend from './icons/IconSend.vue'

const props = defineProps({
  running: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  stopping: { type: Boolean, default: false },
  settings: { type: Object, default: null },
  startedAt: { type: String, default: null },
})
const emit = defineEmits(['toggle', 'send-sample'])

const now = ref(Date.now())
let tick = null
onMounted(() => {
  tick = setInterval(() => (now.value = Date.now()), 1000)
})
onUnmounted(() => clearInterval(tick))

const uptime = computed(() => {
  if (!props.startedAt) return '—'
  const diff = Math.max(0, now.value - new Date(props.startedAt).getTime())
  const s = Math.floor(diff / 1000)
  const hh = String(Math.floor(s / 3600)).padStart(2, '0')
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})
</script>

<template>
  <div class="glass-panel relative overflow-hidden p-6">
    <!-- glow ambient di belakang tombol saat aktif -->
    <div
      class="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-72 rounded-full bg-primary-400/25 blur-3xl transition-opacity duration-700"
      :class="running ? 'opacity-100' : 'opacity-0'"
    />

    <div class="relative flex items-center gap-6">
      <!-- tombol besar -->
      <button
        class="group relative shrink-0 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
        :class="
          running
            ? 'bg-gradient-to-br from-danger-500 to-danger-600 shadow-[0_0_0_6px_rgba(239,68,68,0.12)]'
            : 'bg-brand-gradient shadow-[0_0_0_6px_rgba(0,165,154,0.16)]'
        "
        :disabled="starting || stopping"
        @click="emit('toggle')"
      >
        <span
          v-if="running"
          class="absolute inset-0 rounded-full border-2 border-danger-400/40 animate-ping"
        />
        <Transition name="fade-slide" mode="out-in">
          <svg v-if="starting || stopping" key="loading" class="animate-spin-slow" width="30" height="30" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="42 100" />
          </svg>
          <IconStop v-else-if="running" key="stop" :size="30" class="text-white drop-shadow" />
          <IconPlay v-else key="play" :size="30" class="text-white translate-x-0.5 drop-shadow" />
        </Transition>
      </button>

      <!-- info -->
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-heading font-bold text-neutral-900 dark:text-neutral-100">
              {{ running ? 'Bridge sedang berjalan' : starting ? 'Memulai bridge…' : 'Bridge tidak aktif' }}
            </h2>
            <p class="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
              {{
                running
                  ? 'Menunggu koneksi ASTM dari MC-200 & memantau worklist pending.'
                  : 'Klik tombol untuk mengaktifkan sistem sebagai perantara MC-200 ⇄ SiLAKES.'
              }}
            </p>
          </div>
          <button
            v-if="running"
            class="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px] font-semibold bg-brand-gradient text-white shadow-glow"
            title="Kirim sampel ad-hoc langsung ke MC-200 (tanpa worklist SiLAKES)"
            @click="emit('send-sample')"
          >
            <IconSend :size="13" />
            Kirim Sampel
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-x-5 gap-y-1.5 mt-3 text-[12px] text-neutral-500 dark:text-neutral-400 font-mono">
          <span class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-primary-500" />
            Listen: {{ settings?.listen_host || '0.0.0.0' }}:{{ settings?.listen_port ?? 123 }}
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-accent-600" />
            Device: {{ settings?.device_code || '—' }}
          </span>
          <span v-if="running" class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-success-500" />
            Uptime: {{ uptime }}
          </span>
        </div>

        <div
          v-if="(settings?.listen_host || '0.0.0.0') === '0.0.0.0'"
          class="flex items-start gap-2 mt-3 px-3 py-2 rounded-lg bg-warning-500/10 border border-warning-500/25 text-[12px] text-warning-700 dark:text-warning-300"
        >
          <IconAlert :size="14" class="shrink-0 mt-0.5" />
          <span>
            <strong>0.0.0.0</strong> berarti bridge mendengarkan di semua network interface PC ini.
            Untuk memastikan MC-200 bisa menghubungi bridge, arahkan IP di pengaturan SAGES200
            (Server IP) ke <strong>IP LAN PC yang menjalankan bridge ini</strong> —
            atau ubah "Listen Host" di Pengaturan ke IP LAN spesifik PC yang menangani MC-200
            kalau bridge ini dijalankan di PC yang sama.
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
