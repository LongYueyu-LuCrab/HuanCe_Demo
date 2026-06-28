<script setup lang="ts">
import { computed } from 'vue'
import ScheduleTable from '../components/ScheduleTable.vue'
import { useSession } from '../stores/session'

const session = useSession()
const schedules = computed(() => session.state.dashboard?.schedules ?? [])
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>排期调度</h2>
        <p>按当前角色展示可见的苏州、江阴与委外排期，覆盖质量部分流、项目周期表和变更回流后的排期状态。</p>
      </div>
    </div>

    <ScheduleTable :orders="schedules" />
  </div>
</template>
