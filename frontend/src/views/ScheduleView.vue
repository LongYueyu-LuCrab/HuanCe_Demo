<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchAvailableDevices, fetchLaboratoryOrders, fetchOrderDetail, workflowAction, type LabOrderQuery } from '../services/api'
import { useSession } from '../stores/session'
import type { LabDevice, OrderItem, ScheduleItem } from '../types'

const session = useSession()
const isBusinessDept = computed(() => (session.state.user.roles || []).includes('商务部'))
const props = defineProps<{ outsourcedOnly?: boolean }>()
const schedules = ref<ScheduleItem[]>([])
const scheduleTotal = ref(0)
const schedulesLoading = ref(false)
let scheduleQuery: LabOrderQuery = { page: 1, page_size: 10 }
let scheduleRequest = 0
async function loadSchedules(query: LabOrderQuery = scheduleQuery) {
  scheduleQuery = query
  const request = ++scheduleRequest
  schedulesLoading.value = true
  try {
    const data = await fetchLaboratoryOrders({ ...query, scope: 'assigned', test_type: props.outsourcedOnly ? 3 : undefined })
    if (request !== scheduleRequest) return
    schedules.value = data.items
    scheduleTotal.value = data.total
  } catch (error) {
    if (request === scheduleRequest) ElMessage.error(error instanceof Error ? error.message : '排期查询失败')
  } finally {
    if (request === scheduleRequest) schedulesLoading.value = false
  }
}
const drawerVisible = ref(false)
const dialogVisible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const selectedOrder = ref<OrderItem | null>(null)
const activeSchedule = ref<ScheduleItem | null>(null)
const activeAction = ref('')
const availabilityLoading = ref(false)
const availableDevices = ref<LabDevice[]>([])
const samplePhotoFiles = ref<UploadUserFile[]>([])
const availabilityMessage = ref('')
let availabilityRequest = 0
let preferredDeviceId: number | undefined
const form = reactive({
  plan_start_time: '', plan_end_time: '', outsource_factory: '', outsource_price: '', outsource_cycle: '',
  device_id: undefined as number | undefined,
  sample_arrived: false,
  test_item_list: '', test_standard: '', test_raw_data: '', test_conclusion_temp: '', result_status: '',
  test_start_time: '', test_end_time: '', change_scene: 2, new_test_demand: '', change_content: '',
  report_no: '', report_type: 'formal', final_conclusion: '',
})

async function loadOrder(orderNo: string) {
  selectedOrder.value = null
  loading.value = true
  try {
    selectedOrder.value = await fetchOrderDetail(orderNo)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '订单详情读取失败')
  } finally {
    loading.value = false
  }
}

function openOrderDetail(schedule: ScheduleItem) {
  drawerVisible.value = true
  void loadOrder(schedule.order_no)
}

function openWorkflow(action: string, schedule: ScheduleItem) {
  resetDeviceSelection()
  activeAction.value = action
  activeSchedule.value = schedule
  Object.assign(form, {
    plan_start_time: schedule.start_time || '', plan_end_time: schedule.end_time || '',
    device_id: schedule.device_id || undefined,
    sample_arrived: action === 'sample_arrival' ? true : schedule.sample_arrived,
    outsource_factory: '', outsource_price: '', outsource_cycle: '',
    test_item_list: schedule.remark || schedule.project_name,
    test_standard: '', test_raw_data: '', test_conclusion_temp: '', result_status: '', test_start_time: '', test_end_time: '',
    change_scene: 2, new_test_demand: '', change_content: '', report_no: '', report_type: 'formal', final_conclusion: '',
  })
  preferredDeviceId = form.device_id
  dialogVisible.value = true
  void loadOrder(schedule.order_no)
  availableDevices.value = []
  samplePhotoFiles.value = []
  if ((action === 'schedule_assign' || action === 'process_change') && schedule.start_time && schedule.end_time && !schedule.test_type.includes('委外')) {
    void queryAvailableDevices()
  }
}

function resetDeviceSelection() {
  preferredDeviceId = undefined
  availabilityRequest++
  availabilityLoading.value = false
  availabilityMessage.value = ''
  availableDevices.value = []
  form.device_id = undefined
}

async function queryAvailableDevices() {
  if (!activeSchedule.value || !form.plan_start_time || !form.plan_end_time) {
    ElMessage.warning('请先选择计划开始和结束日期')
    return
  }
  if (form.plan_end_time < form.plan_start_time) return false
  const request = ++availabilityRequest
  preferredDeviceId = form.device_id ?? preferredDeviceId
  const candidateId = preferredDeviceId
  availabilityLoading.value = true
  availabilityMessage.value = ''
  try {
    const devices = await fetchAvailableDevices(activeSchedule.value.id, form.plan_start_time, form.plan_end_time)
    if (request !== availabilityRequest) return false
    availableDevices.value = devices
    availabilityMessage.value = devices.length ? `共 ${devices.length} 台设备，${devices.filter((item) => item.available).length} 台可用；不可用原因见设备选项。` : '当前实验室尚未配置设备，请先到设备管理添加设备。'
    const selected = devices.find((item) => item.id === candidateId)
    form.device_id = selected?.available ? selected.id : undefined
    if (candidateId && !selected?.available) {
      availabilityMessage.value += ` 原选设备${selected?.unavailable_reason ? '：' + selected.unavailable_reason : '当前不可用'}，请选择其他可用设备。`
    }
    return true
  } catch (error) {
    if (request !== availabilityRequest) return false
    availableDevices.value = []
    form.device_id = undefined
    availabilityMessage.value = error instanceof Error ? error.message : '设备可用性查询失败'
    ElMessage.error(availabilityMessage.value)
    return false
  } finally {
    if (request === availabilityRequest) availabilityLoading.value = false
  }
}

async function onPlanDatesChange() {
  const candidateId = form.device_id ?? preferredDeviceId
  resetDeviceSelection()
  preferredDeviceId = candidateId
  if (!activeSchedule.value?.test_type.includes('委外') && form.plan_start_time && form.plan_end_time
    && form.plan_end_time >= form.plan_start_time) {
    await queryAvailableDevices()
  }
}

async function submitWorkflow() {
  if (activeAction.value === 'schedule_assign' || activeAction.value === 'process_change') {
    if (!form.plan_start_time || !form.plan_end_time || form.plan_end_time < form.plan_start_time) {
      ElMessage.warning('请填写完整排期，结束日期不能早于开始日期')
      return
    }
    if (!activeSchedule.value?.test_type.includes('委外')) {
      // Revalidate the current dates, including edits committed by this click.
      if (!await queryAvailableDevices()) return
      if (!form.device_id) {
        ElMessage.warning('请选择一台当前日期可用的试验设备')
        return
      }
    }
  }
  if (!activeSchedule.value) return
  if ((activeAction.value === 'end_test' || activeAction.value === 'outsource_result') && !form.result_status) {
    ElMessage.warning('请选择实验结果')
    return
  }
  if ((activeAction.value === 'schedule_assign' || activeAction.value === 'process_change')
    && !isBusinessDept.value && form.sample_arrived && activeSchedule.value.sample_photos.length === 0 && samplePhotoFiles.value.length === 0) {
    ElMessage.warning('选择“样品已到”时必须上传至少一张样品照片')
    return
  }
  if (activeAction.value === 'sample_arrival' && samplePhotoFiles.value.length === 0) {
    ElMessage.warning(activeSchedule.value.sample_arrived ? '请至少上传一张补充样品图片' : '样品入库必须上传至少一张样品图片')
    return
  }
  submitting.value = true
  try {
    await workflowAction({
      action: activeAction.value,
      order_no: activeSchedule.value.order_no,
      schedule_id: activeSchedule.value.id,
      ...form,
      sample_photos: samplePhotoFiles.value.map((item) => item.raw).filter((file): file is File => Boolean(file)),
    })
    ElMessage.success('任务操作已完成')
    dialogVisible.value = false
    await session.refreshDashboard()
    await loadSchedules()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar"><div><h2>{{ outsourcedOnly ? '委外排期与执行' : '排期与任务' }}</h2><p>实验室负责人在这里维护本人负责的内部及委外任务、样品、变更和报告。</p></div></div>
    <ScheduleTable :orders="schedules" :user="session.state.user" remote :total="scheduleTotal" :loading="schedulesLoading" @query="loadSchedules" @detail="openOrderDetail" @workflow="openWorkflow" />

    <el-dialog v-model="dialogVisible" title="实验室任务操作" width="min(960px, 94vw)">
      <p><strong>{{ activeSchedule?.order_no }}</strong> · {{ activeSchedule?.project_name }} · {{ activeSchedule?.remark }}</p>
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'schedule_assign' || activeAction === 'process_change'">
          <el-form-item label="计划开始"><el-date-picker v-model="form.plan_start_time" value-format="YYYY-MM-DD" type="date" @change="onPlanDatesChange" /></el-form-item>
          <el-form-item label="计划结束"><el-date-picker v-model="form.plan_end_time" value-format="YYYY-MM-DD" type="date" @change="onPlanDatesChange" /></el-form-item>
          <template v-if="activeAction === 'schedule_assign' && activeSchedule?.test_type.includes('委外')">
            <el-form-item label="委外厂家"><el-input v-model="form.outsource_factory" /></el-form-item>
            <el-form-item label="委外价格"><el-input v-model="form.outsource_price" type="number" /></el-form-item>
            <el-form-item label="委外周期/天"><el-input v-model="form.outsource_cycle" type="number" /></el-form-item>
          </template>
          <template v-else-if="!activeSchedule?.test_type.includes('委外')">
            <el-form-item label="查询设备可用性"><el-button :loading="availabilityLoading" plain @click="queryAvailableDevices">查询所选日期的可用设备</el-button></el-form-item>
            <el-form-item label="试验设备">
              <el-select v-model="form.device_id" filterable :loading="availabilityLoading" :disabled="availabilityLoading" placeholder="查询后选择可用设备">
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
          <el-alert v-if="availabilityMessage" class="form-wide" :title="availabilityMessage" :closable="false" type="info" />
          <el-form-item v-if="!isBusinessDept" label="样品到样状态">
            <el-radio-group v-model="form.sample_arrived">
              <el-radio-button :value="false">样品未到</el-radio-button>
              <el-radio-button :value="true">样品已到</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="!isBusinessDept && form.sample_arrived" label="样品照片" class="form-wide">
            <el-upload v-model:file-list="samplePhotoFiles" :auto-upload="false" multiple accept=".jpg,.jpeg,.png">
              <el-button plain>上传样品图片</el-button>
              <template #tip><div class="el-upload__tip">支持 JPG、PNG，单张不超过 10MB，本次合计不超过 30MB。</div></template>
            </el-upload>
            <div v-if="activeSchedule?.sample_photos.length" class="document-list mt-8">
              <a v-for="photo in activeSchedule.sample_photos" :key="photo.id" :href="photo.url" target="_blank" class="document-link">{{ photo.name }}</a>
            </div>
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'sample_arrival'">
          <el-alert
            class="form-wide"
            title="确认样品入库"
            type="success"
            :closable="false"
            description="系统将记录实际入库时间、当前操作账号和上传的现场照片。"
            show-icon
          />
          <el-form-item label="样品入库照片" class="form-wide" required>
            <el-upload v-model:file-list="samplePhotoFiles" :auto-upload="false" multiple accept=".jpg,.jpeg,.png">
              <el-button type="primary" plain>上传样品图片</el-button>
              <template #tip><div class="el-upload__tip">支持 JPG、PNG；单张不超过 10MB，本次合计不超过 30MB。</div></template>
            </el-upload>
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide"><el-input v-model="form.test_item_list" disabled type="textarea" :rows="3" /></el-form-item>
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
        <template v-else-if="activeAction === 'end_test' || activeAction === 'outsource_result'">
          <el-form-item v-if="activeAction === 'outsource_result'" label="开始时间"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item v-if="activeAction === 'outsource_result'" label="完成时间"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="实验结果" class="form-wide" required>
            <el-radio-group v-model="form.result_status">
              <el-radio-button value="pass">合格</el-radio-button>
              <el-radio-button value="fail">不合格</el-radio-button>
              <el-radio-button value="abnormal">异常</el-radio-button>
              <el-radio-button value="retest">待复测</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="原始数据 / 回传摘要" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="试验结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
          <el-alert class="form-wide" title="本操作只结束实验并保存结果，之后仍需点击“提交结果”" type="info" :closable="false" show-icon />
        </template>
        <template v-else-if="activeAction === 'submit_test'">
          <el-alert
            class="form-wide"
            title="确认正式提交实验结果"
            type="warning"
            :closable="false"
            description="全部执行路径都提交结果后，订单才会进入待出报告。"
            show-icon
          />
        </template>
        <template v-else-if="activeAction === 'create_change'">
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="form.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="form.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else-if="activeAction === 'issue_report'">
          <el-form-item label="报告编号"><el-input v-model="form.report_no" placeholder="留空自动生成" /></el-form-item>
          <el-form-item label="报告版本" class="form-wide">
            <el-radio-group v-model="form.report_type">
              <el-radio-button value="formal">正式版</el-radio-button>
              <el-radio-button value="draft">草稿版</el-radio-button>
              <el-radio-button value="data_only">仅数据</el-radio-button>
            </el-radio-group>
            <div class="field-help">正式版带示例章占位水印，草稿版无水印，仅数据版聚焦实验数据。</div>
          </el-form-item>
          <el-form-item label="最终结论" class="form-wide"><el-input v-model="form.final_conclusion" type="textarea" :rows="4" /></el-form-item>
        </template>
      </el-form>
      <el-collapse class="mt-16"><el-collapse-item title="查看订单详情与流程" name="context"><OrderSnapshot :order="selectedOrder" :loading="loading" :show-actions="false" title="任务关联订单" /></el-collapse-item></el-collapse>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="submitting" :disabled="availabilityLoading" @click="submitWorkflow">确认提交</el-button></template>
    </el-dialog>

    <el-drawer v-model="drawerVisible" title="订单详情" size="min(720px, 94vw)"><OrderSnapshot :order="selectedOrder" :loading="loading" title="排期订单信息" /></el-drawer>
  </div>
</template>
