import { ref, watch } from 'vue'

const STORAGE_KEY = 'silakes-bridge-theme'

// Default LIGHT (bukan ikut preferensi OS) -- diminta eksplisit.
const isDark = ref(document.documentElement.classList.contains('dark'))

function applyTheme(dark) {
  document.documentElement.classList.toggle('dark', dark)
  try {
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
  } catch {
    /* localStorage tidak tersedia (mis. private mode) -- abaikan, tema tetap jalan per-sesi */
  }
}

watch(isDark, (v) => applyTheme(v))

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value
  }
  function setDark(v) {
    isDark.value = v
  }
  return { isDark, toggle, setDark }
}
