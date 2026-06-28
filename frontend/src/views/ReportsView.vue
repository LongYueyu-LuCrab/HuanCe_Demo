<script setup lang="ts">
import { computed } from 'vue'
import ReportList from '../components/ReportList.vue'
import { useSession } from '../stores/session'

const session = useSession()
const reports = computed(() => session.state.dashboard?.pending_reports ?? [])
</script>

<template>
  <ReportList :reports="reports" />
</template>
