<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import OrderTable from '../components/OrderTable.vue'
import { workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem } from '../types'

const session = useSession()
const orders = computed(() => session.state.dashboard?.outsource_orders ?? [])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeOrder = ref<OrderItem | null>(null)
const form = reactive({
  test_item_list: '',
  test_standard: '',
  test_raw_data: '',
  test_conclusion_temp: '',
  test_start_time: '',
  test_end_time: '',
})

function openWorkflow(action: string, order: OrderItem) {
  if (action !== 'outsource_result') return
  activeOrder.value = order
  Object.assign(form, {
    test_item_list: order.test_demand || order.project_name,
    test_standard: '',
    test_raw_data: '',
    test_conclusion_temp: '',
    test_start_time: '',
    test_end_time: '',
  })
  dialogVisible.value = true
}

async function submitResult() {
  if (!activeOrder.value) return
  submitting.value = true
  try {
    await workflowAction({
      action: 'outsource_result',
      order_no: activeOrder.value.order_no,
      ...form,
    })
    ElMessage.success('委外试验结果已回传')
    dialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '委外结果回传失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <OrderTable
    title="委外试验订单"
    subtitle="展示分配给外部委托实验室的订单；质量部可录入委外试验结果回传。"
    :orders="orders"
    :user="session.state.user"
    @workflow="openWorkflow"
  />

  <el-dialog v-model="dialogVisible" title="委外试验结果回传" width="720px">
    <el-alert v-if="activeOrder" :title="`${activeOrder.order_no} / ${activeOrder.customer}`" type="info" show-icon :closable="false" />
    <el-form label-position="top" class="form-grid mt-16">
      <el-form-item label="委外试验项目" class="form-wide"><el-input v-model="form.test_item_list" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="执行标准 / 报告依据"><el-input v-model="form.test_standard" /></el-form-item>
      <el-form-item label="委外开始时间"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
      <el-form-item label="委外完成时间"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
      <el-form-item label="委外原始数据 / 回传摘要" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
      <el-form-item label="委外临时结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitResult">确认回传</el-button>
    </template>
  </el-dialog>
</template>
