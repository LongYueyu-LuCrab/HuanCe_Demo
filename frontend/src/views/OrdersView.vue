<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import OrderTable from '../components/OrderTable.vue'
import { createOrder, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem } from '../types'

const session = useSession()
const dialogVisible = ref(false)
const submitting = ref(false)
const actionDialogVisible = ref(false)
const actionSubmitting = ref(false)
const activeAction = ref('')
const activeOrder = ref<OrderItem | null>(null)
const actionForm = reactive<Record<string, unknown>>({})
const form = reactive({
  customer_name: '',
  contact_name: '',
  phone: '',
  project_name: '',
  test_requirements: '',
  expected_sample_arrival: '',
  expected_delivery_date: '',
  quoted_amount: '',
  is_urgent: false,
})

const orders = computed(() => session.state.dashboard?.order_groups?.orders ?? session.state.dashboard?.recent_orders ?? [])

const actionTitleMap: Record<string, string> = {
  review_pass: '评审通过',
  review_reject: '评审驳回',
  order_update: '修改订单并重新提交',
  order_cancel: '退单',
  sales_confirm: '确认无变更',
  create_change: '填写更改单',
  schedule_assign: '排期分配',
  process_change: '处理变更',
  register_sample: '样品登记',
  start_test: '开始试验',
  submit_test: '提交试验结果',
  outsource_result: '委外试验结果回传',
  issue_report: '出具检测报告',
}

function openWorkflow(action: string, order: OrderItem) {
  activeAction.value = action
  activeOrder.value = order
  Object.keys(actionForm).forEach((key) => delete actionForm[key])
  Object.assign(actionForm, {
    customer_name: order.customer,
    contact_name: order.contact || '',
    phone: order.phone || '',
    project_name: order.project_name,
    test_demand: order.test_demand || '',
    quoted_amount: order.total_quote || '',
    reason: '',
    reject_reason: '',
    biz_quote_detail: '',
    note: '',
    change_scene: action === 'create_change' && order.status_key === 4 ? 2 : 1,
    change_content: '',
    new_test_demand: order.test_demand || '',
    test_type: 1,
    plan_start_time: '',
    plan_end_time: '',
    outsource_factory: '',
    outsource_price: '',
    outsource_cycle: '',
    sample_name: `${order.project_name} 样品`,
    sample_spec: '客户送检样品',
    sample_count: 1,
    storage_condition: '常温',
    test_item_list: order.test_demand || '',
    test_standard: '',
    test_raw_data: '',
    test_conclusion_temp: '',
    test_start_time: '',
    test_end_time: '',
    report_no: '',
    final_conclusion: '',
  })
  actionDialogVisible.value = true
}

async function submitWorkflow() {
  if (!activeOrder.value || !activeAction.value) return
  actionSubmitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrder.value.order_no,
      ...actionForm,
    })
    ElMessage.success('流程操作已完成')
    actionDialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '流程操作失败')
  } finally {
    actionSubmitting.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    await createOrder(form)
    ElMessage.success('订单已提交，等待商务技术评审')
    dialogVisible.value = false
    Object.assign(form, {
      customer_name: '',
      contact_name: '',
      phone: '',
      project_name: '',
      test_requirements: '',
      expected_sample_arrival: '',
      expected_delivery_date: '',
      quoted_amount: '',
      is_urgent: false,
    })
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>订单管理</h2>
        <p>按当前角色显示可查看订单；销售可从这里发起新订单。</p>
      </div>
      <el-button v-if="session.canCreateOrder.value" type="primary" @click="dialogVisible = true">销售下单</el-button>
    </div>

    <OrderTable :orders="orders" :user="session.state.user" @workflow="openWorkflow" />

    <el-dialog v-model="dialogVisible" title="销售下单" width="760px">
      <el-form label-position="top" class="form-grid">
        <el-form-item label="客户名称"><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="项目名称"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="预计样品到达"><el-date-picker v-model="form.expected_sample_arrival" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="预计交付日期"><el-date-picker v-model="form.expected_delivery_date" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="报价金额"><el-input v-model="form.quoted_amount" type="number" /></el-form-item>
        <el-form-item label="加急"><el-switch v-model="form.is_urgent" /></el-form-item>
        <el-form-item label="试验需求" class="form-wide"><el-input v-model="form.test_requirements" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交订单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="actionDialogVisible" :title="actionTitleMap[activeAction] || '流程操作'" width="760px">
      <el-alert v-if="activeOrder" :title="`${activeOrder.order_no} / ${activeOrder.customer}`" type="info" show-icon :closable="false" />
      <el-form label-position="top" class="form-grid action-form">
        <template v-if="activeAction === 'review_pass' || activeAction === 'review_reject'">
          <el-form-item label="商务报价/评审说明" class="form-wide"><el-input v-model="actionForm.biz_quote_detail" type="textarea" :rows="3" /></el-form-item>
          <el-form-item v-if="activeAction === 'review_reject'" label="驳回原因" class="form-wide"><el-input v-model="actionForm.reject_reason" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'order_update'">
          <el-form-item label="客户名称"><el-input v-model="actionForm.customer_name" /></el-form-item>
          <el-form-item label="联系人"><el-input v-model="actionForm.contact_name" /></el-form-item>
          <el-form-item label="电话"><el-input v-model="actionForm.phone" /></el-form-item>
          <el-form-item label="项目名称"><el-input v-model="actionForm.project_name" /></el-form-item>
          <el-form-item label="报价"><el-input v-model="actionForm.quoted_amount" type="number" /></el-form-item>
          <el-form-item label="试验需求" class="form-wide"><el-input v-model="actionForm.test_demand" type="textarea" :rows="4" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'order_cancel'">
          <el-form-item label="退单原因" class="form-wide"><el-input v-model="actionForm.reason" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'sales_confirm'">
          <el-form-item label="确认说明" class="form-wide"><el-input v-model="actionForm.note" type="textarea" :rows="3" placeholder="确认样品到货时间和试验需求无变更" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'create_change'">
          <el-form-item label="变更场景">
            <el-select v-model="actionForm.change_scene">
              <el-option label="样品到货前变更" :value="1" />
              <el-option label="试验过程中变更" :value="2" />
            </el-select>
          </el-form-item>
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="actionForm.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="actionForm.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'schedule_assign'">
          <el-form-item label="执行路径">
            <el-select v-model="actionForm.test_type">
              <el-option label="苏州内部实验室" :value="1" />
              <el-option label="江阴内部实验室" :value="2" />
              <el-option label="外部委外" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="计划开始"><el-date-picker v-model="actionForm.plan_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="计划结束"><el-date-picker v-model="actionForm.plan_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外厂家"><el-input v-model="actionForm.outsource_factory" /></el-form-item>
          <el-form-item label="委外价格"><el-input v-model="actionForm.outsource_price" type="number" /></el-form-item>
          <el-form-item label="委外周期/天"><el-input v-model="actionForm.outsource_cycle" type="number" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'process_change'">
          <el-form-item label="调整后开始"><el-date-picker v-model="actionForm.plan_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="调整后结束"><el-date-picker v-model="actionForm.plan_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'register_sample'">
          <el-form-item label="样品名称"><el-input v-model="actionForm.sample_name" /></el-form-item>
          <el-form-item label="规格型号"><el-input v-model="actionForm.sample_spec" /></el-form-item>
          <el-form-item label="数量"><el-input v-model="actionForm.sample_count" type="number" /></el-form-item>
          <el-form-item label="存储条件"><el-input v-model="actionForm.storage_condition" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide"><el-input v-model="actionForm.test_item_list" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="检测标准"><el-input v-model="actionForm.test_standard" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'submit_test'">
          <el-form-item label="原始检测数据" class="form-wide"><el-input v-model="actionForm.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="临时结论" class="form-wide"><el-input v-model="actionForm.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'outsource_result'">
          <el-form-item label="委外试验项目" class="form-wide"><el-input v-model="actionForm.test_item_list" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="执行标准"><el-input v-model="actionForm.test_standard" placeholder="例如：委外厂家报告编号 / 执行标准" /></el-form-item>
          <el-form-item label="委外开始时间"><el-date-picker v-model="actionForm.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外完成时间"><el-date-picker v-model="actionForm.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外原始数据 / 回传摘要" class="form-wide"><el-input v-model="actionForm.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="委外临时结论" class="form-wide"><el-input v-model="actionForm.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>

        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="actionForm.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="最终结论" class="form-wide"><el-input v-model="actionForm.final_conclusion" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="actionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionSubmitting" @click="submitWorkflow">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>
