<script setup>
import IconBase from './IconBase.vue'
defineProps({ size: { type: [Number, String], default: 18 } })
</script>
<template>
  <IconBase :size="size"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></IconBase>
</template>
