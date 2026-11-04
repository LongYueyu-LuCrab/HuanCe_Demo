<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

type Option = { value: string | number; label: string }
type FilterState = {
  keyword?: string
  order_status?: string
  schedule_status?: string
  device_id?: string
  execution_attribute?: string
  sales_user?: string
  urgent?: string
  start_date?: string
  end_date?: string
  create_from?: string
  create_to?: string
  delivery_from?: string
  delivery_to?: string
  sort?: string
}

const props = defineProps<{
  kind: 'orders' | 'lab'
  modelValue?: FilterState
  options?: {
    statuses?: Option[]
    schedule_statuses?: Option[]
    devices?: Option[]
    execution_attributes?: Option[]
    sales?: Option[]
    urgent?: boolean
  }
}>()
const emit = defineEmits<{ 'update:modelValue': [value: FilterState]; apply: [value: FilterState]; reset: [] }>()
const visible = ref(false)
const draft = reactive<FilterState>({ ...(props.modelValue || {}) })
watch(() => props.modelValue, (value) => Object.assign(draft, value || {}), { deep: true })
const options = computed(() => props.options || {})
const activeCount = computed(() => Object.values(props.modelValue || {}).filter(Boolean).length)

function apply() {
  const value = Object.fromEntries(Object.entries(draft).filter(([, item]) => item !== undefined && item !== ''))
  emit('update:modelValue', value)
  emit('apply', value)
  visible.value = false
}
function reset() {
  Object.keys(draft).forEach((key) => delete draft[key as keyof FilterState])
  emit('update:modelValue', {})
  emit('reset')
  visible.value = false
}
</script>

<template>
  <div class="advanced-filter">
    <el-button class="advanced-filter-trigger" plain @click="visible = true">
      <span class="filter-trigger-icon">☷</span>
      高级筛选
      <el-badge v-if="activeCount" :value="activeCount" class="filter-count" />
    </el-button>
    <el-drawer v-model="visible" title="高级筛选" size="min(420px, 92vw)" append-to-body>
      <div class="filter-drawer-intro">筛选条件仅来自当前角色可见的订单，可组合使用。</div>
      <el-form label-position="top" class="advanced-filter-form">
        <el-form-item label="关键词">
          <el-input v-model="draft.keyword" clearable placeholder="订单号、客户、项目、销售" />
        </el-form-item>
        <el-form-item label="订单状态" v-if="options.statuses?.length">
          <el-select v-model="draft.order_status" clearable filterable placeholder="全部状态">
            <el-option v-for="item in options.statuses" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="排期状态" v-if="kind === 'lab' && options.schedule_statuses?.length">
          <el-select v-model="draft.schedule_status" clearable filterable placeholder="全部排期状态">
            <el-option v-for="item in options.schedule_statuses" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行属性" v-if="kind === 'orders' && options.execution_attributes?.length">
          <el-select v-model="draft.execution_attribute" clearable placeholder="全部执行属性">
            <el-option v-for="item in options.execution_attributes" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="销售人员" v-if="kind === 'orders' && options.sales?.length > 1">
          <el-select v-model="draft.sales_user" clearable filterable placeholder="全部销售">
            <el-option v-for="item in options.sales" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="试验设备" v-if="kind === 'lab' && options.devices?.length">
          <el-select v-model="draft.device_id" clearable filterable placeholder="全部设备">
            <el-option v-for="item in options.devices" :key="item.value" :label="item.label" :value="String(item.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单日期" v-if="kind === 'orders'">
          <el-date-picker :model-value="draft.create_from && draft.create_to ? [draft.create_from, draft.create_to] : null" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" @change="(value: string[] | null) => { draft.create_from = value?.[0] || ''; draft.create_to = value?.[1] || '' }" />
        </el-form-item>
        <el-form-item label="交付日期" v-if="kind === 'orders'">
          <el-date-picker :model-value="draft.delivery_from && draft.delivery_to ? [draft.delivery_from, draft.delivery_to] : null" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" @change="(value: string[] | null) => { draft.delivery_from = value?.[0] || ''; draft.delivery_to = value?.[1] || '' }" />
        </el-form-item>
        <el-form-item label="计划日期" v-if="kind === 'lab'">
          <el-date-picker :model-value="draft.start_date && draft.end_date ? [draft.start_date, draft.end_date] : null" type="daterange" value-format="YYYY-MM-DD" start-placeholder="计划开始" end-placeholder="计划结束" @change="(value: string[] | null) => { draft.start_date = value?.[0] || ''; draft.end_date = value?.[1] || '' }" />
        </el-form-item>
        <el-form-item label="排序方式">
          <el-select v-model="draft.sort" clearable placeholder="默认排序">
            <el-option label="最新创建" value="created_desc" />
            <el-option v-if="kind === 'orders'" label="预计交付最早" value="delivery_asc" />
            <el-option v-if="kind === 'orders'" label="预计交付最晚" value="delivery_desc" />
            <el-option v-if="kind === 'orders'" label="报价金额最高" value="amount_desc" />
          </el-select>
        </el-form-item>
        <el-form-item label="加急订单" v-if="kind === 'orders' && options.urgent">
          <el-select v-model="draft.urgent" clearable placeholder="全部订单"><el-option label="仅加急" value="1" /><el-option label="仅普通" value="0" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="filter-drawer-actions"><el-button @click="reset">重置</el-button><el-button type="primary" @click="apply">应用筛选</el-button></div>
      </template>
    </el-drawer>
  </div>
</template>
