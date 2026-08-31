<script setup>
import StatCard from './StatCard.vue'

defineProps({
  stats: { type: Object, required: true },
})
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
    <StatCard label="Koneksi Masuk" :value="stats.connections_total ?? 0" accent="primary" />
    <StatCard label="Query Dijawab" :value="stats.queries_answered ?? 0" accent="accent" />
    <StatCard label="Hasil Terkirim" :value="stats.results_sent_ok ?? 0" accent="success" />
    <StatCard label="Gagal Kirim" :value="stats.results_sent_error ?? 0" accent="danger" />
  </div>
</template>
