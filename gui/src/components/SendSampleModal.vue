<script setup>
/**
 * Form kirim sampel manual dari bridge (PC ini) ke MC-200, TANPA lewat
 * worklist SiLAKES -- dipakai utk uji protokol / pemakaian ad-hoc langsung.
 *
 * Field & sumber bukti (lihat RESEARCH_LOG.md utk detail forensik):
 * - Patient ID, Sample ID/"Lab ID", Position -- 3 field TERPISAH, dikonfirmasi
 *   dari string resource asli SAGES200 (Language/English.ini):
 *     IDS_CWorkList_39 = "Patient ID"
 *     IDS_CWorkList_34 = "Lab ID"
 *     IDS_CWorkList_3  = "Position"
 *     IDS_CWorkList_28 = "The ID value must be between 1 to 996" (range Position umum)
 *     IDS_CWorkList_52 = "STAT position(1-3)" (range khusus utk sampel cito)
 * - Style: field NYATA ada di layar Worklist Sample (IDS_CWorkListSam_2 =
 *   "Style"), TAPI daftar isinya TIDAK ketemu di sandbox statis. Opsi di
 *   bawah (Normal/STAT/QC/Kalibrasi) adalah TEBAKAN BERDASAR BUKTI TIDAK
 *   LANGSUNG (pola nama file log nyata: Single_Check_* vs Urge_Check_* di
 *   CheckData/, serta menu "Add/Urge" pada IDS_CWorkList_0) -- BUKAN
 *   dikonfirmasi field-by-field dari device. Wajib diverifikasi live.
 * - Accession yang dipakai utk mencocokkan Query MC-200: Sample ID (Lab ID)
 *   diutamakan drpd Patient ID, krn live test membuktikan tombol LIS di
 *   Schedule query pakai ID internal alat (mis. "S10001"), lebih dekat ke
 *   konsep "Lab ID"/nomor sampel drpd Patient ID (lihat gui_app.py::send_sample).
 */
import { ref, watch, onMounted } from 'vue'
import IconX from './icons/IconX.vue'
import IconSend from './icons/IconSend.vue'
import { useBridgeStore } from '../composables/useBridgeStore'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const store = useBridgeStore()

const form = ref({
  patient_id: '',
  name: '',
  sample_id: '',
  position: '',
  style: 'normal',
  tests: [],
})
const saving = ref(false)
const errorMessage = ref('')
const availableTests = ref([])

const STYLE_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'stat', label: 'STAT / Cito (urgent)' },
  { value: 'qc', label: 'QC' },
  { value: 'calibration', label: 'Kalibrasi' },
]

onMounted(async () => {
  try {
    availableTests.value = await store.getKnownTests()
  } catch {
    availableTests.value = []
  }
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      errorMessage.value = ''
    }
  }
)

function toggleTest(code) {
  const idx = form.value.tests.indexOf(code)
  if (idx === -1) form.value.tests.push(code)
  else form.value.tests.splice(idx, 1)
}

function close() {
  if (saving.value) return
  emit('update:modelValue', false)
}

function resetForm() {
  form.value = { patient_id: '', name: '', sample_id: '', position: '', style: 'normal', tests: [] }
}

async function submit() {
  if (saving.value) return
  errorMessage.value = ''

  if (!form.value.patient_id.trim() && !form.value.sample_id.trim()) {
    errorMessage.value = 'Isi minimal salah satu: Patient ID atau Sample ID.'
    return
  }
  if (form.value.tests.length === 0) {
    errorMessage.value = 'Pilih minimal 1 test.'
    return
  }

  saving.value = true
  try {
    await store.sendSample({ ...form.value })
    resetForm()
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
          <div class="glass-panel relative z-10 w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div class="flex items-center gap-2.5 mb-1">
              <IconSend :size="17" class="text-primary-600 dark:text-primary-400" />
              <h2 class="text-base font-heading font-bold text-neutral-900 dark:text-neutral-100">Kirim Sampel ke MC-200</h2>
            </div>
            <p class="text-[12px] text-neutral-500 dark:text-neutral-400 mb-5">
              Sampel ad-hoc langsung dari bridge (tidak lewat worklist SiLAKES). Bridge harus sedang aktif.
            </p>

            <div class="space-y-4">
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Patient ID</span>
                  <input v-model="form.patient_id" type="text" placeholder="mis. P11531-12248"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Sample ID / Lab ID</span>
                  <input v-model="form.sample_id" type="text" placeholder="mis. S10001"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
              </div>
              <p class="text-[10.5px] leading-snug text-neutral-500 dark:text-neutral-400 -mt-2">
                Kalau MC-200 nge-query pakai ID yang beda dari keduanya, bridge tetap otomatis
                menjawab selama ini satu-satunya sampel yang sedang pending (lihat log real-time).
              </p>

              <label class="block">
                <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">Nama Pasien</span>
                <input v-model="form.name" type="text" placeholder="mis. MUHAMMAD TAUFIQURRAHMAN"
                  class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
              </label>

              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Position <span class="font-normal text-neutral-400 dark:text-neutral-500">(cup, umumnya 1–8)</span>
                  </span>
                  <input v-model="form.position" type="number" min="1" max="996" placeholder="mis. 3"
                    class="selectable w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50" />
                </label>
                <label class="block">
                  <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    Style <span class="font-normal text-amber-600 dark:text-amber-400">(belum terverifikasi live)</span>
                  </span>
                  <select v-model="form.style"
                    class="w-full bg-neutral-500/5 dark:bg-neutral-950/60 border border-accent-900/10 dark:border-white/10 rounded-lg px-3 py-2 text-[13px] text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/50">
                    <option v-for="opt in STYLE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                  </select>
                </label>
              </div>

              <div>
                <span class="block text-[11px] font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                  Test ({{ form.tests.length }} dipilih)
                </span>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="code in availableTests"
                    :key="code"
                    type="button"
                    class="px-2.5 py-1 rounded-md text-[12px] font-mono font-medium border transition-colors duration-150"
                    :class="
                      form.tests.includes(code)
                        ? 'bg-primary-500/15 text-primary-700 dark:text-primary-400 border-primary-500/40'
                        : 'text-neutral-500 dark:text-neutral-400 border-accent-900/10 dark:border-white/10 hover:border-primary-500/30'
                    "
                    @click="toggleTest(code)"
                  >
                    {{ code }}
                  </button>
                </div>
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
                class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-semibold bg-brand-gradient text-white shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="saving"
                @click="submit"
              >
                <IconSend :size="13" />
                {{ saving ? 'Mengirim…' : 'Kirim Sampel' }}
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
