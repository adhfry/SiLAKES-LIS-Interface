<script setup>
import { ref, watch } from 'vue'
import IconX from './icons/IconX.vue'
import IconSettings from './icons/IconSettings.vue'
import IpOctetInput from './IpOctetInput.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  settings: { type: Object, default: null },
  disabled: { type: Boolean, default: false }, // true saat bridge sedang running
  onSave: { type: Function, required: true }, // async (formData) => void -- WAJIB dilempar (throw) kalau gagal
})
const emit = defineEmits(['update:modelValue'])

const form = ref({
  listen_host: '0.0.0.0',
  listen_port: 123,
  silakes_base_url: '',
  lis_secret_key: '',
  device_code: '',
  poll_interval_seconds: 3.5,
})
const showKey = ref(false)
const saving = ref(false)
const errorMessage = ref('')

watch(
  () => [props.settings, props.modelValue],
  () => {
    if (props.settings && props.modelValue) {
      form.value = { ...props.settings }
      errorMessage.value = ''
    }
  },
  { immediate: true }
)

function close() {
  if (saving.value) return // jangan bisa ditutup di tengah proses simpan
  emit('update:modelValue', false)
}

async function save() {
  if (saving.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    await props.onSave({ ...form.value })
    // Modal HANYA ditutup setelah simpan benar-benar sukses -- kalau onSave
    // melempar error, kita tetap di sini dan tampilkan pesannya di bawah.
    emit('update:modelValue', false)
  } catch (e) {
    errorMessage.value = e?.message || String(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="modelValue" class="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="!saving && close()" />
        <Transition name="modal-pop" appear>
          <div class="modal-panel relative z-10 w-full max-w-md p-6">
            <div class="flex items-center gap-2.5 mb-1">
              <IconSettings :size="18" class="text-primary-600 dark:text-primary-400" />
              <h2 class="text-base font-heading font-bold text-neutral-900 dark:text-neutral-100">Pengaturan Bridge</h2>
            </div>
            <p class="text-[12px] text-neutral-500 dark:text-neutral-400 mb-5">
              {{ disabled ? 'Hentikan bridge dulu untuk mengubah pengaturan.' : 'Perubahan berlaku saat bridge di-Start berikutnya.' }}
            </p>

            <div class="space-y-4" :class="disabled && 'opacity-50 pointer-events-none'">
              <div class="grid grid-cols-3 gap-3">
                <label class="col-span-2 block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Listen Host</span>
                  <IpOctetInput v-model="form.listen_host" />
                  <p class="mt-1 text-[10.5px] leading-snug text-neutral-500 dark:text-neutral-400">
                    Biarkan <strong class="font-mono">0.0.0.0</strong> (dengarkan di semua network interface PC ini).
                    <button type="button" class="text-primary-600 dark:text-primary-400 underline underline-offset-2"
                      @click="form.listen_host = '0.0.0.0'">Reset</button>.
                    Jangan isi IP PC/alat lain di sini — IP tujuan (Server IP) diisi di software SAGES200, arahkan ke IP PC ini.
                  </p>
                </label>
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Port</span>
                  <input v-model.number="form.listen_port" type="number"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
              </div>

              <label class="block">
                <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">SiLAKES API Base URL</span>
                <input v-model="form.silakes_base_url" type="text" placeholder="https://api.silakes.labkesdasumenep.id/api"
                  class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
              </label>

              <label class="block">
                <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">LIS Secret Key (header X-LIS-X)</span>
                <div class="relative">
                  <input v-model="form.lis_secret_key" :type="showKey ? 'text' : 'password'"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 pr-16 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                  <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200 px-1.5"
                    @click="showKey = !showKey">
                    {{ showKey ? 'Sembunyikan' : 'Lihat' }}
                  </button>
                </div>
              </label>

              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Device Code</span>
                  <input v-model="form.device_code" type="text"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Poll Interval (detik)</span>
                  <input v-model.number="form.poll_interval_seconds" type="number" step="0.5"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
              </div>
            </div>

            <p v-if="errorMessage" class="mt-4 text-[12px] text-danger-600 dark:text-danger-400 bg-danger-500/10 border border-danger-500/30 rounded-lg px-3 py-2">
              {{ errorMessage }}
            </p>

            <div class="flex items-center justify-end gap-2 mt-6">
              <button class="px-4 py-2 rounded-lg text-[13px] font-medium text-neutral-500 dark:text-neutral-300 hover:bg-accent-900/5 dark:hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed" :disabled="saving" @click="close">
                Batal
              </button>
              <button
                class="px-4 py-2 rounded-lg text-[13px] font-semibold bg-brand-gradient text-white shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="disabled || saving"
                @click="save"
              >
                {{ saving ? 'Menyimpan…' : 'Simpan Pengaturan' }}
              </button>
            </div>

            <button class="btn-icon absolute top-4 right-4 w-8 h-8 text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-100 hover:bg-accent-900/5 dark:hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed" :disabled="saving" @click="close">
              <IconX :size="16" />
            </button>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-pop-enter-active {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-pop-leave-active {
  transition: all 0.15s ease;
}
.modal-pop-enter-from {
  opacity: 0;
  transform: scale(0.94) translateY(8px);
}
.modal-pop-leave-to {
  opacity: 0;
  transform: scale(0.97);
}
</style>
