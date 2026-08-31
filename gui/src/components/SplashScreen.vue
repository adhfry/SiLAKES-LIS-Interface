<script setup>
/**
 * Splash/boot screen SiLAKES LIS Interface.
 *
 * BUKAN timer palsu -- tiap baris di sini terikat ke pekerjaan ASLI yang
 * memang harus selesai sebelum dashboard boleh tampil (pywebviewready,
 * load settings, load status bridge, tes konektivitas SiLAKES API).
 * "Not responding" di awal (freeze WebView2/CLR sebelum satu baris JS pun
 * jalan) TIDAK bisa dihilangkan splash ini -- itu terjadi SEBELUM window
 * bisa render apa pun. Yang bisa & memang perlu dibenerin: jangan pura-pura
 * "siap" pakai setTimeout padahal belum tentu API/koneksi beneran oke.
 */
import { ref, onMounted } from 'vue'
import { useBridgeStore } from '../composables/useBridgeStore'

const emit = defineEmits(['complete'])
const store = useBridgeStore()

const progress = ref(0)
const currentLabel = ref('Memulai...')
const logLines = ref([]) // { text, ok }
const failedStep = ref(null) // { label, message } | null

function log(text, ok = true) {
  logLines.value.push({ text, ok })
  if (logLines.value.length > 6) logLines.value.shift()
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

const STEPS = [
  {
    pct: 15,
    label: 'Menyiapkan jendela aplikasi...',
    run: async () => {
      await store.waitReady()
      log('Jendela aplikasi siap')
    },
  },
  {
    pct: 40,
    label: 'Memuat pengaturan tersimpan...',
    run: async () => {
      const s = await store.loadSettings()
      log(`Pengaturan dimuat (port ${s?.listen_port ?? '-'}, device ${s?.device_code ?? '-'})`)
    },
  },
  {
    pct: 65,
    label: 'Memeriksa status bridge...',
    run: async () => {
      await store.refreshStatus()
      log('Status bridge diperiksa')
    },
  },
  {
    pct: 90,
    label: 'Menguji koneksi ke SiLAKES API...',
    run: async () => {
      const res = await store.checkSilakesConnection()
      if (!res?.ok) {
        // Lempar supaya ditangkap sbg failedStep -- JANGAN diam-diam lanjut
        // ke dashboard kalau API memang tidak terjangkau.
        const err = new Error(res?.message || 'Tidak bisa menghubungi SiLAKES API.')
        err.isPingFailure = true
        throw err
      }
      log(res.message || 'Koneksi SiLAKES API OK')
    },
  },
]

async function runSequence() {
  failedStep.value = null
  for (const step of STEPS) {
    currentLabel.value = step.label
    try {
      await step.run()
      progress.value = step.pct
      await wait(150) // biar tiap step kelihatan, bukan lompat instan
    } catch (e) {
      log(e.message || String(e), false)
      failedStep.value = { label: step.label, message: e.message || String(e), skippable: !!e.isPingFailure }
      return
    }
  }

  progress.value = 100
  currentLabel.value = 'Siap.'
  await wait(350)
  emit('complete')
}

function retry() {
  runSequence()
}

function skipAndContinue() {
  log('Dilanjutkan tanpa konfirmasi koneksi API (periksa manual nanti).', false)
  progress.value = 100
  emit('complete')
}

onMounted(runSequence)
</script>

<template>
  <div class="splash">
    <svg class="splash-logo" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="splashGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#2bd3c8" />
          <stop offset="100%" stop-color="#00857d" />
        </linearGradient>
      </defs>

      <path class="droplet-fill" d="M60 8 C60 8 22 52 22 78 A38 38 0 0 0 98 78 C98 52 60 8 60 8 Z"
            fill="url(#splashGrad)" opacity="0.15" />
      <path class="droplet-stroke" d="M60 8 C60 8 22 52 22 78 A38 38 0 0 0 98 78 C98 52 60 8 60 8 Z"
            fill="none" stroke="url(#splashGrad)" stroke-width="2.5" pathLength="1" />

      <circle class="node node-device" cx="42" cy="72" r="7" fill="#2bd3c8" />
      <circle class="node node-silakes" cx="78" cy="72" r="7" fill="#00857d" />
      <line class="bridge-line" x1="49" y1="72" x2="71" y2="72"
            stroke="url(#splashGrad)" stroke-width="3" stroke-linecap="round" pathLength="1" />
      <circle class="pulse-dot" cx="60" cy="72" r="3.5" fill="#ffffff" />
    </svg>

    <div class="pulse-ring" />
    <div class="pulse-ring pulse-ring--delay" />

    <h1 class="splash-title">SiLAKES <span>LIS Interface</span></h1>

    <template v-if="!failedStep">
      <p class="splash-sub">{{ currentLabel }}</p>

      <div class="splash-progress">
        <div class="splash-progress-fill" :style="{ width: progress + '%' }" />
      </div>
      <p class="splash-pct">{{ progress }}%</p>

      <ul class="splash-log">
        <li v-for="(l, i) in logLines" :key="i" :class="l.ok ? 'ok' : 'fail'">
          <span class="mark">{{ l.ok ? '✓' : '⚠' }}</span> {{ l.text }}
        </li>
      </ul>
    </template>

    <template v-else>
      <p class="splash-error-label">{{ failedStep.label }}</p>
      <p class="splash-error-msg">⚠ {{ failedStep.message }}</p>
      <div class="splash-actions">
        <button class="btn-retry" @click="retry">Coba lagi</button>
        <button v-if="failedStep.skippable" class="btn-skip" @click="skipAndContinue">
          Lanjutkan tanpa koneksi
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: radial-gradient(circle at 50% 40%, #16213a 0%, #0f172a 60%, #0b1220 100%);
  z-index: 9999;
}

.splash-logo {
  width: 96px;
  height: 96px;
  opacity: 0;
  transform: scale(0.72);
  animation: logoIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s forwards;
  filter: drop-shadow(0 0 18px rgba(59, 130, 246, 0.35));
}

.droplet-stroke,
.bridge-line {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 0.9s ease .35s forwards;
}
.droplet-fill { opacity: 0; animation: fadeIn .6s ease 1.1s forwards; }

.node { opacity: 0; transform-origin: center; transform-box: fill-box; }
.node-device { animation: popIn .35s ease .9s forwards; }
.node-silakes { animation: popIn .35s ease 1.05s forwards; }

.pulse-dot {
  opacity: 0;
  animation: fadeIn .3s ease 1.3s forwards, pulseDot 1s ease 1.5s infinite;
}

.pulse-ring {
  position: absolute;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid #2bd3c8;
  opacity: 0;
  animation: pulseRing 1.4s ease-out 1.5s infinite;
}
.pulse-ring--delay { animation-delay: 2.1s; }

.splash-title {
  margin-top: 22px;
  opacity: 0;
  transform: translateY(12px);
  font: 700 24px/1.3 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
  color: #f8fafc;
  letter-spacing: 0.2px;
  animation: fadeUp 0.5s ease 1.15s forwards;
}
.splash-title span {
  font-weight: 400;
  color: #94a3b8;
  margin-left: 8px;
  font-size: 16px;
}

.splash-sub {
  min-height: 18px;
  margin-top: 18px;
  font: 400 13px 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
  color: #94a3b8;
  transition: opacity 0.15s ease;
}

.splash-progress {
  width: 220px;
  height: 4px;
  background: #1e293b;
  border-radius: 2px;
  margin-top: 10px;
  overflow: hidden;
}
.splash-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2bd3c8, #00857d);
  border-radius: 2px;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.splash-pct {
  margin-top: 6px;
  font: 500 11px 'JetBrains Mono', monospace;
  color: #64748b;
}

.splash-log {
  list-style: none;
  margin-top: 18px;
  padding: 0;
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font: 400 11.5px 'JetBrains Mono', monospace;
}
.splash-log li {
  opacity: 0;
  animation: fadeUp 0.3s ease forwards;
  display: flex;
  gap: 6px;
  color: #94a3b8;
}
.splash-log li.ok .mark { color: #2bd3c8; }
.splash-log li.fail { color: #fbbf24; }
.splash-log li.fail .mark { color: #fbbf24; }

.splash-error-label {
  margin-top: 20px;
  font: 600 14px 'Plus Jakarta Sans', sans-serif;
  color: #f8fafc;
}
.splash-error-msg {
  margin-top: 6px;
  max-width: 320px;
  text-align: center;
  font: 400 12.5px 'Plus Jakarta Sans', sans-serif;
  color: #fbbf24;
  line-height: 1.5;
}
.splash-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}
.btn-retry,
.btn-skip {
  padding: 8px 16px;
  border-radius: 8px;
  font: 600 12.5px 'Plus Jakarta Sans', sans-serif;
  cursor: pointer;
  border: none;
}
.btn-retry {
  background: linear-gradient(135deg, #2bd3c8, #00857d);
  color: white;
}
.btn-skip {
  background: transparent;
  border: 1px solid #334155;
  color: #94a3b8;
}
.btn-skip:hover { color: #f8fafc; border-color: #64748b; }

@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes fadeIn { to { opacity: 1; } }
@keyframes logoIn { to { opacity: 1; transform: scale(1); } }
@keyframes popIn { to { opacity: 1; transform: scale(1); } from { transform: scale(0); } }
@keyframes fadeUp { to { opacity: 1; transform: translateY(0); } from { opacity: 0; transform: translateY(6px); } }
@keyframes pulseDot { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.5); } }
@keyframes pulseRing {
  0% { opacity: 0.8; transform: scale(0.6); }
  100% { opacity: 0; transform: scale(2.6); }
}
</style>
