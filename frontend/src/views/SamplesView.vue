<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import OutsourceBadge from '../components/OutsourceBadge.vue'
import { fetchOrderDetail } from '../services/api'
import { useSession } from '../stores/session'
import type { OrderItem, SampleItem } from '../types'

const session = useSession()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const drawerVisible = ref(false)
const orderLoading = ref(false)
const selectedOrder = ref<OrderItem | null>(null)

const samples = computed(() => session.state.dashboard?.samples ?? [])

const filteredSamples = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return samples.value
  return samples.value.filter((sample) =>
    [
      sample.sample_no,
      sample.order_no,
      sample.customer,
      sample.project_name,
      sample.sample_name,
      sample.sample_spec,
      sample.storage_condition,
      sample.sample_status,
      sample.test_type,
      sample.quality_user,
      sample.expected_arrive_time,
      sample.actual_arrive_time,
      sample.outbound_time,
      sample.outbound_by,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(value),
  )
})

const pagedSamples = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredSamples.value.slice(start, start + pageSize.value)
})

function sampleStage(sample: SampleItem) {
  if (sample.outbound_time) return { key: 'outbound', label: '已出库' }
  if (sample.actual_arrive_time) return { key: 'inbound', label: '已入库' }
  return { key: 'expected', label: '等待到样' }
}

const sampleQueue = computed(() => ({
  total: filteredSamples.value.length,
  waiting: filteredSamples.value.filter((sample) => !sample.actual_arrive_time).length,
  stored: filteredSamples.value.filter((sample) => Boolean(sample.actual_arrive_time && !sample.outbound_time)).length,
  outbound: filteredSamples.value.filter((sample) => Boolean(sample.outbound_time)).length,
  missingPhoto: filteredSamples.value.filter((sample) => Boolean(sample.actual_arrive_time && !sample.photos.length)).length,
}))

async function openOrderDetail(sample: SampleItem) {
  drawerVisible.value = true
  selectedOrder.value = null
  orderLoading.value = true
  try {
    selectedOrder.value = await fetchOrderDetail(sample.order_no)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    orderLoading.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <el-card shadow="never" class="hc-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>样品台账</h2>
            <p>追踪样品预入库、实际入库、入库照片和出库信息。</p>
          </div>
          <el-input
            v-model="keyword"
            clearable
            class="table-search"
            placeholder="搜索样品编号、订单、客户、状态"
            @input="page = 1"
          />
        </div>
      </template>

      <div class="sample-queue-strip" aria-label="样品流转摘要">
        <div><strong>{{ sampleQueue.total }}</strong><span>全部样品</span></div>
        <div><strong>{{ sampleQueue.waiting }}</strong><span>等待到样</span></div>
        <div><strong>{{ sampleQueue.stored }}</strong><span>已入库</span></div>
        <div><strong>{{ sampleQueue.outbound }}</strong><span>已出库</span></div>
        <div class="is-warning"><strong>{{ sampleQueue.missingPhoto }}</strong><span>缺少入库照片</span></div>
      </div>

      <el-table :data="pagedSamples" height="540" empty-text="暂无样品记录">
        <el-table-column prop="sample_no" label="样品编号" min-width="150" />
        <el-table-column label="订单 / 客户" min-width="280">
          <template #default="{ row }">
            <div class="order-reference cell-main">
              <span>{{ row.order_no }}</span>
              <OutsourceBadge :visible="row.is_outsource" />
            </div>
            <div class="cell-sub">{{ row.customer }}</div>
          </template>
        </el-table-column>
        <el-table-column label="样品信息" min-width="300">
          <template #default="{ row }">
            <div class="cell-main">{{ row.sample_name }}</div>
            <div class="cell-sub">{{ row.sample_spec || row.project_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="sample_count" label="数量" width="90" />
        <el-table-column prop="storage_condition" label="存储条件" min-width="130" />
        <el-table-column prop="test_type" label="路径" min-width="150" />
        <el-table-column label="状态" min-width="140">
          <template #default="{ row }">
            <div class="sample-stage-line" :class="`is-${sampleStage(row).key}`"><span class="task-state-dot"></span><strong>{{ sampleStage(row).label }}</strong></div>
            <el-tag effect="plain">{{ row.sample_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="流转轨迹" min-width="300">
          <template #default="{ row }">
            <div class="sample-lifecycle-rail">
              <span :class="{ 'is-done': row.expected_arrive_time }">预计到样</span>
              <span :class="{ 'is-done': row.actual_arrive_time }">入库</span>
              <span :class="{ 'is-done': row.actual_arrive_time }">实验使用</span>
              <span :class="{ 'is-done': row.outbound_time }">出库</span>
            </div>
            <div class="cell-sub">{{ row.actual_arrive_time || row.expected_arrive_time || '时间待确认' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="expected_arrive_time" label="预入库时间" min-width="150" />
        <el-table-column prop="actual_arrive_time" label="实际入库时间" min-width="150" />
        <el-table-column label="入库照片" min-width="170">
          <template #default="{ row }">
            <div v-if="row.photos.length" class="sample-photo-links">
              <a v-for="photo in row.photos" :key="photo.id" :href="photo.url" target="_blank">{{ photo.name }}</a>
            </div>
            <span v-else class="cell-sub">暂无照片</span>
          </template>
        </el-table-column>
        <el-table-column label="出库信息" min-width="180">
          <template #default="{ row }">
            <div>{{ row.outbound_time || '尚未出库' }}</div>
            <div v-if="row.outbound_by" class="cell-sub">操作人：{{ row.outbound_by }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="quality_user" label="入库登记人" min-width="120" />
        <el-table-column label="订单信息" fixed="right" width="110">
          <template #default="{ row }">
            <el-button size="small" plain @click="openOrderDetail(row)">订单详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <span>共 {{ filteredSamples.length }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 15, 20]"
          :total="filteredSamples.length"
          layout="sizes, prev, pager, next"
          @size-change="page = 1"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" title="订单详情" size="min(720px, 94vw)">
      <OrderSnapshot :order="selectedOrder" :loading="orderLoading" title="样品关联订单信息" />
    </el-drawer>
  </div>
</template>
