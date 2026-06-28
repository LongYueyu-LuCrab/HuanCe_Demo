<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document } from '@element-plus/icons-vue'

const route = useRoute()
const title = computed(() => String(route.meta.title || '模块工作台'))
</script>

<template>
  <el-card shadow="never" class="hc-card placeholder-card">
    <el-empty :description="`${title}正在接入专属业务表单`">
      <template #image>
        <el-icon size="72"><Document /></el-icon>
      </template>
      <p>当前版本已完成角色菜单、数据权限和主列表重构；该模块的审批动作、表单和时间线会在下一轮继续补齐。</p>
    </el-empty>
  </el-card>
</template>
