<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ReportList from '../components/ReportList.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem, ReportItem } from '../types'

const session = useSession()
const reports = computed(() => session.state.dashboard?.pending_reports ?? [])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeReport = ref<ReportItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const form = reactive({ audit_opinion: '' })

const titleMap: Record<string, string> = {
  report_sales_pass: '销售初审通过',
  report_sales_reject: '销售初审驳回',
  report_gm_pass: '总经理终审通过',
  report_gm_reject: '总经理终审驳回',
}

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

  <el-dialog v-model="dialogVisible" :title="titleMap[activeAction] || '报告审核'" width="min(960px, 94vw)">
    <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="报告关联订单信息" />
    <el-form label-position="top" class="mt-16">
      <el-form-item label="审核意见">
        <el-input v-model="form.audit_opinion" type="textarea" :rows="4" placeholder="填写通过说明或驳回修改要求" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button>
    </template>
  </el-dialog>

  <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
    <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="报告关联订单信息" />
  </el-drawer>
</template>
