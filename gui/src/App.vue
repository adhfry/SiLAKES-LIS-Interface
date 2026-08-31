<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SplashScreen from './components/SplashScreen.vue'
import AppHeader from './components/AppHeader.vue'
import ControlPanel from './components/ControlPanel.vue'
import StatsGrid from './components/StatsGrid.vue'
import LogPanel from './components/LogPanel.vue'
import SettingsModal from './components/SettingsModal.vue'
import SendSampleModal from './components/SendSampleModal.vue'
import ToastContainer from './components/ToastContainer.vue'
import { useBridgeStore } from './composables/useBridgeStore'

const booted = ref(false)
const settingsOpen = ref(false)
const sendSampleOpen = ref(false)

const store = useBridgeStore()

let statusPoll = null

onMounted(() => {
  // Pemuatan awal (settings/status/tes koneksi) sudah dikerjakan SplashScreen
  // sbg step sequence -- di sini cuma pasang fallback polling (selain event
  // push real-time dari Python) supaya stats tetap sinkron walau 1-2 event
  // terlewat.
  statusPoll = setInterval(() => store.refreshStatus(), 4000)
})
onUnmounted(() => clearInterval(statusPoll))

function toggleBridge() {
  if (store.state.running) {
    store.stop()
  } else {
    store.start()
  }
}

async function handleSaveSettings(s) {
  // Lempar ulang error-nya (jangan ditelan) -- SettingsModal butuh throw ini
  // supaya tahu simpan gagal dan modal tidak ikut tertutup.
  await store.saveSettings(s)
}
</script>

<template>
  <SplashScreen v-if="!booted" @complete="booted = true" />

  <Transition name="fade-slide" appear>
    <div v-if="booted" class="h-screen w-screen flex flex-col overflow-hidden">
      <AppHeader
        :running="store.state.running"
        :starting="store.state.starting"
        @open-settings="settingsOpen = true"
      />

      <main class="flex-1 min-h-0 flex flex-col gap-4 p-5">
        <ControlPanel
          :running="store.state.running"
          :starting="store.state.starting"
          :stopping="store.state.stopping"
          :settings="store.state.settings"
          :started-at="store.state.stats.started_at"
          @toggle="toggleBridge"
          @send-sample="sendSampleOpen = true"
        />

        <StatsGrid :stats="store.state.stats" />

        <LogPanel :logs="store.state.logs" @clear="store.clearLogs" />
      </main>

      <footer class="px-5 py-2 text-center text-[11px] text-neutral-400 dark:text-neutral-500 border-t border-accent-900/[0.06] dark:border-white/[0.06] shrink-0">
        UPTD Labkesda Sumenep &middot; SiLAKES LIS Interface Bridge
      </footer>
    </div>
  </Transition>

  <SettingsModal
    v-model="settingsOpen"
    :settings="store.state.settings"
    :disabled="store.state.running"
    :on-save="handleSaveSettings"
  />

  <SendSampleModal v-model="sendSampleOpen" />

  <ToastContainer :toasts="store.state.toasts" @dismiss="store.dismissToast" />
</template>
