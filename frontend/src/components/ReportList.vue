<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ReportItem, User } from '../types'
import OutsourceBadge from './OutsourceBadge.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ reports: ReportItem[]; user?: User }>()
const emit = defineEmits<{
  workflow: [action: string, report: ReportItem]
  detail: [report: ReportItem]
}>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredReports = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return props.reports
  return props.reports.filter((report) =>
    [report.report_no, report.order_no, report.customer, report.project_name, report.status, report.report_type_label, report.conclusion, report.quality_user]
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

const reportQueue = computed(() => ({
  sales: props.reports.filter((report) => report.status_key === 2).length,
  gm: props.reports.filter((report) => report.status_key === 3).length,
  rejected: props.reports.filter((report) => report.status_key === 4).length,
  ready: props.reports.filter((report) => report.status_key === 5 && !report.order_is_closed).length,
}))

const roleSet = computed(() => new Set(props.user?.roles || []))
const isChairman = computed(() => Boolean(props.user?.is_chairman))

function hasRole(role: string) {
  return isChairman.value || roleSet.value.has(role) || (role === '销售' && roleSet.value.has('商务部'))
}

function actionsFor(report: ReportItem) {
  const actions: Array<{ key: string; label: string; type?: 'primary' | 'danger' | 'success' }> = []
  if (report.order_is_closed) return actions
  if (report.status_key === 2 && hasRole('销售')) {
    actions.push({ key: 'start_report_review', label: '开始初审', type: 'primary' })
  }
  if (report.status_key === 3 && hasRole('总经理')) {
    actions.push({ key: 'start_report_review', label: '开始终审', type: 'primary' })
  }
  return actions
}

function downloadReport(report: ReportItem) {
  if (report.download_url) window.location.assign(report.download_url)
}
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>报告工作台</h2>
          <p>显示当前角色可查看的待办与历史报告，PDF 文件可按权限下载。</p>
        </div>
        <el-input v-model="keyword" clearable class="table-search" placeholder="报告号、订单号、客户、状态" @input="page = 1" />
      </div>
      <div class="review-queue-strip" aria-label="报告队列摘要">
        <div><strong>{{ reportQueue.sales }}</strong><span>待销售初审</span></div>
        <div><strong>{{ reportQueue.gm }}</strong><span>待总经理终审</span></div>
        <div class="is-warning"><strong>{{ reportQueue.rejected }}</strong><span>驳回重制</span></div>
        <div><strong>{{ reportQueue.ready }}</strong><span>通过待开票</span></div>
      </div>
    </template>
    <el-table :data="pagedReports" max-height="min(520px, calc(100vh - 320px))" empty-text="当前没有可查看的报告">
      <el-table-column prop="report_no" label="报告号" min-width="170" />
      <el-table-column prop="order_no" label="订单号" min-width="165">
        <template #default="{ row }">
          <span class="order-reference">
            <span>{{ row.order_no }}</span>
            <OutsourceBadge :visible="row.is_outsource" />
          </span>
        </template>
      </el-table-column>
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" min-width="150">
        <template #default="{ row }"><StatusBadge :label="row.status" /></template>
      </el-table-column>
      <el-table-column prop="report_type_label" label="版本" width="100">
        <template #default="{ row }">
          <el-tag :type="row.report_type === 'formal' ? 'danger' : row.report_type === 'data_only' ? 'info' : 'warning'" effect="plain">
            {{ row.report_type_label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remake_count" label="重制次数" width="100" />
      <el-table-column prop="quality_user" label="出具人" min-width="120" />
      <el-table-column label="订单信息 / 审核操作" fixed="right" min-width="260">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" plain @click="emit('detail', row)">订单详情</el-button>
            <el-button v-if="row.has_file" size="small" type="primary" plain @click="downloadReport(row)">下载 PDF</el-button>
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
            <span v-if="actionsFor(row).length === 0 && !row.has_file" class="cell-sub">无可操作</span>
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
