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
  if (activeAction.value !== 'invoice_pay' && (!form.invoice_amount || Number(form.invoice_amount) <= 0)) {
    ElMessage.warning('请填写大于 0 的开票金额')
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
      report_no: activeInvoice.value.report_no,
      invoice_no: activeInvoice.value.invoice_no || form.invoice_no,
      invoice_amount: form.invoice_amount,
      invoice_type: form.invoice_type,
      invoice_date: form.invoice_date,
      pay_status: form.pay_status,
    })
    ElMessage.success(
      activeAction.value === 'preinvoice_create'
        ? '预开票已记录，订单继续流转'
        : activeAction.value === 'invoice_create'
          ? '最终总开票办结完成'
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
      title="可预开票订单"
      subtitle="商务与技术双评审通过后可预开票；全部实验结束后可再次预开票。"
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
      :title="activeAction === 'preinvoice_create' ? '预开票' : activeAction === 'invoice_create' ? '最终总开票' : '更新回款状态'"
      width="min(960px, 94vw)"
    >
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="开票关联订单信息" />
      <el-alert
        v-if="activeInvoice"
        class="mt-16"
        :title="activeInvoice.invoice_stage_label"
        :description="`订单金额 ${activeInvoice.order_total} 元，已开 ${activeInvoice.invoiced_total} 元，剩余 ${activeInvoice.remaining_amount} 元。${activeInvoice.experiment_result_status}`"
        :type="activeAction === 'invoice_create' ? 'success' : 'info'"
        :closable="false"
        show-icon
      />
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
        <el-form-item label="回款状态">
          <el-select v-model="form.pay_status">
            <el-option label="未收款" :value="0" />
            <el-option label="已回款" :value="1" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="财务核对订单信息" />
    </el-drawer>
  </div>
</template>
