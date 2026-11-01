<script setup lang="ts">
import { computed, ref } from 'vue'
import { getMetricCards } from '../permissions'
import OrderTable from '../components/OrderTable.vue'
import { useSession } from '../stores/session'

const session = useSession()
const activeMetric = ref('')

const cards = computed(() => getMetricCards(session.state.user, session.state.dashboard))
const selectedKey = computed(() => activeMetric.value || cards.value[0]?.key || 'orders')
const orders = computed(() => session.state.dashboard?.order_groups?.[selectedKey.value] ?? [])
const selectedLabel = computed(() => cards.value.find((card) => card.key === selectedKey.value)?.label || '相关订单')
const roleText = computed(() => session.state.user.roles?.join(' / ') || '普通用户')
const priorityOrders = computed(() => {
  const source = session.state.dashboard?.recent_orders ?? orders.value
  const unique = new Map(source.map((order) => [order.order_no, order]))
  return [...unique.values()]
    .sort((left, right) => {
      if (left.is_urgent !== right.is_urgent) return left.is_urgent ? -1 : 1
      return String(left.expected_delivery_date || '').localeCompare(String(right.expected_delivery_date || ''))
    })
    .slice(0, 5)
})

function priorityReason(order: (typeof priorityOrders.value)[number]) {
  if (order.is_urgent) return '加急订单，需要优先推进'
  if (order.expected_delivery_date) return `交付日期 ${order.expected_delivery_date}`
  return '等待当前流程节点处理'
}
</script>

<template>
  <div class="page-stack">
    <section class="command-panel">
      <div>
        <p class="dashboard-context">{{ roleText }} · 今日工作台</p>
        <h2>今天要推进哪些工作？</h2>
        <p>从待处理订单到报告交付，先处理当前岗位最紧急的任务。</p>
      </div>
    </section>

    <div class="metric-grid">
      <el-card
        v-for="card in cards"
        :key="`${card.key}-${card.label}`"
        shadow="never"
        :class="['metric-card', { active: selectedKey === card.key }]"
        role="button"
        tabindex="0"
        :aria-pressed="selectedKey === card.key"
        @click="activeMetric = card.key"
        @keydown.enter.prevent="activeMetric = card.key"
        @keydown.space.prevent="activeMetric = card.key"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
      </el-card>
    </div>

    <div class="workbench-grid">
      <OrderTable :orders="orders" :title="`${selectedLabel}明细`" subtitle="点击订单行查看客户、报价、交付、试验需求和当前流程状态。" />

      <aside class="priority-panel" aria-labelledby="priority-title">
        <div class="priority-panel-heading">
          <div>
            <p class="priority-label">优先关注</p>
            <h3 id="priority-title">先处理这些订单</h3>
          </div>
          <span>{{ priorityOrders.length }} 条</span>
        </div>
        <div v-if="priorityOrders.length" class="priority-list">
          <article v-for="order in priorityOrders" :key="order.order_no" class="priority-item">
            <div class="priority-item-topline">
              <strong>{{ order.order_no }}</strong>
              <span v-if="order.is_urgent" class="priority-urgent">加急</span>
            </div>
            <p>{{ order.customer }} · {{ order.status }}</p>
            <small>{{ priorityReason(order) }}</small>
          </article>
        </div>
        <div v-else class="priority-empty">
          <strong>暂无优先订单</strong>
          <span>当前岗位没有需要额外关注的订单。</span>
        </div>
      </aside>
    </div>
  </div>
</template>
