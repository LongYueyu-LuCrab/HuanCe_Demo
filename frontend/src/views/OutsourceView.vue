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
const activeAction = ref('')
const form = reactive({
  test_item_list: '',
  test_standard: '',
  test_raw_data: '',
  test_conclusion_temp: '',
  result_status: '',
  test_start_time: '',
  test_end_time: '',
})

function openWorkflow(action: string, order: OrderItem) {
  if (!['outsource_result', 'submit_test'].includes(action)) return
  activeAction.value = action
  activeOrder.value = order
  Object.assign(form, {
    test_item_list: order.test_demand || order.project_name,
    test_standard: '',
    test_raw_data: '',
    test_conclusion_temp: '',
    result_status: '',
    test_start_time: '',
    test_end_time: '',
  })
  dialogVisible.value = true
}

async function submitResult() {
  if (!activeOrder.value) return
  if (activeAction.value === 'outsource_result' && !form.result_status) {
    ElMessage.warning('请选择实验结果')
    return
  }
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrder.value.order_no,
      ...form,
    })
    ElMessage.success(activeAction.value === 'submit_test' ? '委外实验结果已正式提交' : '委外实验已结束并记录结果')
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
    subtitle="展示分配给当前负责人的委外任务；内部实验室负责人维护厂家、排期与结果回传。"
    :orders="orders"
    :user="session.state.user"
    @workflow="openWorkflow"
  />

  <el-dialog v-model="dialogVisible" :title="activeAction === 'submit_test' ? '提交委外实验结果' : '委外实验结果回传 / 结束实验'" width="720px">
    <el-alert v-if="activeOrder" :title="`${activeOrder.order_no} / ${activeOrder.customer}`" type="info" show-icon :closable="false" />
    <el-form v-if="activeAction === 'outsource_result'" label-position="top" class="form-grid mt-16">
      <el-form-item label="委外试验项目" class="form-wide"><el-input v-model="form.test_item_list" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="执行标准 / 报告依据"><el-input v-model="form.test_standard" /></el-form-item>
      <el-form-item label="委外开始时间"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
      <el-form-item label="委外完成时间"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
      <el-form-item label="实验结果" class="form-wide" required>
        <el-radio-group v-model="form.result_status">
          <el-radio-button value="pass">合格</el-radio-button>
          <el-radio-button value="fail">不合格</el-radio-button>
          <el-radio-button value="abnormal">异常</el-radio-button>
          <el-radio-button value="retest">待复测</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="委外原始数据 / 回传摘要" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
      <el-form-item label="委外实验结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
      <el-alert class="form-wide" title="回传后实验状态为“已结束待提交结果”" type="info" :closable="false" show-icon />
    </el-form>
    <el-alert
      v-else
      class="mt-16"
      title="确认正式提交委外实验结果"
      type="warning"
      :closable="false"
      description="提交后将计入订单完成判断；全部执行路径均提交后才进入待出报告。"
      show-icon
    />
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitResult">{{ activeAction === 'submit_test' ? '确认提交' : '确认回传并结束' }}</el-button>
    </template>
  </el-dialog>
</template>
