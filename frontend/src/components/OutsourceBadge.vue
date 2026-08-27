<script setup lang="ts">
withDefaults(defineProps<{
  visible?: boolean
}>(), {
  visible: false,
})
</script>

<template>
  <el-tag
    v-if="visible"
    class="outsource-badge"
    type="danger"
    effect="dark"
    size="small"
    aria-label="委外订单"
  >
    委外
  </el-tag>
</template>
