<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSession } from '../stores/session'

const session = useSession()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

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
</script>

<template>
  <div class="page-stack">
    <el-card shadow="never" class="hc-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>样品台账</h2>
            <p>展示质量部已登记的样品编号、规格、存储条件、到货时间和关联订单。</p>
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

      <el-table :data="pagedSamples" stripe height="540" empty-text="暂无样品记录">
        <el-table-column prop="sample_no" label="样品编号" min-width="150" />
        <el-table-column label="订单 / 客户" min-width="280">
          <template #default="{ row }">
            <div class="cell-main">{{ row.order_no }}</div>
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
          <template #default="{ row }"><el-tag effect="plain">{{ row.sample_status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="actual_arrive_time" label="到货" min-width="120" />
        <el-table-column prop="quality_user" label="登记人" min-width="120" />
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
  </div>
</template>
