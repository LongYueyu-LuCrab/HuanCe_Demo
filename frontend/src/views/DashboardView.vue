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

const visibleOrders = computed(() => {
  const groups = session.state.dashboard?.order_groups || {}
  const source = Object.values(groups).flat()
  return [...new Map(source.map((order) => [order.order_no, order])).values()]
})

const riskOrders = computed(() => visibleOrders.value.filter((order) => {
  const overdue = Boolean(order.expected_delivery_date && order.expected_delivery_date < new Date().toISOString().slice(0, 10) && !['已开票办结', '退单'].includes(order.status))
  return order.is_urgent || overdue || order.status === '评审驳回'
}).slice(0, 6))

const riskCounts = computed(() => ({
  urgent: visibleOrders.value.filter((order) => order.is_urgent).length,
  overdue: visibleOrders.value.filter((order) => Boolean(order.expected_delivery_date && order.expected_delivery_date < new Date().toISOString().slice(0, 10) && !['已开票办结', '退单'].includes(order.status))).length,
  rejected: visibleOrders.value.filter((order) => order.status === '评审驳回').length,
}))

function priorityReason(order: (typeof priorityOrders.value)[number]) {
  if (order.is_urgent) return '加急订单，需要优先推进'
  if (order.expected_delivery_date) return `交付日期 ${order.expected_delivery_date}`
  return '等待当前流程节点处理'
}

function riskReason(order: (typeof riskOrders.value)[number]) {
  if (order.is_urgent) return '加急订单'
  if (order.status === '评审驳回') return '评审驳回，等待修改或退单'
  return `已超过预计交付 ${order.expected_delivery_date}`
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

    <section class="risk-workbench" aria-labelledby="risk-title">
      <div class="risk-workbench-heading">
        <div><span>交付风险</span><h3 id="risk-title">先处理可能影响交付的订单</h3></div>
        <strong>{{ riskOrders.length }} 条需要关注</strong>
      </div>
      <div class="risk-counts">
        <div><strong>{{ riskCounts.urgent }}</strong><span>加急订单</span></div>
        <div><strong>{{ riskCounts.overdue }}</strong><span>超过预计交付</span></div>
        <div><strong>{{ riskCounts.rejected }}</strong><span>评审驳回</span></div>
      </div>
      <div v-if="riskOrders.length" class="risk-list">
        <article v-for="order in riskOrders" :key="order.order_no">
          <div><strong>{{ order.order_no }}</strong><span>{{ order.customer }} · {{ order.status }}</span></div>
          <small>{{ riskReason(order) }}</small>
        </article>
      </div>
      <div v-else class="risk-empty">当前没有识别到加急、逾期或评审驳回订单。</div>
    </section>

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
