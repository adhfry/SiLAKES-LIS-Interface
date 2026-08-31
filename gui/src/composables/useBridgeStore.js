import { reactive, readonly } from 'vue'
import { usePywebviewApi } from './usePywebviewApi'

const MAX_LOG_LINES = 3000
let _seq = 0

const state = reactive({
  running: false,
  starting: false,
  stopping: false,
  stats: {
    running: false,
    started_at: null,
    connections_total: 0,
    queries_answered: 0,
    results_sent_ok: 0,
    results_sent_error: 0,
    last_error: null,
    last_activity: null,
  },
  settings: null,
  settingsLoaded: false,
  logs: [], // { id, ts, level, message }
  toasts: [], // { id, level, message }
})

const api = usePywebviewApi()

function pushLog(level, message, ts) {
  state.logs.push({
    id: ++_seq,
    ts: ts || new Date().toISOString(),
    level: (level || 'info').toLowerCase(),
    message,
  })
  if (state.logs.length > MAX_LOG_LINES) {
    state.logs.splice(0, state.logs.length - MAX_LOG_LINES)
  }
}

function pushToast(level, message) {
  const id = ++_seq
  state.toasts.push({ id, level, message })
  setTimeout(() => {
    const idx = state.toasts.findIndex((t) => t.id === id)
    if (idx !== -1) state.toasts.splice(idx, 1)
  }, 6000)
}

function dismissToast(id) {
  const idx = state.toasts.findIndex((t) => t.id === id)
  if (idx !== -1) state.toasts.splice(idx, 1)
}

function applyStats(stats) {
  if (!stats) return
  Object.assign(state.stats, stats)
  state.running = !!stats.running
}

// ---- jembatan event real-time dari Python (dipanggil via evaluate_js) ----
function installWindowBridge() {
  window.__bridgeOnLog = (level, message, ts) => {
    pushLog(level, message, ts)
    if (level === 'error') pushToast('error', message)
  }
  window.__bridgeOnStats = (stats) => {
    applyStats(stats)
  }
}

async function loadSettings() {
  const s = await api.getSettings()
  state.settings = s
  state.settingsLoaded = true
  return s
}

async function saveSettings(partial) {
  try {
    const s = await api.saveSettings(partial)
    state.settings = s
    pushToast('success', 'Pengaturan disimpan.')
    return s
  } catch (e) {
    pushToast('error', `Gagal menyimpan pengaturan: ${e}`)
    pushLog('error', `Gagal menyimpan pengaturan: ${e}`)
    throw e
  }
}

async function refreshStatus() {
  const status = await api.getStatus()
  applyStats(status.stats || status)
}

async function checkSilakesConnection() {
  return api.pingSilakes()
}

async function start() {
  if (state.running || state.starting) return
  state.starting = true
  pushLog('info', 'Memulai bridge...')
  try {
    const res = await api.startBridge()
    applyStats(res.stats || res)
    pushToast('success', 'Bridge aktif dan siap menerima koneksi MC-200.')
  } catch (e) {
    pushToast('error', `Gagal memulai bridge: ${e}`)
    pushLog('error', `Gagal memulai bridge: ${e}`)
  } finally {
    state.starting = false
  }
}

async function stop() {
  if (!state.running || state.stopping) return
  state.stopping = true
  pushLog('info', 'Menghentikan bridge...')
  try {
    const res = await api.stopBridge()
    applyStats(res.stats || res)
    pushToast('info', 'Bridge dihentikan.')
  } catch (e) {
    pushToast('error', `Gagal menghentikan bridge: ${e}`)
  } finally {
    state.stopping = false
  }
}

function clearLogs() {
  state.logs.splice(0, state.logs.length)
}

let _knownTestsCache = null
async function getKnownTests() {
  if (_knownTestsCache) return _knownTestsCache
  const res = await api.knownTests()
  _knownTestsCache = res?.tests || []
  return _knownTestsCache
}

async function sendSample(payload) {
  try {
    const res = await api.sendSample(payload)
    pushLog('info', `Sampel manual dikirim ke cache: ${res.accession} (${(res.tests || []).join(', ')})`)
    pushToast('success', `Sampel ${res.accession} siap dijawab saat MC-200 query.`)
    return res
  } catch (e) {
    pushToast('error', `Gagal kirim sampel: ${e}`)
    throw e
  }
}

installWindowBridge()

export function useBridgeStore() {
  return {
    state: readonly(state),
    start,
    stop,
    loadSettings,
    saveSettings,
    refreshStatus,
    checkSilakesConnection,
    clearLogs,
    pushToast,
    dismissToast,
    getKnownTests,
    sendSample,
    isPywebview: api.isPywebview,
    waitReady: api.waitReady,
    openDataFolder: api.openDataFolder,
  }
}
