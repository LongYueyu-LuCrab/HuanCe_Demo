<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OrderItem, User } from '../types'

const props = defineProps<{
  orders: OrderItem[]
  title?: string
  subtitle?: string
  user?: User
}>()

const emit = defineEmits<{
  workflow: [action: string, order: OrderItem]
}>()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const selectedOrder = ref<OrderItem | null>(null)
const drawerVisible = ref(false)

const filteredOrders = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return props.orders
  return props.orders.filter((order) =>
    [
      order.order_no,
      order.customer,
      order.contact,
      order.phone,
      order.project_name,
      order.test_demand,
      order.status,
      order.execution_mode,
      order.expected_delivery_date,
      order.sales_owner,
    ]
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

function resetPage() {
  page.value = 1
}

function openOrder(order: OrderItem) {
  selectedOrder.value = order
  drawerVisible.value = true
}

const roleSet = computed(() => new Set(props.user?.roles || []))
const isChairman = computed(() => Boolean(props.user?.is_chairman))

function hasRole(role: string) {
  return isChairman.value || roleSet.value.has(role)
}

function actionsFor(order: OrderItem) {
  const actions: Array<{ key: string; label: string; type?: 'primary' | 'danger' | 'warning' | 'success' }> = []
  if (order.status_key === 1 && (hasRole('商务') || hasRole('技术'))) {
    actions.push({ key: 'review_pass', label: '评审通过', type: 'success' })
    actions.push({ key: 'review_reject', label: '评审驳回', type: 'danger' })
  }
  if ([1, 2].includes(order.status_key) && hasRole('销售')) {
    actions.push({ key: 'order_update', label: '修改重提', type: 'primary' })
    actions.push({ key: 'order_cancel', label: '退单', type: 'danger' })
  }
  if (order.status_key === 3 && hasRole('销售')) {
    actions.push({ key: 'sales_confirm', label: '确认无变更', type: 'success' })
    actions.push({ key: 'create_change', label: '填写更改单', type: 'warning' })
  }
  if ([3, 4].includes(order.status_key) && hasRole('质量部')) {
    actions.push({ key: 'schedule_assign', label: '排期分配', type: 'primary' })
    actions.push({ key: 'process_change', label: '处理变更', type: 'warning' })
    actions.push({ key: 'register_sample', label: '样品登记', type: 'success' })
    if (order.execution_mode.includes('委外')) {
      actions.push({ key: 'outsource_result', label: '委外结果回传', type: 'success' })
    }
  }
  if ([4, 5].includes(order.status_key) && hasRole('质量部')) {
    actions.push({ key: 'issue_report', label: '出具报告', type: 'primary' })
  }
  if ([3, 4].includes(order.status_key) && (hasRole('苏州实验室') || hasRole('江阴实验室'))) {
    actions.push({ key: 'start_test', label: '开始试验', type: 'primary' })
    actions.push({ key: 'submit_test', label: '提交结果', type: 'success' })
    actions.push({ key: 'create_change', label: '试验中变更', type: 'warning' })
  }
  return actions
}
</script>

<template>
  <el-card shadow="never" class="hc-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>{{ title || '订单列表' }}</h2>
          <p>{{ subtitle || '按订单号、客户、项目、状态检索，并查看订单详情。' }}</p>
        </div>
        <el-input
          v-model="keyword"
          clearable
          class="table-search"
          placeholder="搜索订单号、客户、项目、状态"
          @input="resetPage"
        />
      </div>
    </template>

    <el-table :data="pagedOrders" stripe height="540" empty-text="暂无匹配订单" @row-click="openOrder">
      <el-table-column prop="order_no" label="订单号" min-width="150">
        <template #default="{ row }">
          <strong>{{ row.order_no }}</strong>
          <el-tag v-if="row.is_urgent" size="small" type="warning" class="ml-8">加急</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="客户 / 项目" min-width="300">
        <template #default="{ row }">
          <div class="cell-main">{{ row.customer }}</div>
          <div class="cell-sub">{{ row.project_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="execution_mode" label="路径" min-width="150" />
      <el-table-column prop="status" label="状态" min-width="130">
        <template #default="{ row }">
          <el-tag effect="plain">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="expected_delivery_date" label="交付" min-width="120" />
      <el-table-column prop="sales_owner" label="销售" min-width="120" />
      <el-table-column label="流程操作" fixed="right" min-width="220">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button
              v-for="action in actionsFor(row)"
              :key="action.key"
              size="small"
              :type="action.type || 'primary'"
              plain
              @click.stop="emit('workflow', action.key, row)"
            >
              {{ action.label }}
            </el-button>
            <span v-if="actionsFor(row).length === 0" class="cell-sub">无可操作</span>
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
        @size-change="resetPage"
      />
    </div>
  </el-card>

  <el-drawer v-model="drawerVisible" title="订单详情" size="520px">
    <el-descriptions v-if="selectedOrder" :column="1" border>
      <el-descriptions-item label="订单号">{{ selectedOrder.order_no }}</el-descriptions-item>
      <el-descriptions-item label="客户">{{ selectedOrder.customer }}</el-descriptions-item>
      <el-descriptions-item label="项目">{{ selectedOrder.project_name }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ selectedOrder.status }}</el-descriptions-item>
      <el-descriptions-item label="执行路径">{{ selectedOrder.execution_mode }}</el-descriptions-item>
      <el-descriptions-item label="销售">{{ selectedOrder.sales_owner || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="报价">{{ selectedOrder.total_quote || '0.00' }}</el-descriptions-item>
      <el-descriptions-item label="交付">{{ selectedOrder.expected_delivery_date || '待确认' }}</el-descriptions-item>
      <el-descriptions-item label="试验需求">{{ selectedOrder.test_demand || '未填写' }}</el-descriptions-item>
    </el-descriptions>
  </el-drawer>
</template>
