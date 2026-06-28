<script setup lang="ts">
import { computed } from 'vue'
import InvoiceTable from '../components/InvoiceTable.vue'
import { useSession } from '../stores/session'

const session = useSession()
const pendingInvoices = computed(() => session.state.dashboard?.finance?.pending_invoices ?? [])
const issuedInvoices = computed(() => session.state.dashboard?.finance?.issued_invoices ?? [])
</script>

<template>
  <div class="page-stack">
    <InvoiceTable
      pending
      title="待开票订单"
      subtitle="总经理终审通过后进入这里，供会计核对并开票。"
      :invoices="pendingInvoices"
    />
    <InvoiceTable
      title="已开票记录"
      subtitle="追溯发票号码、金额、回款状态和流程办结状态。"
      :invoices="issuedInvoices"
    />
  </div>
</template>
