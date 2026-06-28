<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ReportItem, User } from '../types'

const props = defineProps<{ reports: ReportItem[]; user?: User }>()
const emit = defineEmits<{
  workflow: [action: string, report: ReportItem]
}>()

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

const roleSet = computed(() => new Set(props.user?.roles || []))
const isChairman = computed(() => Boolean(props.user?.is_chairman))

function hasRole(role: string) {
  return isChairman.value || roleSet.value.has(role)
}

function actionsFor(report: ReportItem) {
  const actions: Array<{ key: string; label: string; type?: 'primary' | 'danger' | 'success' }> = []
  if (report.status_key === 2 && hasRole('销售')) {
    actions.push({ key: 'report_sales_pass', label: '初审通过', type: 'success' })
    actions.push({ key: 'report_sales_reject', label: '初审驳回', type: 'danger' })
  }
  if (report.status_key === 3 && hasRole('总经理')) {
    actions.push({ key: 'report_gm_pass', label: '终审通过', type: 'success' })
    actions.push({ key: 'report_gm_reject', label: '终审驳回', type: 'danger' })
  }
  return actions
}
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
      <el-table-column label="审核操作" fixed="right" min-width="190">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button
              v-for="action in actionsFor(row)"
              :key="action.key"
              size="small"
              :type="action.type || 'primary'"
              plain
              @click="emit('workflow', action.key, row)"
            >
              {{ action.label }}
            </el-button>
            <span v-if="actionsFor(row).length === 0" class="cell-sub">无可操作</span>
          </div>
        </template>
      </el-table-column>
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
