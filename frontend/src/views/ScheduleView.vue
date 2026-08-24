<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchOrderDetail } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem, ScheduleItem } from '../types'

const session = useSession()
const schedules = computed(() => session.state.dashboard?.schedules ?? [])
const drawerVisible = ref(false)
const loading = ref(false)
const selectedOrder = ref<OrderItem | null>(null)

async function openOrderDetail(schedule: ScheduleItem) {
  drawerVisible.value = true
  selectedOrder.value = null
  loading.value = true
  try {
    selectedOrder.value = await fetchOrderDetail(schedule.order_no)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>排期调度</h2>
        <p>按当前角色展示可见的苏州、江阴与委外排期，覆盖质量部分流、项目周期表和变更回流后的排期状态。</p>
      </div>
    </div>

    <ScheduleTable :orders="schedules" :user="session.state.user" @detail="openOrderDetail" />

    <el-drawer v-model="drawerVisible" title="订单详情" size="min(720px, 94vw)">
      <OrderSnapshot :order="selectedOrder" :loading="loading" title="排期订单信息" />
    </el-drawer>
  </div>
</template>
