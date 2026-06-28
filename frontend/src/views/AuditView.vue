<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSession } from '../stores/session'

const session = useSession()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const events = computed(() => session.state.dashboard?.workflow_events ?? [])
const changes = computed(() => session.state.dashboard?.changes ?? [])
const reviews = computed(() => session.state.dashboard?.reviews ?? [])

const filteredEvents = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return events.value
  return events.value.filter((event) =>
    [
      event.order_no,
      event.customer,
      event.project_name,
      event.actor,
      event.event_type,
      event.from_status,
      event.to_status,
      event.note,
      event.create_time,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value),
  )
})

const pagedEvents = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredEvents.value.slice(start, start + pageSize.value)
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
        </div>
      </template>

      <el-table :data="pagedEvents" stripe height="460" empty-text="暂无流程日志">
        <el-table-column prop="create_time" label="时间" min-width="150" />
        <el-table-column prop="order_no" label="订单号" min-width="150" />
        <el-table-column label="客户 / 项目" min-width="300">
          <template #default="{ row }">
            <div class="cell-main">{{ row.customer }}</div>
            <div class="cell-sub">{{ row.project_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="actor" label="操作人" min-width="120" />
        <el-table-column prop="event_type" label="类型" min-width="110" />
        <el-table-column prop="note" label="节点说明" min-width="320" />
      </el-table>

      <div class="table-footer">
        <span>共 {{ filteredEvents.length }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 15, 20]"
          :total="filteredEvents.length"
          layout="sizes, prev, pager, next"
          @size-change="page = 1"
        />
      </div>
    </el-card>

    <div class="split-grid">
      <el-card shadow="never" class="hc-card">
        <template #header><h2>变更回流记录</h2></template>
        <el-table :data="changes" stripe height="320" empty-text="暂无变更单">
          <el-table-column prop="order_no" label="订单号" min-width="140" />
          <el-table-column prop="scene" label="场景" min-width="150" />
          <el-table-column prop="status" label="状态" min-width="130" />
          <el-table-column prop="change_user" label="发起人" min-width="110" />
          <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card shadow="never" class="hc-card">
        <template #header><h2>商务技术评审</h2></template>
        <el-table :data="reviews" stripe height="320" empty-text="暂无评审记录">
          <el-table-column prop="order_no" label="订单号" min-width="140" />
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
