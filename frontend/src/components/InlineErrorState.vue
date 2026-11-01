<script setup lang="ts">
defineProps<{
  message: string
  retryLabel?: string
}>()

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="inline-error-state" role="alert">
    <div>
      <strong>数据暂时无法加载</strong>
      <p>{{ message }}</p>
    </div>
    <el-button type="warning" plain @click="emit('retry')">{{ retryLabel || '重新加载' }}</el-button>
  </div>
</template>
