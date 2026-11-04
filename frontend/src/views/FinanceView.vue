<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import InvoiceTable from '../components/InvoiceTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { InvoiceItem, OrderItem } from '../types'

const session = useSession()
const preinvoiceCandidates = computed(() => session.state.dashboard?.finance?.preinvoice_candidates ?? [])
const pendingInvoices = computed(() => session.state.dashboard?.finance?.pending_invoices ?? [])
const issuedInvoices = computed(() => session.state.dashboard?.finance?.issued_invoices ?? [])
const canOperateFinance = computed(() => Boolean(
  session.state.user?.is_chairman || session.state.user?.roles?.includes('会计'),
))
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeInvoice = ref<InvoiceItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const form = reactive({
  invoice_no: '',
  invoice_amount: '',
  invoice_type: '增值税专票',
  invoice_date: '',
  pay_status: 0,
  void_reason: '',
})

const actionMeta = computed(() => {
  const map: Record<string, { title: string; stage: string; impact: string; button: string }> = {
    preinvoice_create: { title: '阶段开票', stage: '当前订单阶段 → 阶段开票记录', impact: '阶段开票不会结束订单，系统会保留后续最终总开票余额。', button: '确认阶段开票' },
    invoice_create: { title: '最终总开票', stage: '终审通过 → 订单办结', impact: '提交后必须一次性开完剩余金额，订单进入已开票办结。', button: '确认最终开票' },
    invoice_pay: { title: '更新回款状态', stage: '已开票 → 回款记录', impact: '提交后只更新回款状态，不改变发票金额和审核结果。', button: '保存回款状态' },
    invoice_void: { title: '作废发票', stage: '已开票 → 退回待开票余额', impact: '作废会影响可开票余额，必须填写清晰的作废原因。', button: '确认作废发票' },
  }
  return map[activeAction.value] || { title: '财务操作', stage: '订单财务节点', impact: '请确认金额和操作影响后提交。', button: '确认提交' }
})

function openWorkflow(action: string, invoice: InvoiceItem) {
  activeAction.value = action
  activeInvoice.value = invoice
  Object.assign(form, {
    invoice_no: invoice.invoice_no || '',
    invoice_amount: action === 'preinvoice_create' ? '' : invoice.invoice_amount || '',
    invoice_type: invoice.invoice_type && invoice.invoice_type !== '待确认' ? invoice.invoice_type : '增值税专票',
    invoice_date: invoice.invoice_date || '',
    pay_status: action === 'invoice_pay' && invoice.pay_status === '已回款' ? 1 : 0,
    void_reason: '',
  })
  dialogVisible.value = true
  void loadOrderContext(invoice.order_no)
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

function openOrderDetail(invoice: InvoiceItem) {
  detailDrawerVisible.value = true
  void loadOrderContext(invoice.order_no)
}

async function submitWorkflow() {
  if (!activeInvoice.value) return
  if (!['invoice_pay', 'invoice_void'].includes(activeAction.value) && (!form.invoice_amount || Number(form.invoice_amount) <= 0)) {
    ElMessage.warning('请填写大于 0 的开票金额')
    return
  }
  if (activeAction.value === 'invoice_void' && !form.void_reason.trim()) {
    ElMessage.warning('请填写作废原因')
    return
  }
  if (
    activeAction.value === 'preinvoice_create'
    && Number(form.invoice_amount) >= Number(activeInvoice.value.remaining_amount)
  ) {
    ElMessage.warning('预开票必须为最终总开票保留余额')
    return
  }
  if (
    activeAction.value === 'invoice_create'
    && Number(form.invoice_amount) !== Number(activeInvoice.value.remaining_amount)
  ) {
    ElMessage.warning(`最终总开票必须一次性开完剩余 ${activeInvoice.value.remaining_amount} 元`)
    return
  }
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeInvoice.value.order_no,
      expected_update_time: activeOrder.value?.updated_at,
      report_no: activeInvoice.value.report_no,
      invoice_no: activeInvoice.value.invoice_no || form.invoice_no,
      invoice_amount: form.invoice_amount,
      invoice_type: form.invoice_type,
      invoice_date: form.invoice_date,
      pay_status: form.pay_status,
      void_reason: form.void_reason,
    })
    ElMessage.success(
      activeAction.value === 'preinvoice_create'
        ? '预开票已记录，订单继续流转'
        : activeAction.value === 'invoice_create'
          ? '最终总开票办结完成'
          : activeAction.value === 'invoice_void'
            ? '发票已作废，金额已退回待开票余额'
          : '回款状态已更新',
    )
    dialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '财务操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <InvoiceTable
      mode="preinvoice"
      title="可阶段开票订单"
      subtitle="订单未退单、未办结且尚未完成最终报告审核时，均可阶段开票；阶段开票不推进订单流程。"
      :invoices="preinvoiceCandidates"
      :can-operate="canOperateFinance"
      @workflow="openWorkflow"
      @detail="openOrderDetail"
    />
    <InvoiceTable
      mode="final"
      title="待最终总开票"
      subtitle="总经理终审通过后进入这里，最终总开票完成后订单办结。"
      :invoices="pendingInvoices"
      :can-operate="canOperateFinance"
      @workflow="openWorkflow"
      @detail="openOrderDetail"
    />
    <InvoiceTable
      mode="history"
      title="已开票记录"
      subtitle="统一追溯预开票、最终总开票、金额和回款状态。"
      :invoices="issuedInvoices"
      :can-operate="canOperateFinance"
      @workflow="openWorkflow"
      @detail="openOrderDetail"
    />

    <el-dialog
      v-model="dialogVisible"
      class="action-dialog"
      :title="actionMeta.title"
      width="min(960px, 94vw)"
    >
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="开票关联订单信息" />
      <div v-if="activeInvoice" class="action-dialog-context mt-16">
        <div><strong>{{ activeInvoice.order_no }}</strong><span>{{ activeInvoice.customer }} · {{ activeInvoice.project_name }}</span></div>
        <div class="action-dialog-step"><span>流程影响</span><strong>{{ actionMeta.stage }}</strong><small>{{ actionMeta.impact }}</small></div>
      </div>
      <el-alert
        v-if="activeInvoice"
        class="mt-16"
        :title="activeInvoice.invoice_stage_label"
        :description="`订单金额 ${activeInvoice.order_total} 元，已开 ${activeInvoice.invoiced_total} 元，剩余 ${activeInvoice.remaining_amount} 元。${activeInvoice.experiment_result_status}`"
        :type="activeAction === 'invoice_create' ? 'success' : 'info'"
        :closable="false"
        show-icon
      />
      <el-divider content-position="left">本次财务操作</el-divider>
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'preinvoice_create' || activeAction === 'invoice_create'">
          <el-form-item label="发票号"><el-input v-model="form.invoice_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="开票金额">
            <el-input
              v-model="form.invoice_amount"
              type="number"
              :readonly="activeAction === 'invoice_create'"
            />
            <el-text v-if="activeAction === 'invoice_create'" type="info" size="small">
              最终总开票须一次性开完全部剩余金额
            </el-text>
          </el-form-item>
          <el-form-item label="发票类型"><el-input v-model="form.invoice_type" /></el-form-item>
          <el-form-item label="开票日期"><el-date-picker v-model="form.invoice_date" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        </template>
        <el-form-item v-if="activeAction === 'invoice_void'" label="作废原因">
          <el-input v-model="form.void_reason" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item v-else label="回款状态">
          <el-select v-model="form.pay_status">
            <el-option label="未收款" :value="0" />
            <el-option label="已回款" :value="1" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitWorkflow">{{ actionMeta.button }}</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="财务核对订单信息" />
    </el-drawer>
  </div>
</template>
