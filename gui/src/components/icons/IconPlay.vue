<script setup>
import IconBase from './IconBase.vue'
defineProps({ size: { type: [Number, String], default: 18 } })
</script>
<template>
  <IconBase :size="size"><polygon points="6 3 20 12 6 21 6 3" /></IconBase>
</template>
