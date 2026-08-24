<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem, ScheduleItem } from '../types'

const session = useSession()
const schedules = computed(() => session.state.dashboard?.schedules ?? [])
const drawerVisible = ref(false)
const dialogVisible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const selectedOrder = ref<OrderItem | null>(null)
const activeSchedule = ref<ScheduleItem | null>(null)
const activeAction = ref('')
const form = reactive({
  plan_start_time: '', plan_end_time: '', outsource_factory: '', outsource_price: '', outsource_cycle: '',
  sample_name: '', sample_spec: '', sample_count: 1, storage_condition: '常温',
  test_item_list: '', test_standard: '', test_raw_data: '', test_conclusion_temp: '',
  test_start_time: '', test_end_time: '', change_scene: 2, new_test_demand: '', change_content: '',
  report_no: '', final_conclusion: '',
})

async function loadOrder(orderNo: string) {
  selectedOrder.value = null
  loading.value = true
  try {
    selectedOrder.value = await fetchOrderDetail(orderNo)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    loading.value = false
  }
}

function openOrderDetail(schedule: ScheduleItem) {
  drawerVisible.value = true
  void loadOrder(schedule.order_no)
}

function openWorkflow(action: string, schedule: ScheduleItem) {
  activeAction.value = action
  activeSchedule.value = schedule
  Object.assign(form, {
    plan_start_time: schedule.start_time || '', plan_end_time: schedule.end_time || '',
    outsource_factory: '', outsource_price: '', outsource_cycle: '',
    sample_name: `${schedule.project_name} 样品`, sample_spec: '客户送检样品', sample_count: 1,
    storage_condition: '常温', test_item_list: schedule.remark || schedule.project_name,
    test_standard: '', test_raw_data: '', test_conclusion_temp: '', test_start_time: '', test_end_time: '',
    change_scene: 2, new_test_demand: '', change_content: '', report_no: '', final_conclusion: '',
  })
  dialogVisible.value = true
  void loadOrder(schedule.order_no)
}

async function submitWorkflow() {
  if (!activeSchedule.value) return
  submitting.value = true
  try {
    await workflowAction({ action: activeAction.value, order_no: activeSchedule.value.order_no, schedule_id: activeSchedule.value.id, ...form })
    ElMessage.success('任务操作已完成')
    dialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar"><div><h2>排期与任务</h2><p>实验室负责人在这里维护本人负责的内部及委外任务、样品、变更和报告。</p></div></div>
    <ScheduleTable :orders="schedules" :user="session.state.user" @detail="openOrderDetail" @workflow="openWorkflow" />

    <el-dialog v-model="dialogVisible" title="实验室任务操作" width="min(960px, 94vw)">
      <OrderSnapshot :order="selectedOrder" :loading="loading" title="任务关联订单" />
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'schedule_assign' || activeAction === 'process_change'">
          <el-form-item label="计划开始"><el-date-picker v-model="form.plan_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="计划结束"><el-date-picker v-model="form.plan_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <template v-if="activeAction === 'schedule_assign' && activeSchedule?.test_type.includes('委外')">
            <el-form-item label="委外厂家"><el-input v-model="form.outsource_factory" /></el-form-item>
            <el-form-item label="委外价格"><el-input v-model="form.outsource_price" type="number" /></el-form-item>
            <el-form-item label="委外周期/天"><el-input v-model="form.outsource_cycle" type="number" /></el-form-item>
          </template>
        </template>
        <template v-else-if="activeAction === 'register_sample'">
          <el-form-item label="样品名称"><el-input v-model="form.sample_name" /></el-form-item>
          <el-form-item label="规格型号"><el-input v-model="form.sample_spec" /></el-form-item>
          <el-form-item label="数量"><el-input v-model="form.sample_count" type="number" /></el-form-item>
          <el-form-item label="存储条件"><el-input v-model="form.storage_condition" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide"><el-input v-model="form.test_item_list" disabled type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="执行标准" class="form-wide"><el-input v-model="form.test_standard" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'submit_test' || activeAction === 'outsource_result'">
          <el-form-item v-if="activeAction === 'outsource_result'" label="开始时间"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item v-if="activeAction === 'outsource_result'" label="完成时间"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="原始数据 / 回传摘要" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="试验结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'create_change'">
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="form.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="form.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="form.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="最终结论" class="form-wide"><el-input v-model="form.final_conclusion" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button></template>
    </el-dialog>

    <el-drawer v-model="drawerVisible" title="订单详情" size="min(720px, 94vw)"><OrderSnapshot :order="selectedOrder" :loading="loading" title="排期订单信息" /></el-drawer>
  </div>
</template>
