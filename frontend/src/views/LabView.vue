<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchAvailableDevices, fetchLaboratoryOrders, fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { LabDevice, OrderItem, ScheduleItem } from '../types'

const route = useRoute()
const session = useSession()
const labKey = computed(() => (route.params.lab === 'jiangyin' ? 'jiangyin' : 'suzhou'))
const lab = computed(() => session.state.dashboard?.labs?.[labKey.value])
const labType = computed(() => labKey.value === 'jiangyin' ? 2 : 1)
const labOrders = ref<ScheduleItem[]>([])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeOrderNo = ref('')
const activeSchedule = ref<ScheduleItem | null>(null)
const activeOrder = ref<OrderItem | null>(null)
const orderLoading = ref(false)
const detailDrawerVisible = ref(false)
const availabilityLoading = ref(false)
const availableDevices = ref<LabDevice[]>([])
const form = reactive({
  change_scene: 2,
  change_content: '',
  new_test_demand: '',
  test_item_list: '',
  device_id: undefined as number | undefined,
  test_raw_data: '',
  test_conclusion_temp: '',
  plan_start_time: '',
  plan_end_time: '',
  outsource_factory: '',
  outsource_price: '',
  outsource_cycle: '',
  sample_name: '',
  sample_spec: '',
  sample_count: 1,
  storage_condition: '常温',
  test_start_time: '',
  test_end_time: '',
  report_no: '',
  final_conclusion: '',
})

async function loadLaboratoryOrders() {
  try {
    const data = await fetchLaboratoryOrders({ lab_type: labType.value, page: 1, page_size: 500 })
    labOrders.value = data.items
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '实验室订单读取失败')
  }
}

watch(labType, loadLaboratoryOrders, { immediate: true })
async function loadOrderContext(orderNo: string) {
  activeOrder.value = null
  orderLoading.value = true
  try {
    activeOrder.value = await fetchOrderDetail(orderNo)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    orderLoading.value = false
  }
}

function openOrderDetail(schedule: ScheduleItem) {
  detailDrawerVisible.value = true
  void loadOrderContext(schedule.order_no)
}

function openWorkflow(action: string, schedule: ScheduleItem) {
  activeAction.value = action
  activeSchedule.value = schedule
  activeOrderNo.value = schedule.order_no
  availableDevices.value = []
  Object.assign(form, {
    change_scene: 2,
    change_content: '',
    new_test_demand: '',
    test_item_list: schedule.remark || schedule.project_name,
    device_id: schedule.device_id || undefined,
    test_raw_data: '',
    test_conclusion_temp: '',
    plan_start_time: schedule.start_time || '',
    plan_end_time: schedule.end_time || '',
    outsource_factory: '',
    outsource_price: '',
    outsource_cycle: '',
    sample_name: `${schedule.project_name} 样品`,
    sample_spec: '客户送检样品',
    sample_count: 1,
    storage_condition: '常温',
    test_start_time: '',
    test_end_time: '',
    report_no: '',
    final_conclusion: '',
  })
  dialogVisible.value = true
  void loadOrderContext(schedule.order_no)
  if ((action === 'schedule_assign' || action === 'process_change') && schedule.start_time && schedule.end_time && !schedule.test_type.includes('委外')) {
    void queryAvailableDevices()
  }
}

async function queryAvailableDevices() {
  if (!activeSchedule.value || !form.plan_start_time || !form.plan_end_time) {
    ElMessage.warning('请先选择计划开始和结束日期')
    return
  }
  availabilityLoading.value = true
  try {
    availableDevices.value = await fetchAvailableDevices(activeSchedule.value.id, form.plan_start_time, form.plan_end_time)
    const selected = availableDevices.value.find((item) => item.id === form.device_id)
    if (selected && !selected.available) form.device_id = undefined
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '设备可用性查询失败')
  } finally {
    availabilityLoading.value = false
  }
}

function resetDeviceSelection() {
  availableDevices.value = []
  form.device_id = undefined
}

async function submitWorkflow() {
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrderNo.value,
      schedule_id: activeSchedule.value?.id,
      ...form,
      test_item_list: activeSchedule.value?.remark || form.test_item_list,
    })
    ElMessage.success('试验节点操作已完成')
    dialogVisible.value = false
    await session.refreshDashboard()
    await loadLaboratoryOrders()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>{{ lab?.name }}</h2>
        <p>上半部分显示设备状态和未来排期，下半部分筛选本实验室订单。</p>
      </div>
    </div>

    <div class="device-grid">
      <el-card v-for="device in lab?.devices ?? []" :key="device.name" shadow="never" class="device-card">
        <div class="device-head">
          <h3>{{ device.name }}</h3>
          <el-tag :type="device.status === '实验中' || device.status === '设备正常' ? 'success' : device.status === '维修中' ? 'warning' : 'danger'" effect="plain">{{ device.status }}</el-tag>
        </div>
        <p v-if="device.order_no" class="device-current">
          {{ device.order_no }} / {{ device.project_name }}
        </p>
        <p v-else class="device-current muted">当前无执行订单</p>
        <p class="cell-sub">预计结束：{{ device.end_time || '暂无' }}</p>
        <el-divider />
        <ul class="future-list">
          <li v-for="future in device.future_orders" :key="future.order_no">
            <span>{{ future.order_no }}</span>
            <small>{{ future.start_time || '待排' }} - {{ future.end_time || '待定' }}</small>
          </li>
          <li v-if="device.future_orders.length === 0" class="muted">暂无未来排期</li>
        </ul>
      </el-card>
    </div>

    <ScheduleTable
      :orders="labOrders"
      :user="session.state.user"
      :lab-type="labType"
      exportable
      @workflow="openWorkflow"
      @detail="openOrderDetail"
    />

    <el-dialog v-model="dialogVisible" title="实验室任务操作" width="min(960px, 94vw)">
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="试验任务订单信息" />
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'schedule_assign' || activeAction === 'process_change'">
          <el-form-item :label="activeAction === 'process_change' ? '调整后开始' : '计划开始'">
            <el-date-picker v-model="form.plan_start_time" value-format="YYYY-MM-DD" type="date" @change="resetDeviceSelection" />
          </el-form-item>
          <el-form-item :label="activeAction === 'process_change' ? '调整后结束' : '计划结束'">
            <el-date-picker v-model="form.plan_end_time" value-format="YYYY-MM-DD" type="date" @change="resetDeviceSelection" />
          </el-form-item>
          <template v-if="activeSchedule?.test_type.includes('委外') && activeAction === 'schedule_assign'">
            <el-form-item label="委外厂家"><el-input v-model="form.outsource_factory" /></el-form-item>
            <el-form-item label="委外价格"><el-input v-model="form.outsource_price" type="number" /></el-form-item>
            <el-form-item label="委外周期/天"><el-input v-model="form.outsource_cycle" type="number" /></el-form-item>
          </template>
          <template v-else-if="!activeSchedule?.test_type.includes('委外')">
            <el-form-item label="查询设备可用性">
              <el-button :loading="availabilityLoading" plain @click="queryAvailableDevices">查询所选日期的可用设备</el-button>
            </el-form-item>
            <el-form-item label="试验设备">
              <el-select v-model="form.device_id" filterable placeholder="请先查询，再选择设备">
                <el-option
                  v-for="device in availableDevices"
                  :key="device.id"
                  :label="`${device.device_code} · ${device.name}${device.available ? '' : `（${device.unavailable_reason}）`}`"
                  :value="device.id"
                  :disabled="!device.available"
                />
              </el-select>
            </el-form-item>
          </template>
        </template>
        <template v-else-if="activeAction === 'register_sample'">
          <el-form-item label="样品名称"><el-input v-model="form.sample_name" /></el-form-item>
          <el-form-item label="规格型号"><el-input v-model="form.sample_spec" /></el-form-item>
          <el-form-item label="数量"><el-input v-model="form.sample_count" type="number" /></el-form-item>
          <el-form-item label="存储条件"><el-input v-model="form.storage_condition" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide">
            <el-input v-model="form.test_item_list" disabled type="textarea" :rows="3" />
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'submit_test'">
          <el-form-item label="原始检测数据" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="临时结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'outsource_result'">
          <el-form-item label="委外开始"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外完成"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="回传原始数据" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="委外结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="form.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="最终结论" class="form-wide"><el-input v-model="form.final_conclusion" type="textarea" :rows="4" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'create_change'">
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="form.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="form.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="实验室订单信息" />
    </el-drawer>

  </div>
</template>
