<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import OutsourceBadge from '../components/OutsourceBadge.vue'
import { fetchAvailableDevices, fetchLaboratoryOrders, fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { LabDevice, OrderItem, ScheduleItem } from '../types'

const route = useRoute()
const router = useRouter()
const session = useSession()
const isBusinessDept = computed(() => (session.state.user.roles || []).includes('商务部'))
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
const availabilityMessage = ref('')
let availabilityRequest = 0
let preferredDeviceId: number | undefined
const handledActionKey = ref('')
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
    openRequestedAction()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '实验室订单读取失败')
  }
}

function openActionFromDetail(action: string, schedule: ScheduleItem) {
  detailDrawerVisible.value = false
  openWorkflow(action, schedule)
}

async function openRequestedAction() {
  const action = String(route.query.action || '')
  const scheduleId = Number(route.query.schedule || 0)
  const allowedActions = new Set(['schedule_assign', 'sample_arrival', 'process_change'])
  const key = `${route.fullPath}:${scheduleId}:${action}`
  if (!scheduleId || !allowedActions.has(action) || handledActionKey.value === key) return
  handledActionKey.value = key
  try {
    // Resolve the requested order directly; it may be outside the loaded page.
    const order = await fetchOrderDetail(String(route.query.order || ''))
    if (route.fullPath + `:${scheduleId}:${action}` !== key) return
    const schedule = order.schedule_records?.find((item) => item.id === scheduleId)
    if (!schedule) throw new Error('未找到指定实验室任务，请刷新订单后重试')
    detailDrawerVisible.value = false
    openWorkflow(action, schedule)
    const { action: ignoredAction, schedule: ignoredSchedule, ...query } = route.query
    await router.replace({ query })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务读取失败')
  } finally {
    handledActionKey.value = ''
  }
}

watch(labType, loadLaboratoryOrders, { immediate: true })
watch(() => route.fullPath, () => openRequestedAction())
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
  activeSchedule.value = schedule
  detailDrawerVisible.value = true
  void loadOrderContext(schedule.order_no)
}

function scheduleFromDetail() {
  if (!activeSchedule.value) return
  openActionFromDetail('schedule_assign', activeSchedule.value)
}

function sampleArrivalFromDetail() {
  if (!activeSchedule.value) return
  openActionFromDetail('sample_arrival', activeSchedule.value)
}

function openWorkflow(action: string, schedule: ScheduleItem) {
  resetDeviceSelection()
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
    sample_arrived: action === 'sample_arrival' ? true : schedule.sample_arrived,
    test_start_time: '',
    test_end_time: '',
    report_no: '',
    report_type: 'formal',
    final_conclusion: '',
  })
  preferredDeviceId = form.device_id
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

function resetDeviceSelection() {
  preferredDeviceId = undefined
  availabilityRequest++
  availabilityLoading.value = false
  availabilityMessage.value = ''
  availableDevices.value = []
  form.device_id = undefined
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
  if ((activeAction.value === 'end_test' || activeAction.value === 'outsource_result') && !form.result_status) {
    ElMessage.warning('请选择实验结果')
    return
  }
  if ((activeAction.value === 'schedule_assign' || activeAction.value === 'process_change')
    && !isBusinessDept.value && form.sample_arrived && (activeSchedule.value?.sample_photos.length || 0) === 0 && samplePhotoFiles.value.length === 0) {
    ElMessage.warning('选择“样品已到”时必须上传至少一张样品照片')
    return
  }
  if (activeAction.value === 'sample_arrival' && samplePhotoFiles.value.length === 0) {
    ElMessage.warning(activeSchedule.value?.sample_arrived ? '请至少上传一张补充样品图片' : '样品入库必须上传至少一张样品图片')
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
      <p><strong>{{ activeSchedule?.order_no }}</strong> · {{ activeSchedule?.project_name }} · {{ activeSchedule?.remark }}</p>
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'schedule_assign' || activeAction === 'process_change'">
          <el-form-item :label="activeAction === 'process_change' ? '调整后开始' : '计划开始'">
            <el-date-picker v-model="form.plan_start_time" value-format="YYYY-MM-DD" type="date" @change="onPlanDatesChange" />
          </el-form-item>
          <el-form-item :label="activeAction === 'process_change' ? '调整后结束' : '计划结束'">
            <el-date-picker v-model="form.plan_end_time" value-format="YYYY-MM-DD" type="date" @change="onPlanDatesChange" />
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
            description="系统将记录实际入库时间、当前操作账号和上传的现场照片；该操作不依赖排期，可先入库后排期。"
            show-icon
          />
          <el-form-item label="样品入库照片" class="form-wide" required>
            <el-upload v-model:file-list="samplePhotoFiles" :auto-upload="false" multiple accept=".jpg,.jpeg,.png">
              <el-button type="primary" plain>上传样品图片</el-button>
              <template #tip><div class="el-upload__tip">支持 JPG、PNG；单张不超过 10MB，本次合计不超过 30MB。</div></template>
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
      <el-collapse class="mt-16"><el-collapse-item title="查看订单详情与流程" name="context"><OrderSnapshot :order="activeOrder" :loading="orderLoading" :show-actions="false" title="试验任务订单信息" /></el-collapse-item></el-collapse>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="availabilityLoading" @click="submitWorkflow">确认提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="订单详情" size="min(720px, 94vw)">
      <el-alert
        v-if="activeSchedule && !activeSchedule.is_scheduled && [3, 4].includes(activeSchedule.status_key)"
        class="mb-16"
        title="该执行路径尚未由实验室确认排期"
        type="warning"
        :closable="false"
        description="委外合同中的实验起止时间仅供参考；实验室负责人或操作员确认日期后，才计为完成排期。"
        show-icon
      >
        <template #default>
          <el-button class="mt-8" type="primary" @click="scheduleFromDetail">排期 / 排台</el-button>
        </template>
      </el-alert>
      <div v-if="activeSchedule && [3, 4].includes(activeSchedule.status_key) && ![4, 5].includes(activeSchedule.schedule_status_key)" class="row-actions mb-16">
        <el-button type="primary" @click="scheduleFromDetail">{{ activeSchedule.is_scheduled ? '重新排期' : '排期 / 排台' }}</el-button>
        <el-button v-if="!isBusinessDept" type="success" @click="sampleArrivalFromDetail">{{ activeSchedule.sample_arrived ? '补充样品图片' : '样品入库' }}</el-button>
      </div>
      <OrderSnapshot :order="activeOrder" :loading="orderLoading" title="实验室订单信息" />
    </el-drawer>

  </div>
</template>
