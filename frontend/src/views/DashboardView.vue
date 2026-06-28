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
const activeOrders = computed(() => session.state.dashboard?.metrics?.active_orders ?? 0)
const runningExperiments = computed(() => session.state.dashboard?.metrics?.running_experiments ?? 0)
const pendingReports = computed(() => session.state.dashboard?.metrics?.pending_reports ?? 0)
const changeRequests = computed(() => session.state.dashboard?.metrics?.change_requests ?? 0)
const commandSignals = computed(() => [
  { label: '进行中', value: activeOrders.value, tone: 'primary' },
  { label: '试验执行', value: runningExperiments.value, tone: 'success' },
  { label: '报告待办', value: pendingReports.value, tone: 'warning' },
  { label: '变更闭环', value: changeRequests.value, tone: 'danger' },
])
const flowSteps = ['下单', '评审', '排期', '样品', '试验', '报告', '开票']
</script>

<template>
  <div class="page-stack">
    <section class="command-panel">
      <div>
        <p class="panel-kicker">ROLE WORKBENCH</p>
        <h2>{{ roleText }}工作台</h2>
        <p>聚焦当前岗位的待办、订单状态和关键风险，敏感模块已按角色隔离。</p>
      </div>
      <div class="signal-grid">
        <div v-for="signal in commandSignals" :key="signal.label" :class="['signal-card', signal.tone]">
          <span>{{ signal.label }}</span>
          <strong>{{ signal.value }}</strong>
        </div>
      </div>
    </section>

    <div class="metric-grid">
      <el-card
        v-for="card in cards"
        :key="`${card.key}-${card.label}`"
        shadow="never"
        :class="['metric-card', { active: selectedKey === card.key }]"
        @click="activeMetric = card.key"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
      </el-card>
    </div>

    <section class="workflow-strip">
      <div v-for="(step, index) in flowSteps" :key="step" class="flow-node">
        <i>{{ String(index + 1).padStart(2, '0') }}</i>
        <span>{{ step }}</span>
      </div>
    </section>

    <OrderTable :orders="orders" :title="`${selectedLabel}明细`" subtitle="点击订单行查看客户、报价、交付、试验需求和当前流程状态。" />
  </div>
</template>
