<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import { useRoute } from 'vue-router'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import OutsourceBadge from '../components/OutsourceBadge.vue'
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
const samplePhotoFiles = ref<UploadUserFile[]>([])
const form = reactive({
  change_scene: 2,
  change_content: '',
  new_test_demand: '',
  test_item_list: '',
  device_id: undefined as number | undefined,
  test_raw_data: '',
  test_conclusion_temp: '',
  result_status: '',
  plan_start_time: '',
  plan_end_time: '',
  outsource_factory: '',
  outsource_price: '',
  outsource_cycle: '',
  sample_arrived: false,
  test_start_time: '',
  test_end_time: '',
  report_no: '',
  report_type: 'formal',
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
    result_status: '',
    plan_start_time: schedule.start_time || '',
    plan_end_time: schedule.end_time || '',
    outsource_factory: '',
    outsource_price: '',
    outsource_cycle: '',
    sample_arrived: schedule.sample_arrived,
    test_start_time: '',
    test_end_time: '',
    report_no: '',
    report_type: 'formal',
    final_conclusion: '',
  })
  dialogVisible.value = true
  samplePhotoFiles.value = []
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
  if ((activeAction.value === 'end_test' || activeAction.value === 'outsource_result') && !form.result_status) {
    ElMessage.warning('请选择实验结果')
    return
  }
  if ((activeAction.value === 'schedule_assign' || activeAction.value === 'process_change')
    && form.sample_arrived && (activeSchedule.value?.sample_photos.length || 0) === 0 && samplePhotoFiles.value.length === 0) {
    ElMessage.warning('选择“样品已到”时必须上传至少一张样品照片')
    return
  }
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrderNo.value,
      schedule_id: activeSchedule.value?.id,
      ...form,
      test_item_list: activeSchedule.value?.remark || form.test_item_list,
      sample_photos: samplePhotoFiles.value.map((item) => item.raw).filter((file): file is File => Boolean(file)),
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
        <p v-if="device.order_no" class="device-current order-reference">
          <span>{{ device.order_no }} / {{ device.project_name }}</span>
          <OutsourceBadge :visible="device.is_outsource" />
        </p>
        <p v-else class="device-current muted">当前无执行订单</p>
        <p class="cell-sub">预计结束：{{ device.end_time || '暂无' }}</p>
        <el-divider />
        <ul class="future-list">
          <li v-for="future in device.future_orders" :key="future.order_no">
            <span class="order-reference">
              <span>{{ future.order_no }}</span>
              <OutsourceBadge :visible="future.is_outsource" />
            </span>
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
          <el-form-item label="样品到样状态">
            <el-radio-group v-model="form.sample_arrived">
              <el-radio-button :value="false">样品未到</el-radio-button>
              <el-radio-button :value="true">样品已到</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.sample_arrived" label="样品照片" class="form-wide">
            <el-upload v-model:file-list="samplePhotoFiles" :auto-upload="false" multiple accept=".jpg,.jpeg,.png">
              <el-button plain>上传样品图片</el-button>
              <template #tip><div class="el-upload__tip">支持 JPG、PNG，单张不超过 10MB，本次合计不超过 30MB。</div></template>
            </el-upload>
            <div v-if="activeSchedule?.sample_photos.length" class="document-list mt-8">
              <a v-for="photo in activeSchedule.sample_photos" :key="photo.id" :href="photo.url" target="_blank" class="document-link">{{ photo.name }}</a>
            </div>
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide">
            <el-input v-model="form.test_item_list" disabled type="textarea" :rows="3" />
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'end_test'">
          <el-form-item label="实验结果" class="form-wide" required>
            <el-radio-group v-model="form.result_status">
              <el-radio-button value="pass">合格</el-radio-button>
              <el-radio-button value="fail">不合格</el-radio-button>
              <el-radio-button value="abnormal">异常</el-radio-button>
              <el-radio-button value="retest">待复测</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="原始检测数据" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="实验结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
          <el-alert class="form-wide" title="本操作只结束实验并保存结果，不会进入报告流程" type="info" :closable="false" description="实验结束后，请复核数据并再次点击“提交结果”。" show-icon />
        </template>
        <template v-else-if="activeAction === 'submit_test'">
          <el-alert
            class="form-wide"
            title="确认正式提交实验结果"
            type="warning"
            :closable="false"
            description="提交后结果将计入订单完成判断；全部执行路径都提交后，订单才进入待出报告。"
            show-icon
          />
        </template>
        <template v-else-if="activeAction === 'sample_outbound'">
          <el-alert
            class="form-wide"
            title="确认办理样品出库"
            type="warning"
            :closable="false"
            description="提交后将使用服务器当前时间作为出库时间，并记录当前操作账号。"
            show-icon
          />
        </template>
        <template v-else-if="activeAction === 'outsource_result'">
          <el-form-item label="委外开始"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="委外完成"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="实验结果" class="form-wide" required>
            <el-radio-group v-model="form.result_status">
              <el-radio-button value="pass">合格</el-radio-button>
              <el-radio-button value="fail">不合格</el-radio-button>
              <el-radio-button value="abnormal">异常</el-radio-button>
              <el-radio-button value="retest">待复测</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="回传原始数据" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="委外结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
          <el-alert class="form-wide" title="回传后仍需点击“提交结果”" type="info" :closable="false" show-icon />
        </template>
        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="form.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="报告版本" class="form-wide">
            <el-radio-group v-model="form.report_type">
              <el-radio-button value="formal">正式版</el-radio-button>
              <el-radio-button value="draft">草稿版</el-radio-button>
              <el-radio-button value="data_only">仅数据</el-radio-button>
            </el-radio-group>
            <div class="field-help">
              正式版带“示例章 / DEMO”占位水印；草稿版无水印；仅数据版只保留委托、实验与原始数据。
            </div>
          </el-form-item>
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
