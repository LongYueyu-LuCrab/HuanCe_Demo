<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ReportItem } from '../types'

const props = defineProps<{ reports: ReportItem[] }>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredReports = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return props.reports
  return props.reports.filter((report) =>
    [report.report_no, report.order_no, report.customer, report.project_name, report.status, report.conclusion, report.quality_user]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value),
  )
})

const pagedReports = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredReports.value.slice(start, start + pageSize.value)
})
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>报告工作台</h2>
          <p>显示当前角色需要处理或核对的报告。</p>
        </div>
        <el-input v-model="keyword" clearable class="table-search" placeholder="报告号、订单号、客户、状态" @input="page = 1" />
      </div>
    </template>
    <el-table :data="pagedReports" stripe height="520" empty-text="当前没有待处理报告">
      <el-table-column prop="report_no" label="报告号" min-width="170" />
      <el-table-column prop="order_no" label="订单号" min-width="150" />
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" min-width="150">
        <template #default="{ row }"><el-tag effect="plain">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="remake_count" label="重制次数" width="100" />
      <el-table-column prop="quality_user" label="出具人" min-width="120" />
    </el-table>
    <div class="table-footer">
      <span>共 {{ filteredReports.length }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 15, 20]"
        :total="filteredReports.length"
        layout="sizes, prev, pager, next"
        @size-change="page = 1"
      />
    </div>
  </el-card>
</template>
