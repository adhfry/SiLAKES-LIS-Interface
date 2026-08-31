<script setup>
/**
 * Input IP versi "4 kotak + titik tetap" (mis. panel admin router/printer).
 * Titik pemisah dicetak permanen di antara kotak, tidak bisa dihapus user --
 * user cukup ketik angka tiap oktet, otomatis pindah ke kotak berikutnya
 * (saat 3 digit terisi, atau saat tekan "." / Enter / spasi).
 * v-model tetap berupa string IP biasa, mis. "192.168.1.44".
 */
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '0.0.0.0' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

function parseIp(ip) {
  const parts = String(ip || '')
    .split('.')
    .map((p) => p.replace(/\D/g, '').slice(0, 3))
  while (parts.length < 4) parts.push('')
  return parts.slice(0, 4)
}

const octets = ref(parseIp(props.modelValue))
const inputs = ref([])

watch(
  () => props.modelValue,
  (val) => {
    const parsed = parseIp(val)
    const current = octets.value.join('.')
    if (parsed.join('.') !== current) octets.value = parsed
  }
)

function emitValue() {
  const clamped = octets.value.map((o) => (o === '' ? '0' : String(Math.min(255, parseInt(o, 10) || 0))))
  emit('update:modelValue', clamped.join('.'))
}

function focusOctet(i) {
  nextTick(() => {
    const el = inputs.value[i]
    if (el) {
      el.focus()
      el.select()
    }
  })
}

function onInput(i, e) {
  let digits = e.target.value.replace(/\D/g, '').slice(0, 3)
  if (digits !== '') {
    const n = Math.min(255, parseInt(digits, 10))
    digits = String(n)
    if (parseInt(digits, 10) !== n) digits = String(n)
  }
  octets.value[i] = digits
  e.target.value = digits
  emitValue()

  // auto-advance: 3 digit penuh, atau 2 digit tapi nilai udah pasti >=26 (mis "99" gapapa lanjut manual),
  // paling gampang & konsisten: pindah begitu genap 3 digit.
  if (digits.length === 3 && i < 3) {
    focusOctet(i + 1)
  }
}

function onKeydown(i, e) {
  if (['.', ' ', 'Enter', 'ArrowRight'].includes(e.key)) {
    e.preventDefault()
    if (i < 3) focusOctet(i + 1)
    return
  }
  if (e.key === 'ArrowLeft' && e.target.selectionStart === 0 && i > 0) {
    e.preventDefault()
    focusOctet(i - 1)
    return
  }
  if (e.key === 'Backspace' && e.target.value === '' && i > 0) {
    e.preventDefault()
    focusOctet(i - 1)
  }
}

function onPaste(i, e) {
  const text = (e.clipboardData || window.clipboardData).getData('text')
  if (text.includes('.')) {
    e.preventDefault()
    octets.value = parseIp(text)
    emitValue()
    focusOctet(3)
  }
}

const displayValue = computed(() => octets.value.join('.'))
</script>

<template>
  <div
    class="flex items-center gap-0 bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-2 focus-within:ring-1 focus-within:ring-primary-500/50 focus-within:border-primary-500/50"
    :class="disabled && 'opacity-50 pointer-events-none'"
    :title="displayValue"
  >
    <template v-for="(octet, i) in octets" :key="i">
      <input
        :ref="(el) => (inputs[i] = el)"
        :value="octet"
        type="text"
        inputmode="numeric"
        maxlength="3"
        class="selectable w-9 bg-transparent text-center py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none"
        :disabled="disabled"
        @input="onInput(i, $event)"
        @keydown="onKeydown(i, $event)"
        @paste="onPaste(i, $event)"
        @focus="$event.target.select()"
      />
      <span v-if="i < 3" class="text-neutral-400 dark:text-neutral-500 select-none font-mono">.</span>
    </template>
  </div>
</template>
