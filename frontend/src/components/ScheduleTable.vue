<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ScheduleItem, User } from '../types'

const props = defineProps<{
  orders: ScheduleItem[]
  user?: User
}>()
const emit = defineEmits<{
  workflow: [action: string, schedule: ScheduleItem]
  detail: [schedule: ScheduleItem]
}>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredOrders = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return props.orders
  return props.orders.filter((order) =>
    [order.order_no, order.customer, order.project_name, order.status, order.test_type, order.schedule_status, order.device_code, order.device_name, order.remark]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value),
  )
})

const pagedOrders = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredOrders.value.slice(start, start + pageSize.value)
})

const roleSet = computed(() => new Set(props.user?.roles || []))
const isChairman = computed(() => Boolean(props.user?.is_chairman))
const canLabOperate = computed(() => isChairman.value || roleSet.value.has('苏州实验室') || roleSet.value.has('江阴实验室'))
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>实验室订单筛选</h2>
          <p>筛选本实验室内执行过或排期中的订单。</p>
        </div>
        <el-input v-model="keyword" clearable class="table-search" placeholder="订单号、客户、项目、状态" @input="page = 1" />
      </div>
    </template>
    <el-table :data="pagedOrders" stripe height="420" empty-text="暂无匹配任务">
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
      <el-table-column label="状态" min-width="170">
        <template #default="{ row }">
          <el-tag effect="plain">{{ row.status }}</el-tag>
          <span class="cell-sub block">{{ row.schedule_status }}</span>
        </template>
      </el-table-column>
      <el-table-column label="订单信息 / 试验操作" fixed="right" min-width="300">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" plain @click="emit('detail', row)">订单详情</el-button>
            <template v-if="canLabOperate">
              <template v-if="row.workflow_version === 2">
                <el-button size="small" type="primary" plain @click="emit('workflow', 'schedule_assign', row)">排期 / 排台</el-button>
                <el-button v-if="row.schedule_status.includes('变更')" size="small" type="warning" plain @click="emit('workflow', 'process_change', row)">处理变更</el-button>
                <el-button v-if="!row.sample_registered" size="small" type="success" plain @click="emit('workflow', 'register_sample', row)">登记样品</el-button>
                <el-button v-if="row.test_type.includes('委外')" size="small" type="success" plain @click="emit('workflow', 'outsource_result', row)">委外回传</el-button>
                <template v-else>
                  <el-button v-if="row.sample_registered && row.device_id && !row.experiment_status" size="small" type="primary" plain @click="emit('workflow', 'start_test', row)">开始试验</el-button>
                  <el-button v-if="row.experiment_status.includes('试验中')" size="small" type="success" plain @click="emit('workflow', 'submit_test', row)">提交结果</el-button>
                </template>
                <el-button v-if="row.is_lead" size="small" type="primary" plain @click="emit('workflow', 'issue_report', row)">汇总出报告</el-button>
              </template>
              <template v-else>
                <el-button size="small" type="primary" plain @click="emit('workflow', 'start_test', row)">开始试验</el-button>
                <el-button size="small" type="success" plain @click="emit('workflow', 'submit_test', row)">提交结果</el-button>
              </template>
              <el-button size="small" type="warning" plain @click="emit('workflow', 'create_change', row)">试验中变更</el-button>
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
