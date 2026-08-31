<script setup>
import IconBase from './IconBase.vue'
defineProps({ size: { type: [Number, String], default: 18 } })
</script>
<template>
  <IconBase :size="size">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </IconBase>
</template>
