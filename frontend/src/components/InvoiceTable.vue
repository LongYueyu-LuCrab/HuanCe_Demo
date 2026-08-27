<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InvoiceItem } from '../types'
import OutsourceBadge from './OutsourceBadge.vue'

const props = defineProps<{
  invoices: InvoiceItem[]
  title: string
  subtitle: string
  mode: 'preinvoice' | 'final' | 'history'
  canOperate?: boolean
}>()
const emit = defineEmits<{
  workflow: [action: string, invoice: InvoiceItem]
  detail: [invoice: InvoiceItem]
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
      invoice.invoice_stage_label,
      invoice.order_total,
      invoice.invoiced_total,
      invoice.remaining_amount,
      invoice.invoice_type,
      invoice.invoice_date,
      invoice.pay_status,
      invoice.finish_status,
      invoice.finance_user,
      invoice.experiment_result_status,
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
      <el-table-column :label="mode === 'history' ? '发票 / 订单' : '订单 / 报告'" min-width="210">
        <template #default="{ row }">
          <div v-if="mode === 'history'" class="cell-main">{{ row.invoice_no }}</div>
          <div :class="['order-reference', mode === 'history' ? 'cell-sub' : 'cell-main']">
            <span>{{ row.order_no }}</span>
            <OutsourceBadge :visible="row.is_outsource" />
          </div>
          <div v-if="mode !== 'history'" class="cell-sub">{{ row.report_no || '暂未生成报告' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="开票阶段" min-width="190">
        <template #default="{ row }">
          <el-tag :type="row.invoice_stage === 'final' ? 'success' : 'warning'" effect="plain">{{ row.invoice_stage_label }}</el-tag>
          <div class="cell-sub mt-8">{{ row.experiment_result_status }}</div>
        </template>
      </el-table-column>
      <el-table-column label="金额" min-width="210">
        <template #default="{ row }">
          <div class="cell-main">{{ mode === 'history' ? row.invoice_amount : row.remaining_amount }}</div>
          <div class="cell-sub">订单 {{ row.order_total }} · 已开 {{ row.invoiced_total }} · 余额 {{ row.remaining_amount }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="190">
        <template #default="{ row }">
          <el-tag :type="row.pay_status.includes('已') ? 'success' : 'warning'" effect="plain">{{ row.pay_status }}</el-tag>
          <div class="cell-sub">{{ row.finish_status }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_date" label="开票日期" min-width="120" />
      <el-table-column prop="finance_user" label="操作人" min-width="120" />
      <el-table-column label="订单信息 / 财务操作" fixed="right" min-width="210">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" plain @click="emit('detail', row)">订单详情</el-button>
            <el-button v-if="canOperate && mode === 'preinvoice'" size="small" type="warning" plain @click="emit('workflow', 'preinvoice_create', row)">预开票</el-button>
            <el-button v-if="canOperate && mode === 'final'" size="small" type="primary" plain @click="emit('workflow', 'invoice_create', row)">最终总开票</el-button>
            <el-button v-if="canOperate && mode === 'history'" size="small" type="success" plain @click="emit('workflow', 'invoice_pay', row)">更新回款</el-button>
          </div>
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
