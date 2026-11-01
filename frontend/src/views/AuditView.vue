<script setup lang="ts">
import { computed, ref } from 'vue'
import OutsourceBadge from '../components/OutsourceBadge.vue'
import { useSession } from '../stores/session'

const session = useSession()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const actorFilter = ref('')
const dateFilter = ref('')

const events = computed(() => session.state.dashboard?.workflow_events ?? [])
const changes = computed(() => session.state.dashboard?.changes ?? [])
const reviews = computed(() => session.state.dashboard?.reviews ?? [])

const filteredEvents = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  return events.value.filter((event) => {
    const matchesKeyword = !value || [
      event.order_no,
      event.customer,
      event.project_name,
      event.actor,
      event.event_type,
      event.from_status,
      event.to_status,
      event.note,
      event.action_code,
      event.change_summary,
      event.create_time,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value)
    return matchesKeyword && (!actorFilter.value || event.actor === actorFilter.value) && (!dateFilter.value || event.create_time.startsWith(dateFilter.value))
  })
})

const actors = computed(() => [...new Set(events.value.map((event) => event.actor).filter(Boolean))])

function exportAudit() {
  const header = '订单号,操作人,事件类型,原状态,新状态,说明,时间'
  const rows = filteredEvents.value.map((event) => [event.order_no, event.actor, event.event_type, event.from_status, event.to_status, event.note, event.create_time]
    .map((value) => `"${String(value || '').replaceAll('"', '""')}"`).join(','))
  const blob = new Blob([`\ufeff${[header, ...rows].join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `LIMS流程日志-${new Date().toISOString().slice(0, 10)}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}

const auditGroups = computed(() => {
  const groups = new Map<string, { order_no: string; customer: string; project_name: string; is_outsource: boolean; events: typeof filteredEvents.value }>()
  for (const event of filteredEvents.value) {
    if (!groups.has(event.order_no)) {
      groups.set(event.order_no, { order_no: event.order_no, customer: event.customer, project_name: event.project_name, is_outsource: event.is_outsource, events: [] })
    }
    groups.get(event.order_no)?.events.push(event)
  }
  return [...groups.values()]
})

const pagedAuditGroups = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return auditGroups.value.slice(start, start + pageSize.value)
})
</script>

<template>
  <div class="page-stack">
    <div class="metric-strip compact">
      <el-card shadow="never" class="metric-card">
        <span>评审记录</span>
        <strong>{{ reviews.length }}</strong>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <span>变更单</span>
        <strong>{{ changes.length }}</strong>
      </el-card>
      <el-card shadow="never" class="metric-card">
        <span>流程日志</span>
        <strong>{{ events.length }}</strong>
      </el-card>
    </div>

    <el-card shadow="never" class="hc-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>流程日志</h2>
            <p>按当前角色权限展示订单评审、变更回流、报告审核和开票办结等关键节点记录。</p>
          </div>
          <el-input
            v-model="keyword"
            clearable
            class="table-search"
            placeholder="搜索订单、客户、操作人、节点说明"
            @input="page = 1"
          />
          <el-select v-model="actorFilter" clearable placeholder="操作人" class="table-search" @change="page = 1">
            <el-option v-for="actor in actors" :key="actor" :label="actor" :value="actor" />
          </el-select>
          <el-input v-model="dateFilter" clearable placeholder="日期 YYYY-MM-DD" class="table-search" @input="page = 1" />
          <el-button plain @click="exportAudit">导出当前结果</el-button>
        </div>
      </template>

      <div v-if="pagedAuditGroups.length" class="audit-timeline-grid">
        <article v-for="group in pagedAuditGroups" :key="group.order_no" class="audit-timeline-card">
          <header>
            <div><span class="order-reference"><strong>{{ group.order_no }}</strong><OutsourceBadge :visible="group.is_outsource" /></span><p>{{ group.customer }} · {{ group.project_name }}</p></div>
            <span>{{ group.events.length }} 条记录</span>
          </header>
          <ol class="audit-timeline">
            <li v-for="event in group.events.slice(0, 6)" :key="`${event.order_no}-${event.create_time}-${event.action_code}`">
              <span class="audit-timeline-dot"></span>
              <div><div class="audit-event-head"><strong>{{ event.to_status || event.event_type }}</strong><time>{{ event.create_time }}</time></div><p>{{ event.note }}</p><small>{{ event.actor }}<template v-if="event.change_summary"> · {{ event.change_summary }}</template></small></div>
            </li>
          </ol>
          <span v-if="group.events.length > 6" class="cell-sub">还有 {{ group.events.length - 6 }} 条历史记录</span>
        </article>
      </div>
      <el-empty v-else description="暂无流程日志" :image-size="64" />

      <div class="table-footer">
        <span>共 {{ auditGroups.length }} 个订单</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 15, 20]"
          :total="auditGroups.length"
          layout="sizes, prev, pager, next"
          @size-change="page = 1"
        />
      </div>
    </el-card>

    <div class="split-grid">
      <el-card shadow="never" class="hc-card">
        <template #header><h2>变更回流记录</h2></template>
        <el-table :data="changes" height="320" empty-text="暂无变更单">
          <el-table-column prop="order_no" label="订单号" min-width="155">
            <template #default="{ row }">
              <span class="order-reference">
                <span>{{ row.order_no }}</span>
                <OutsourceBadge :visible="row.is_outsource" />
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="scene" label="场景" min-width="150" />
          <el-table-column prop="status" label="状态" min-width="130" />
          <el-table-column prop="change_user" label="发起人" min-width="110" />
          <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card shadow="never" class="hc-card">
        <template #header><h2>商务技术评审</h2></template>
        <el-table :data="reviews" height="320" empty-text="暂无评审记录">
          <el-table-column prop="order_no" label="订单号" min-width="155">
            <template #default="{ row }">
              <span class="order-reference">
                <span>{{ row.order_no }}</span>
                <OutsourceBadge :visible="row.is_outsource" />
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="结果" min-width="90" />
          <el-table-column prop="tech_feasible" label="技术" min-width="90" />
          <el-table-column prop="biz_user" label="商务" min-width="110" />
          <el-table-column prop="tech_user" label="技术评审" min-width="110" />
          <el-table-column prop="reject_reason" label="驳回原因" min-width="240" show-overflow-tooltip />
        </el-table>
      </el-card>
    </div>
  </div>
</template>
