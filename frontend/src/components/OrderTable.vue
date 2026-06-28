<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OrderItem } from '../types'

const props = defineProps<{
  orders: OrderItem[]
  title?: string
  subtitle?: string
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
