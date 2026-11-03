<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ReportList from '../components/ReportList.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem, ReportItem } from '../types'

const session = useSession()
const route = useRoute()
const reports = computed(() => session.state.dashboard?.pending_reports ?? [])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeReport = ref<ReportItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const form = reactive({ audit_opinion: '' })

onMounted(() => {
  const orderNo = String(route.query.order || '')
  const action = String(route.query.action || '')
  const target = reports.value.find((report) => report.order_no === orderNo)
  if (target && ['report_sales_pass', 'report_sales_reject', 'report_gm_pass', 'report_gm_reject'].includes(action)) {
    openWorkflow(action, target)
  }
})

const titleMap: Record<string, string> = {
  report_sales_pass: '销售初审通过',
  report_sales_reject: '销售初审驳回',
  report_gm_pass: '总经理终审通过',
  report_gm_reject: '总经理终审驳回',
}

const actionMeta = computed(() => {
  const rejected = activeAction.value.includes('reject')
  const finalReview = activeAction.value.includes('gm')
  return {
    title: titleMap[activeAction.value] || '报告审核',
    stage: rejected ? '报告审核 → 退回重制' : finalReview ? '总经理终审 → 审核结果' : '报告 → 销售初审',
    impact: rejected ? '提交后报告会退回主责实验室重制，并记录本次审核意见。' : '提交后会记录审核意见，并推进报告审核节点。',
    button: rejected ? '确认驳回重制' : finalReview ? '确认终审通过' : '确认初审通过',
  }
})

function openWorkflow(action: string, report: ReportItem) {
  activeAction.value = action
  activeReport.value = report
  form.audit_opinion = ''
  dialogVisible.value = true
  void loadOrderContext(report.order_no)
}

async function loadOrderContext(orderNo: string) {
  activeOrder.value = null
  orderLoading.value = true
  try {
    activeOrder.value = await fetchOrderDetail(orderNo)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    orderLoading.value = false
  }
}

function openOrderDetail(report: ReportItem) {
  detailDrawerVisible.value = true
  void loadOrderContext(report.order_no)
}

async function submitWorkflow() {
  if (!activeReport.value) return
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      report_no: activeReport.value.report_no,
      order_no: activeReport.value.order_no,
      expected_update_time: activeOrder.value?.updated_at,
      audit_opinion: form.audit_opinion,
    })
    ElMessage.success('报告审核已提交')
    dialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '审核失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <ReportList
    :reports="reports"
    :user="session.state.user"
    @workflow="openWorkflow"
    @detail="openOrderDetail"
  />

  <el-dialog v-model="dialogVisible" class="action-dialog" :title="actionMeta.title" width="min(960px, 94vw)">
    <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="报告关联订单信息" />
    <div class="action-dialog-context mt-16">
      <div><strong>{{ activeReport?.report_no }}</strong><span>{{ activeReport?.customer }} · {{ activeReport?.project_name }}</span></div>
      <div class="action-dialog-step"><span>流程影响</span><strong>{{ actionMeta.stage }}</strong><small>{{ actionMeta.impact }}</small></div>
    </div>
    <el-divider content-position="left">审核意见</el-divider>
    <el-form label-position="top" class="mt-16">
      <el-form-item label="审核意见">
        <el-input v-model="form.audit_opinion" type="textarea" :rows="4" placeholder="填写通过说明或驳回修改要求" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitWorkflow">{{ actionMeta.button }}</el-button>
    </template>
  </el-dialog>

  <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
    <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="报告关联订单信息" />
  </el-drawer>
</template>
