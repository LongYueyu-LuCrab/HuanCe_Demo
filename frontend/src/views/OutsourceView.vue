<script setup lang="ts">
import { computed } from 'vue'
import OrderTable from '../components/OrderTable.vue'
import { useSession } from '../stores/session'

const session = useSession()
const orders = computed(() => session.state.dashboard?.outsource_orders ?? [])
</script>

<template>
  <OrderTable title="委外试验订单" subtitle="展示分配给外部委托实验室的订单。" :orders="orders" />
</template>
