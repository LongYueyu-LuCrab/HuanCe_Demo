<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import InvoiceTable from '../components/InvoiceTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { exportFinanceOrders, fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { InvoiceItem, OrderItem, PaymentOrderItem } from '../types'

const session = useSession()
const preinvoiceCandidates = computed(() => session.state.dashboard?.finance?.preinvoice_candidates ?? [])
const pendingInvoices = computed(() => session.state.dashboard?.finance?.pending_invoices ?? [])
const issuedInvoices = computed(() => session.state.dashboard?.finance?.issued_invoices ?? [])
const paymentOrders = computed(() => session.state.dashboard?.finance?.payment_orders ?? [])
const canOperateFinance = computed(() => Boolean(session.state.user?.roles?.includes('会计')))
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeInvoice = ref<InvoiceItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const paymentDialogVisible = ref(false)
const paymentDetailVisible = ref(false)
const paymentSubmitting = ref(false)
const exportingOrders = ref(false)
const activePaymentOrder = ref<PaymentOrderItem | null>(null)
const form = reactive({
  invoice_no: '',
  invoice_amount: '',
  invoice_type: '增值税专票',
  invoice_date: '',
  pay_status: 0,
  void_reason: '',
  payment_amount: '',
  payment_date: '',
  payment_remark: '',
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

function openPayment(order: PaymentOrderItem) {
  activePaymentOrder.value = order
  Object.assign(form, { payment_amount: '', payment_date: '', payment_remark: '' })
  paymentDialogVisible.value = true
}

function openPaymentDetails(order: PaymentOrderItem) {
  activePaymentOrder.value = order
  paymentDetailVisible.value = true
}

async function submitPayment() {
  if (!activePaymentOrder.value) return
  const amount = Number(form.payment_amount)
  if (!Number.isFinite(amount) || amount <= 0) {
    ElMessage.warning('请填写大于 0 的回款金额')
    return
  }
  if (amount > Number(activePaymentOrder.value.remaining_total)) {
    ElMessage.warning(`本次回款不能超过待回款余额 ${activePaymentOrder.value.remaining_total} 元`)
    return
  }
  if (!form.payment_date) {
    ElMessage.warning('请选择回款时间')
    return
  }
  paymentSubmitting.value = true
  try {
    await workflowAction({
      action: 'payment_create',
      order_no: activePaymentOrder.value.order_no,
      payment_amount: form.payment_amount,
      payment_date: form.payment_date,
      payment_remark: form.payment_remark,
    })
    ElMessage.success('回款已登记，累计金额已更新')
    paymentDialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '回款登记失败')
  } finally {
    paymentSubmitting.value = false
  }
}

async function exportPaymentOrders() {
  exportingOrders.value = true
  try {
    await exportFinanceOrders()
    ElMessage.success('财务订单回款 Excel 已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exportingOrders.value = false
  }
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

    <el-card shadow="never" class="hc-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>订单回款</h2>
            <p>回款不依赖开票，订单任意节点均可登记；同一订单支持多次回款并累计展示。</p>
          </div>
          <el-button type="primary" plain :loading="exportingOrders" @click="exportPaymentOrders">导出财务订单回款</el-button>
        </div>
      </template>
      <el-table :data="paymentOrders" max-height="min(420px, calc(100vh - 320px))" empty-text="暂无可登记回款的订单">
        <el-table-column label="订单 / 客户" min-width="240">
          <template #default="{ row }">
            <div class="cell-main">{{ row.order_no }}</div>
            <div class="cell-sub">{{ row.customer }} · {{ row.project_name || '未填写项目' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单状态" min-width="150">
          <template #default="{ row }">
            <div class="cell-main">{{ row.order_status }}</div>
            <div class="cell-sub">{{ row.payment_status }}</div>
          </template>
        </el-table-column>
        <el-table-column label="金额" min-width="240">
          <template #default="{ row }">
            <div class="cell-main">已回款 {{ row.paid_total }} 元</div>
            <div class="cell-sub">订单 {{ row.order_total }} · 待回款 {{ row.remaining_total }} 元</div>
          </template>
        </el-table-column>
        <el-table-column label="回款笔数" min-width="100" prop="payment_count" />
        <el-table-column label="财务操作" fixed="right" min-width="220">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button v-if="canOperateFinance" size="small" type="primary" plain @click="openPayment(row)">登记回款</el-button>
              <el-button size="small" plain @click="openPaymentDetails(row)">回款细节</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
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

    <el-dialog v-model="paymentDialogVisible" title="登记回款" width="min(620px, 92vw)">
      <div v-if="activePaymentOrder" class="action-dialog-context">
        <div><strong>{{ activePaymentOrder.order_no }}</strong><span>{{ activePaymentOrder.customer }} · {{ activePaymentOrder.project_name }}</span></div>
        <div class="action-dialog-step"><span>当前累计回款</span><strong>{{ activePaymentOrder.paid_total }} 元</strong><small>本次最多可登记 {{ activePaymentOrder.remaining_total }} 元</small></div>
      </div>
      <el-form label-position="top" class="form-grid mt-16">
        <el-form-item label="本次回款金额" required><el-input v-model="form.payment_amount" type="number" placeholder="例如：200000" /></el-form-item>
        <el-form-item label="回款时间" required><el-date-picker v-model="form.payment_date" value-format="YYYY-MM-DD HH:mm:ss" type="datetime" placeholder="请选择实际到账时间" /></el-form-item>
        <el-form-item label="回款备注" class="form-wide"><el-input v-model="form.payment_remark" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="可填写付款方、凭证号等说明" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paymentDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="paymentSubmitting" @click="submitPayment">保存回款</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="paymentDetailVisible" title="回款细节" width="min(760px, 92vw)">
      <div v-if="activePaymentOrder" class="action-dialog-context mb-16">
        <div><strong>{{ activePaymentOrder.order_no }}</strong><span>{{ activePaymentOrder.customer }} · {{ activePaymentOrder.project_name }}</span></div>
        <div class="action-dialog-step"><span>累计回款</span><strong>{{ activePaymentOrder.paid_total }} 元</strong><small>共 {{ activePaymentOrder.payment_count }} 笔，待回款 {{ activePaymentOrder.remaining_total }} 元</small></div>
      </div>
      <el-table v-if="activePaymentOrder?.payments.length" :data="activePaymentOrder.payments" empty-text="暂无回款记录">
        <el-table-column prop="payment_date" label="回款时间" min-width="170" />
        <el-table-column label="回款金额" min-width="140"><template #default="{ row }">{{ row.amount }} 元</template></el-table-column>
        <el-table-column prop="accounting_user" label="登记会计" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="220" />
      </el-table>
      <el-empty v-else description="暂无回款记录" :image-size="64" />
    </el-dialog>
  </div>
</template>
