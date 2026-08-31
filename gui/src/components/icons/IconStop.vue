<script setup>
import IconBase from './IconBase.vue'
defineProps({ size: { type: [Number, String], default: 18 } })
</script>
<template>
  <IconBase :size="size"><rect x="5" y="5" width="14" height="14" rx="2" /></IconBase>
</template>
