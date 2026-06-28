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
</script>

<template>
  <div class="page-stack">
    <section class="command-panel">
      <div>
        <p class="panel-kicker">ROLE WORKBENCH</p>
        <h2>{{ roleText }}工作台</h2>
        <p>聚焦当前岗位的待办、订单状态和关键风险，敏感模块已按角色隔离。</p>
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

    <OrderTable :orders="orders" :title="`${selectedLabel}明细`" subtitle="点击订单行查看客户、报价、交付、试验需求和当前流程状态。" />
  </div>
</template>
