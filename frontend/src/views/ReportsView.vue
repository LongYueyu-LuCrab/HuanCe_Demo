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
const reviewStage = ref<'sales' | 'gm'>('sales')
const activeReport = ref<ReportItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const form = reactive({ audit_opinion: '' })

onMounted(() => {
  const orderNo = String(route.query.order || '')
  const action = String(route.query.action || '')
  const target = reports.value.find((report) => report.order_no === orderNo)
  if (target && ['start_report_review', 'report_sales_pass', 'report_sales_reject', 'report_gm_pass', 'report_gm_reject'].includes(action)) {
    openWorkflow(action, target)
  }
})

const titleMap: Record<string, string> = {
  sales: '销售初审',
  gm: '总经理终审',
}

const actionMeta = computed(() => {
  const rejected = activeAction.value.includes('reject')
  const finalReview = reviewStage.value === 'gm'
  return {
    title: titleMap[reviewStage.value] || '报告审核',
    stage: rejected ? '报告审核 → 退回重制' : finalReview ? '总经理终审 → 审核结果' : '报告 → 销售初审',
    impact: rejected ? '提交后报告会退回主责实验室重制，并记录本次审核意见。' : '提交后会记录审核意见，并推进报告审核节点。',
    passLabel: finalReview ? '终审通过' : '初审通过',
    rejectLabel: finalReview ? '终审驳回' : '初审驳回',
  }
})

function openWorkflow(action: string, report: ReportItem) {
  reviewStage.value = report.status_key === 3 ? 'gm' : 'sales'
  activeAction.value = action
  activeReport.value = report
  form.audit_opinion = ''
  dialogVisible.value = true
  void loadOrderContext(report.order_no)
}

function reportFileUrl(preview = false) {
  const url = activeReport.value?.download_url
  if (!url || !preview) return url || ''
  return `${url}${url.includes('?') ? '&' : '?'}preview=1`
}

function previewReport() {
  const url = reportFileUrl(true)
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function downloadReport() {
  const url = reportFileUrl()
  if (url) window.location.assign(url)
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

async function submitWorkflow(result: 'pass' | 'reject') {
  if (!activeReport.value) return
  const submittedReportNo = activeReport.value.report_no
  submitting.value = true
  try {
    await workflowAction({
      action: reviewStage.value === 'sales'
        ? result === 'pass' ? 'report_sales_pass' : 'report_sales_reject'
        : result === 'pass' ? 'report_gm_pass' : 'report_gm_reject',
      report_no: activeReport.value.report_no,
      order_no: activeReport.value.order_no,
      expected_update_time: activeOrder.value?.updated_at,
      audit_opinion: form.audit_opinion,
    })
    ElMessage.success('报告审核已提交')
    dialogVisible.value = false
    // 审核成功后先更新当前内存中的待办，避免旧行停留到手动刷新。
    if (session.state.dashboard) {
      session.state.dashboard.pending_reports = session.state.dashboard.pending_reports.filter(
        (report) => report.report_no !== submittedReportNo,
      )
      session.state.dashboard.metrics.pending_reports = session.state.dashboard.pending_reports.length
    }
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
      <el-space v-if="activeReport?.has_file" class="report-file-actions" wrap>
        <el-button size="small" type="primary" plain @click="previewReport">预览 PDF</el-button>
        <el-button size="small" plain @click="downloadReport">下载 PDF</el-button>
      </el-space>
    </div>
    <el-divider content-position="left">审核意见</el-divider>
    <el-form label-position="top" class="mt-16">
      <el-form-item label="审核意见">
        <el-input v-model="form.audit_opinion" type="textarea" :rows="4" placeholder="填写通过说明或驳回修改要求" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="danger" plain :loading="submitting" @click="submitWorkflow('reject')">{{ actionMeta.rejectLabel }}</el-button>
      <el-button type="primary" :loading="submitting" @click="submitWorkflow('pass')">{{ actionMeta.passLabel }}</el-button>
    </template>
  </el-dialog>

  <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
    <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="报告关联订单信息" />
  </el-drawer>
</template>
