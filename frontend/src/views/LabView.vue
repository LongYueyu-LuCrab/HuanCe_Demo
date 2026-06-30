<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import ScheduleTable from '../components/ScheduleTable.vue'
import { workflowAction } from '../services/api'
import { useSession } from '../stores/session'
import type { ScheduleItem } from '../types'

const route = useRoute()
const session = useSession()
const labKey = computed(() => (route.params.lab === 'jiangyin' ? 'jiangyin' : 'suzhou'))
const lab = computed(() => session.state.dashboard?.labs?.[labKey.value])
const dialogVisible = ref(false)
const submitting = ref(false)
const activeAction = ref('')
const activeOrderNo = ref('')
const activeSchedule = ref<ScheduleItem | null>(null)
const standardDialogVisible = ref(false)
const standardSubmitting = ref(false)
const form = reactive({
  change_scene: 2,
  change_content: '',
  new_test_demand: '',
  test_item_list: '',
  standard_industry: '',
  standard_id: undefined as number | undefined,
  test_standard: '',
  test_raw_data: '',
  test_conclusion_temp: '',
})
const standardForm = reactive({
  industry: '',
  standard_code: '',
  standard_name: '',
  description: '',
})

const standards = computed(() => session.state.dashboard?.test_standards ?? [])
const standardIndustries = computed(() => Array.from(new Set(standards.value.map((item) => item.industry))).filter(Boolean))
const standardOptions = computed(() => standards.value.filter((item) => item.industry === form.standard_industry))

const canManageStandards = computed(() => {
  const roles = new Set(session.state.user.roles || [])
  return Boolean(session.state.user.is_chairman || roles.has('苏州实验室') || roles.has('江阴实验室') || roles.has('质量部'))
})

function openWorkflow(action: string, schedule: ScheduleItem) {
  activeAction.value = action
  activeSchedule.value = schedule
  activeOrderNo.value = schedule.order_no
  const firstIndustry = standardIndustries.value[0] || ''
  const firstStandard = standards.value.find((item) => item.industry === firstIndustry)
  Object.assign(form, {
    change_scene: 2,
    change_content: '',
    new_test_demand: '',
    test_item_list: schedule.remark || schedule.project_name,
    standard_industry: firstIndustry,
    standard_id: firstStandard?.id,
    test_standard: firstStandard ? `${firstStandard.standard_code} ${firstStandard.standard_name}` : '',
    test_raw_data: '',
    test_conclusion_temp: '',
  })
  dialogVisible.value = true
}

function handleIndustryChange() {
  form.standard_id = standardOptions.value[0]?.id
}

function openStandardDialog() {
  Object.assign(standardForm, {
    industry: '',
    standard_code: '',
    standard_name: '',
    description: '',
  })
  standardDialogVisible.value = true
}

async function submitStandard() {
  standardSubmitting.value = true
  try {
    await workflowAction({ action: 'standard_create', ...standardForm })
    ElMessage.success('试验标准已保存')
    standardDialogVisible.value = false
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    standardSubmitting.value = false
  }
}

async function submitWorkflow() {
  submitting.value = true
  try {
    const selectedStandard = standards.value.find((item) => item.id === form.standard_id)
    const testStandard = selectedStandard
      ? `${selectedStandard.standard_code} ${selectedStandard.standard_name}`
      : form.test_standard
    await workflowAction({
      action: activeAction.value,
      order_no: activeOrderNo.value,
      ...form,
      test_item_list: activeSchedule.value?.remark || form.test_item_list,
      test_standard: testStandard,
    })
    ElMessage.success('试验节点操作已完成')
    dialogVisible.value = false
    await session.refreshDashboard()
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
      <el-button v-if="canManageStandards" type="primary" @click="openStandardDialog">添加试验标准</el-button>
    </div>

    <div class="device-grid">
      <el-card v-for="device in lab?.devices ?? []" :key="device.name" shadow="never" class="device-card">
        <div class="device-head">
          <h3>{{ device.name }}</h3>
          <el-tag :type="device.status.includes('运行') ? 'success' : 'info'" effect="plain">{{ device.status }}</el-tag>
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

    <ScheduleTable :orders="lab?.orders ?? []" :user="session.state.user" @workflow="openWorkflow" />

    <el-dialog v-model="dialogVisible" title="试验节点操作" width="720px">
      <el-alert :title="activeOrderNo" type="info" show-icon :closable="false" />
      <el-form label-position="top" class="form-grid mt-16">
        <template v-if="activeAction === 'start_test'">
          <el-form-item label="试验项目" class="form-wide">
            <el-input v-model="form.test_item_list" disabled type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="行业">
            <el-select v-model="form.standard_industry" placeholder="选择行业" @change="handleIndustryChange">
              <el-option v-for="industry in standardIndustries" :key="industry" :label="industry" :value="industry" />
            </el-select>
          </el-form-item>
          <el-form-item label="检测标准">
            <el-select v-model="form.standard_id" filterable placeholder="选择标准">
              <el-option
                v-for="standard in standardOptions"
                :key="standard.id"
                :label="`${standard.standard_code} ${standard.standard_name}`"
                :value="standard.id"
              />
            </el-select>
          </el-form-item>
        </template>
        <template v-else-if="activeAction === 'submit_test'">
          <el-form-item label="原始检测数据" class="form-wide"><el-input v-model="form.test_raw_data" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="临时结论" class="form-wide"><el-input v-model="form.test_conclusion_temp" type="textarea" :rows="3" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="变更后需求" class="form-wide"><el-input v-model="form.new_test_demand" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="变更说明" class="form-wide"><el-input v-model="form.change_content" type="textarea" :rows="3" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitWorkflow">确认提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="standardDialogVisible" title="添加试验标准" width="640px">
      <el-form label-position="top" class="form-grid">
        <el-form-item label="行业"><el-input v-model="standardForm.industry" placeholder="例如：振动、汽车、环境" /></el-form-item>
        <el-form-item label="标准编号"><el-input v-model="standardForm.standard_code" placeholder="例如：GB/T 2423.10" /></el-form-item>
        <el-form-item label="标准名称" class="form-wide"><el-input v-model="standardForm.standard_name" /></el-form-item>
        <el-form-item label="说明" class="form-wide"><el-input v-model="standardForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="standardDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="standardSubmitting" @click="submitStandard">保存标准</el-button>
      </template>
    </el-dialog>
  </div>
</template>
