<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportLaboratoryOrders } from '../services/api'
import type { ScheduleItem, User } from '../types'

const props = defineProps<{
  orders: ScheduleItem[]
  user?: User
  labType?: number
  exportable?: boolean
}>()
const emit = defineEmits<{
  workflow: [action: string, schedule: ScheduleItem]
  detail: [schedule: ScheduleItem]
}>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const orderStatus = ref<number | ''>('')
const scheduleStatus = ref<number | ''>('')
const deviceId = ref<number | ''>('')
const dateRange = ref<[string, string] | []>([])
const selectedRows = ref<ScheduleItem[]>([])
const exporting = ref(false)

const orderStatusOptions = computed(() => Array.from(new Map(props.orders.map((item) => [item.status_key, item.status])).entries()))
const scheduleStatusOptions = computed(() => Array.from(new Map(props.orders.map((item) => [item.schedule_status_key, item.schedule_status])).entries()))
const deviceOptions = computed(() => Array.from(new Map(props.orders.filter((item) => item.device_id).map((item) => [item.device_id as number, `${item.device_code} · ${item.device_name}`])).entries()))

const filteredOrders = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  return props.orders.filter((order) => {
    const matchesKeyword = !value || [order.order_no, order.customer, order.project_name, order.status, order.test_type, order.schedule_status, order.device_code, order.device_name, order.remark]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value)
    const matchesOrderStatus = orderStatus.value === '' || order.status_key === orderStatus.value
    const matchesScheduleStatus = scheduleStatus.value === '' || order.schedule_status_key === scheduleStatus.value
    const matchesDevice = deviceId.value === '' || order.device_id === deviceId.value
    const matchesDate = dateRange.value.length !== 2 || (
      (!order.end_time || order.end_time >= dateRange.value[0])
      && (!order.start_time || order.start_time <= dateRange.value[1])
    )
    return matchesKeyword && matchesOrderStatus && matchesScheduleStatus && matchesDevice && matchesDate
  })
})

const pagedOrders = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredOrders.value.slice(start, start + pageSize.value)
})

const roleSet = computed(() => new Set(props.user?.roles || []))
const isChairman = computed(() => Boolean(props.user?.is_chairman))
const canLabOperate = computed(() => isChairman.value || roleSet.value.has('苏州实验室') || roleSet.value.has('江阴实验室') || roleSet.value.has('实验操作员'))
const canIssueReport = computed(() => isChairman.value || roleSet.value.has('苏州实验室') || roleSet.value.has('江阴实验室'))

function resetPage() {
  page.value = 1
}

function resultTagType(result: string): 'success' | 'danger' | 'warning' | 'info' {
  if (result === 'pass') return 'success'
  if (result === 'fail') return 'danger'
  if (result === 'abnormal') return 'warning'
  return 'info'
}

function handleSelection(rows: ScheduleItem[]) {
  selectedRows.value = rows
}

async function exportOrders(selectedOnly: boolean) {
  if (!props.labType) return
  if (selectedOnly && selectedRows.value.length === 0) {
    ElMessage.warning('请先勾选需要导出的订单')
    return
  }
  exporting.value = true
  try {
    await exportLaboratoryOrders({
      lab_type: props.labType,
      keyword: keyword.value,
      order_status: orderStatus.value === '' ? '' : String(orderStatus.value),
      schedule_status: scheduleStatus.value === '' ? '' : String(scheduleStatus.value),
      device_id: deviceId.value === '' ? '' : String(deviceId.value),
      start_date: dateRange.value[0] || '',
      end_date: dateRange.value[1] || '',
      schedule_ids: selectedOnly ? selectedRows.value.map((item) => item.id) : undefined,
    })
    ElMessage.success('Excel 已生成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>实验室订单筛选</h2>
          <p>筛选本实验室内执行过或排期中的订单。</p>
        </div>
        <div v-if="exportable" class="row-actions">
          <el-button :loading="exporting" plain @click="exportOrders(true)">导出已选</el-button>
          <el-button :loading="exporting" type="primary" plain @click="exportOrders(false)">按条件导出 Excel</el-button>
        </div>
      </div>
    </template>
    <div class="schedule-filter-bar">
      <el-input v-model="keyword" clearable placeholder="搜索订单号、客户、项目、任务、设备" @input="resetPage" />
      <el-select v-model="orderStatus" clearable placeholder="订单状态" @change="resetPage">
        <el-option v-for="item in orderStatusOptions" :key="item[0]" :label="item[1]" :value="item[0]" />
      </el-select>
      <el-select v-model="scheduleStatus" clearable placeholder="排期状态" @change="resetPage">
        <el-option v-for="item in scheduleStatusOptions" :key="item[0]" :label="item[1]" :value="item[0]" />
      </el-select>
      <el-select v-model="deviceId" clearable filterable placeholder="试验设备" @change="resetPage">
        <el-option v-for="item in deviceOptions" :key="item[0]" :label="item[1]" :value="item[0]" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="计划开始"
        end-placeholder="计划结束"
        @change="resetPage"
      />
    </div>
    <el-table :data="pagedOrders" stripe height="420" empty-text="暂无匹配任务" @selection-change="handleSelection">
      <el-table-column v-if="exportable" type="selection" width="48" />
      <el-table-column prop="order_no" label="订单号" min-width="150" />
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="任务" min-width="180" />
      <el-table-column label="试验设备" min-width="160">
        <template #default="{ row }">
          <div v-if="row.device_name" class="cell-main">{{ row.device_name }}</div>
          <div class="cell-sub">{{ row.device_code || (row.test_type.includes('委外') ? '委外任务' : '待排台') }}</div>
        </template>
      </el-table-column>
      <el-table-column label="排期" min-width="190">
        <template #default="{ row }">{{ row.start_time || '待排' }} - {{ row.end_time || '待定' }}</template>
      </el-table-column>
      <el-table-column label="样品流转" min-width="235">
        <template #default="{ row }">
          <div class="sample-time-line"><span>预入库</span>{{ row.expected_sample_arrival || '待确认' }}</div>
          <div class="sample-time-line"><span>实入库</span>{{ row.sample_arrived_at || '尚未入库' }}</div>
          <div class="sample-time-line"><span>出库</span>{{ row.sample_outbound_at || '尚未出库' }}</div>
          <div v-if="row.sample_photos.length" class="sample-photo-links">
            <a v-for="photo in row.sample_photos" :key="photo.id" :href="photo.url" target="_blank">{{ photo.name }}</a>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="170">
        <template #default="{ row }">
          <el-tag effect="plain">{{ row.status }}</el-tag>
          <span class="cell-sub block">{{ row.schedule_status }}</span>
          <el-tag class="mt-8" size="small" :type="row.sample_arrived ? 'success' : 'warning'" effect="plain">
            {{ row.sample_arrival_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="实验结果" min-width="220">
        <template #default="{ row }">
          <template v-if="row.experiment_status">
            <div class="row-actions">
              <el-tag size="small" effect="plain">{{ row.experiment_status }}</el-tag>
              <el-tag v-if="row.experiment_result" size="small" :type="resultTagType(row.experiment_result_key)">
                {{ row.experiment_result }}
              </el-tag>
            </div>
            <div v-if="row.experiment_ended_at" class="cell-sub mt-8">结束：{{ row.experiment_ended_at }}</div>
            <div v-if="row.experiment_operator" class="cell-sub">操作：{{ row.experiment_operator }}</div>
            <div v-if="row.experiment_conclusion" class="cell-sub">结论：{{ row.experiment_conclusion }}</div>
          </template>
          <span v-else class="cell-sub">尚未开始</span>
        </template>
      </el-table-column>
      <el-table-column label="订单信息 / 试验操作" fixed="right" min-width="300">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" plain @click="emit('detail', row)">订单详情</el-button>
            <template v-if="canLabOperate">
              <template v-if="row.workflow_version === 2">
                <el-button v-if="(row.status_key === 3 || row.status_key === 4) && ![4, 5].includes(row.schedule_status_key)" size="small" type="primary" plain @click="emit('workflow', 'schedule_assign', row)">排期 / 排台</el-button>
                <el-button v-if="row.schedule_status.includes('变更')" size="small" type="warning" plain @click="emit('workflow', 'process_change', row)">处理变更</el-button>
                <template v-if="row.test_type.includes('委外')">
                  <el-button v-if="!row.experiment_status.includes('结束') && !row.experiment_status.includes('提交')" size="small" type="success" plain @click="emit('workflow', 'outsource_result', row)">委外回传 / 结束实验</el-button>
                </template>
                <template v-else>
                  <el-button v-if="row.sample_arrived && row.device_id && !row.experiment_status" size="small" type="primary" plain @click="emit('workflow', 'start_test', row)">开始试验</el-button>
                  <el-button v-if="row.experiment_status.includes('试验中')" size="small" type="warning" plain @click="emit('workflow', 'end_test', row)">实验结束</el-button>
                </template>
                <el-button v-if="row.experiment_status.includes('待提交结果')" size="small" type="success" plain @click="emit('workflow', 'submit_test', row)">提交结果</el-button>
                <el-button v-if="row.sample_arrived && [4, 5].includes(row.schedule_status_key) && !row.sample_outbound_at" size="small" plain @click="emit('workflow', 'sample_outbound', row)">样品出库</el-button>
                <el-button v-if="row.is_lead && canIssueReport && (row.status_key === 8 || row.status_key === 5)" size="small" type="primary" plain @click="emit('workflow', 'issue_report', row)">汇总出报告</el-button>
              </template>
              <template v-else>
                <el-button v-if="!row.experiment_status" size="small" type="primary" plain @click="emit('workflow', 'start_test', row)">开始试验</el-button>
                <el-button v-if="row.experiment_status.includes('试验中')" size="small" type="warning" plain @click="emit('workflow', 'end_test', row)">实验结束</el-button>
                <el-button v-if="row.experiment_status.includes('待提交结果')" size="small" type="success" plain @click="emit('workflow', 'submit_test', row)">提交结果</el-button>
              </template>
              <el-button v-if="row.status_key === 4 && (!row.experiment_status || row.experiment_status.includes('试验中'))" size="small" type="warning" plain @click="emit('workflow', 'create_change', row)">试验中变更</el-button>
            </template>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <div class="table-footer">
      <span>共 {{ filteredOrders.length }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 15, 20]"
        :total="filteredOrders.length"
        layout="sizes, prev, pager, next"
        @size-change="page = 1"
      />
    </div>
  </el-card>
</template>
