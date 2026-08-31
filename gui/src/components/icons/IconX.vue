<script setup>
import IconBase from './IconBase.vue'
defineProps({ size: { type: [Number, String], default: 18 } })
</script>
<template>
  <IconBase :size="size">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </IconBase>
</template>
