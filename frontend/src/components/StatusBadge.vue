<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label?: string | null
  size?: 'large' | 'default' | 'small'
}>(), { label: '', size: 'default' })

const type = computed<'success' | 'warning' | 'danger' | 'info' | 'primary'>(() => {
  const value = props.label || ''
  if (/驳回|异常|失败|作废|退单|逾期|不合格/.test(value)) return 'danger'
  if (/待|等待|变更|未到|草稿|未收款|维修/.test(value)) return 'warning'
  if (/已|完成|通过|合格|正常|办结|出库|入库/.test(value)) return 'success'
  if (/实验中|执行中|处理中|审核中|排期中/.test(value)) return 'primary'
  return 'info'
})
</script>

<template>
  <el-tag :type="type" :size="size" effect="plain" :aria-label="`状态：${label || '未标记'}`">
    {{ label || '未标记' }}
  </el-tag>
</template>
