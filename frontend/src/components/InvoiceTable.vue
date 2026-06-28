<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InvoiceItem } from '../types'

const props = defineProps<{
  invoices: InvoiceItem[]
  title: string
  subtitle: string
  pending?: boolean
}>()
const emit = defineEmits<{
  workflow: [action: string, invoice: InvoiceItem]
}>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredInvoices = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return props.invoices
  return props.invoices.filter((invoice) =>
    [
      invoice.invoice_no,
      invoice.order_no,
      invoice.report_no,
      invoice.customer,
      invoice.project_name,
      invoice.invoice_amount,
      invoice.invoice_type,
      invoice.invoice_date,
      invoice.pay_status,
      invoice.finish_status,
      invoice.finance_user,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value),
  )
})

const pagedInvoices = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredInvoices.value.slice(start, start + pageSize.value)
})
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>{{ title }}</h2>
          <p>{{ subtitle }}</p>
        </div>
        <el-input v-model="keyword" clearable class="table-search" placeholder="发票号、订单号、客户、项目" @input="page = 1" />
      </div>
    </template>
    <el-table :data="pagedInvoices" stripe height="360" empty-text="暂无匹配记录">
      <el-table-column :label="pending ? '订单 / 报告' : '发票 / 订单'" min-width="210">
        <template #default="{ row }">
          <div class="cell-main">{{ pending ? row.order_no : row.invoice_no }}</div>
          <div class="cell-sub">{{ row.report_no || row.order_no }}</div>
        </template>
      </el-table-column>
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_amount" label="金额" min-width="120" />
      <el-table-column label="状态" min-width="190">
        <template #default="{ row }">
          <el-tag :type="row.pay_status.includes('已') ? 'success' : 'warning'" effect="plain">{{ row.pay_status }}</el-tag>
          <div class="cell-sub">{{ row.finish_status }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_date" label="开票日期" min-width="120" />
      <el-table-column prop="finance_user" label="操作人" min-width="120" />
      <el-table-column label="财务操作" fixed="right" min-width="150">
        <template #default="{ row }">
          <el-button v-if="pending" size="small" type="primary" plain @click="emit('workflow', 'invoice_create', row)">开票办结</el-button>
          <el-button v-else size="small" type="success" plain @click="emit('workflow', 'invoice_pay', row)">更新回款</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="table-footer">
      <span>共 {{ filteredInvoices.length }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 15, 20]"
        :total="filteredInvoices.length"
        layout="sizes, prev, pager, next"
        @size-change="page = 1"
      />
    </div>
  </el-card>
</template>
