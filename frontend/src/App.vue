<template>
  <router-view />
  <div class="toasts">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="'toast-' + t.type">{{ t.msg }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onToast } from './toast'

const toasts = ref([])
const handler = (action, t) => {
  if (action === 'add') toasts.value.push(t)
  else toasts.value = toasts.value.filter(x => x.id !== t.id)
}
onMounted(() => onToast(handler))
</script>
