<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import InvoiceTable from '../components/InvoiceTable.vue'
import { workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { InvoiceItem } from '../types'

const session = useSession()
const pendingInvoices = computed(() => session.state.dashboard?.finance?.pending_invoices ?? [])
const issuedInvoices = computed(() => session.state.dashboard?.finance?.issued_invoices ?? [])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeInvoice = ref<InvoiceItem | null>(null)
const form = reactive({
  invoice_no: '',
  invoice_amount: '',
  invoice_type: '增值税专票',
  invoice_date: '',
  pay_status: 1,
})

function openWorkflow(action: string, invoice: InvoiceItem) {
  activeAction.value = action
  activeInvoice.value = invoice
  Object.assign(form, {
    invoice_no: invoice.invoice_no || '',
    invoice_amount: invoice.invoice_amount || '',
    invoice_type: invoice.invoice_type && invoice.invoice_type !== '待确认' ? invoice.invoice_type : '增值税专票',
    invoice_date: invoice.invoice_date || '',
    pay_status: 1,
  })
  dialogVisible.value = true
}

async function submitWorkflow() {
  if (!activeInvoice.value) return
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      report_no: activeInvoice.value.report_no,
      invoice_no: activeInvoice.value.invoice_no || form.invoice_no,
      invoice_amount: form.invoice_amount,
      invoice_type: form.invoice_type,
      invoice_date: form.invoice_date,
      pay_status: form.pay_status,
    })
    ElMessage.success(activeAction.value === 'invoice_create' ? '开票办结完成' : '回款状态已更新')
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
      pending
      title="待开票订单"
      subtitle="总经理终审通过后进入这里，供会计核对并开票。"
      :invoices="pendingInvoices"
      @workflow="openWorkflow"
    />
    <InvoiceTable
      title="已开票记录"
      subtitle="追溯发票号码、金额、回款状态和流程办结状态。"
      :invoices="issuedInvoices"
      @workflow="openWorkflow"
    />

    <el-dialog v-model="dialogVisible" :title="activeAction === 'invoice_create' ? '开票办结' : '更新回款状态'" width="640px">
      <el-alert v-if="activeInvoice" :title="`${activeInvoice.order_no} / ${activeInvoice.customer}`" type="info" show-icon :closable="false" />
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'invoice_create'">
          <el-form-item label="发票号"><el-input v-model="form.invoice_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="开票金额"><el-input v-model="form.invoice_amount" type="number" /></el-form-item>
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
  </div>
</template>
