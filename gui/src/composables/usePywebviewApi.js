/**
 * Klien HTTP ke API lokal Python (127.0.0.1:8765, lihat gui_app.py).
 *
 * Sengaja TIDAK pakai window.pywebview.api lagi -- mekanisme js_api bawaan
 * pywebview terbukti tidak andal di kombinasi pywebview+WebView2+Windows ini
 * (gagal "belum siap" berulang kali, baik di exe PyInstaller maupun
 * `python gui_app.py` langsung). fetch() ke server lokal jauh lebih stabil.
 *
 * Punya fallback "dev mock" saat server lokal ini benar-benar tidak terjangkau
 * (mis. develop UI murni di browser tanpa gui_app.py jalan sama sekali).
 */
const API_BASE = 'http://127.0.0.1:8765/api'
const FETCH_TIMEOUT_MS = 8000

const mockSettings = {
  listen_host: '0.0.0.0',
  listen_port: 123,
  silakes_base_url: 'https://api.silakes.labkesdasumenep.id/api',
  lis_secret_key: 'kesehatanNo120112025BLUDLabkesmas2025',
  device_code: 'MC200',
  poll_interval_seconds: 3.5,
  http_timeout_seconds: 10,
  socket_timeout_seconds: 60,
}

const _mock = { running: false, startedAt: null }

function mockStats() {
  return {
    running: _mock.running,
    started_at: _mock.startedAt,
    connections_total: _mock.running ? 12 : 0,
    queries_answered: _mock.running ? 3 : 0,
    results_sent_ok: _mock.running ? 8 : 0,
    results_sent_error: _mock.running ? 1 : 0,
    last_error: null,
    last_activity: _mock.running ? new Date().toISOString() : null,
  }
}

async function mockCall(method, ...args) {
  console.debug(`[dev-mock] ${method}(`, ...args, ')')
  switch (method) {
    case 'start_bridge':
      _mock.running = true
      _mock.startedAt = new Date().toISOString()
      return { running: true, stats: mockStats() }
    case 'stop_bridge':
      _mock.running = false
      _mock.startedAt = null
      return { running: false, stats: mockStats() }
    case 'get_status':
      return { running: _mock.running, stats: mockStats() }
    case 'get_settings':
      return { ...mockSettings }
    case 'save_settings':
      return { ...mockSettings, ...args[0] }
    case 'open_data_folder':
      return true
    case 'ping_silakes':
      return { ok: true, message: 'Terhubung ke SiLAKES API (dev-mock).' }
    case 'known_tests':
      return { tests: ['ALB', 'UA', 'TG', 'T-CHOL', 'AST', 'ALT', 'CREA', 'UREA', 'HDL-C', 'LDL-C', 'TBIL', 'DBIL', 'GLU'] }
    case 'send_sample':
      return { accession: args[0]?.sample_id || args[0]?.patient_id, tests: args[0]?.tests || [] }
    default:
      return null
  }
}

let _serverUnreachable = false

async function httpCall(path, { method = 'GET', body } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
    _serverUnreachable = false
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(data?.error || `HTTP ${res.status}`)
    }
    return data
  } catch (e) {
    if (e.name === 'AbortError') {
      throw new Error(`Timeout menghubungi API lokal (${path}).`)
    }
    // fetch gagal total (server belum jalan) -- tandai supaya caller bisa fallback ke mock kalau perlu
    _serverUnreachable = true
    throw e
  } finally {
    clearTimeout(timer)
  }
}

export function usePywebviewApi() {
  async function call(method, ...args) {
    try {
      switch (method) {
        case 'start_bridge':
          return await httpCall('/start', { method: 'POST' })
        case 'stop_bridge':
          return await httpCall('/stop', { method: 'POST' })
        case 'get_status':
          return await httpCall('/status')
        case 'get_settings':
          return await httpCall('/settings')
        case 'save_settings':
          return await httpCall('/settings', { method: 'POST', body: args[0] })
        case 'open_data_folder':
          return await httpCall('/open_data_folder', { method: 'POST' })
        case 'ping_silakes':
          return await httpCall('/ping_silakes')
        case 'known_tests':
          return await httpCall('/known_tests')
        case 'send_sample':
          return await httpCall('/send_sample', { method: 'POST', body: args[0] })
        default:
          return null
      }
    } catch (e) {
      // Hanya fallback ke mock kalau server API lokal memang tidak terjangkau
      // sama sekali (dev di browser biasa) -- error API asli (mis. 500) tetap dilempar apa adanya.
      if (_serverUnreachable) {
        return mockCall(method, ...args)
      }
      throw e
    }
  }

  return {
    isPywebview: true, // dipertahankan demi kompatibilitas nama; sekarang berarti "ada backend Python via HTTP"
    waitReady: () => Promise.resolve(true), // tidak perlu tunggu apa pun lagi -- HTTP server siap sejak awal proses Python
    startBridge: () => call('start_bridge'),
    stopBridge: () => call('stop_bridge'),
    getStatus: () => call('get_status'),
    getSettings: () => call('get_settings'),
    saveSettings: (s) => call('save_settings', s),
    openDataFolder: () => call('open_data_folder'),
    pingSilakes: () => call('ping_silakes'),
    knownTests: () => call('known_tests'),
    sendSample: (payload) => call('send_sample', payload),
  }
}
