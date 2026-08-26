<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import ScheduleTable from '../components/ScheduleTable.vue'
import OrderSnapshot from '../components/OrderSnapshot.vue'
import { fetchAvailableDevices, fetchOrderDetail, workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { LabDevice, OrderItem, ScheduleItem } from '../types'

const session = useSession()
const schedules = computed(() => session.state.dashboard?.schedules ?? [])
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
const form = reactive({
  plan_start_time: '', plan_end_time: '', outsource_factory: '', outsource_price: '', outsource_cycle: '',
  device_id: undefined as number | undefined,
  sample_arrived: false,
  test_item_list: '', test_standard: '', test_raw_data: '', test_conclusion_temp: '',
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
  activeAction.value = action
  activeSchedule.value = schedule
  Object.assign(form, {
    plan_start_time: schedule.start_time || '', plan_end_time: schedule.end_time || '',
    device_id: schedule.device_id || undefined,
    sample_arrived: schedule.sample_arrived,
    outsource_factory: '', outsource_price: '', outsource_cycle: '',
    test_item_list: schedule.remark || schedule.project_name,
    test_standard: '', test_raw_data: '', test_conclusion_temp: '', test_start_time: '', test_end_time: '',
    change_scene: 2, new_test_demand: '', change_content: '', report_no: '', report_type: 'formal', final_conclusion: '',
  })
  dialogVisible.value = true
  void loadOrder(schedule.order_no)
  availableDevices.value = []
  samplePhotoFiles.value = []
  if ((action === 'schedule_assign' || action === 'process_change') && schedule.start_time && schedule.end_time && !schedule.test_type.includes('委外')) {
    void queryAvailableDevices()
  }
}

function resetDeviceSelection() {
  availableDevices.value = []
  form.device_id = undefined
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

async function submitWorkflow() {
  if (!activeSchedule.value) return
  if ((activeAction.value === 'schedule_assign' || activeAction.value === 'process_change')
    && form.sample_arrived && activeSchedule.value.sample_photos.length === 0 && samplePhotoFiles.value.length === 0) {
    ElMessage.warning('选择“样品已到”时必须上传至少一张样品照片')
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
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar"><div><h2>排期与任务</h2><p>实验室负责人在这里维护本人负责的内部及委外任务、样品、变更和报告。</p></div></div>
    <ScheduleTable :orders="schedules" :user="session.state.user" @detail="openOrderDetail" @workflow="openWorkflow" />

    <el-dialog v-model="dialogVisible" title="实验室任务操作" width="min(960px, 94vw)">
      <OrderSnapshot :order="selectedOrder" :loading="loading" title="任务关联订单" />
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'schedule_assign' || activeAction === 'process_change'">
          <el-form-item label="计划开始"><el-date-picker v-model="form.plan_start_time" value-format="YYYY-MM-DD" type="date" @change="resetDeviceSelection" /></el-form-item>
          <el-form-item label="计划结束"><el-date-picker v-model="form.plan_end_time" value-format="YYYY-MM-DD" type="date" @change="resetDeviceSelection" /></el-form-item>
          <template v-if="activeAction === 'schedule_assign' && activeSchedule?.test_type.includes('委外')">
            <el-form-item label="委外厂家"><el-input v-model="form.outsource_factory" /></el-form-item>
            <el-form-item label="委外价格"><el-input v-model="form.outsource_price" type="number" /></el-form-item>
            <el-form-item label="委外周期/天"><el-input v-model="form.outsource_cycle" type="number" /></el-form-item>
          </template>
          <template v-else-if="!activeSchedule?.test_type.includes('委外')">
            <el-form-item label="查询设备可用性"><el-button :loading="availabilityLoading" plain @click="queryAvailableDevices">查询所选日期的可用设备</el-button></el-form-item>
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
        <template v-else-if="activeAction === 'submit_test' || activeAction === 'outsource_result'">
          <el-form-item v-if="activeAction === 'outsource_result'" label="开始时间"><el-date-picker v-model="form.test_start_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item v-if="activeAction === 'outsource_result'" label="完成时间"><el-date-picker v-model="form.test_end_time" value-format="YYYY-MM-DD" type="date" /></el-form-item>
          <el-form-item label="原始数据 / 回传摘要" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="试验结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
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
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button></template>
    </el-dialog>

    <el-drawer v-model="drawerVisible" title="订单详情" size="min(720px, 94vw)"><OrderSnapshot :order="selectedOrder" :loading="loading" title="排期订单信息" /></el-drawer>
  </div>
</template>
