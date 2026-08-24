<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createLabDevice, deleteLabDevice, fetchLabDevices, updateLabDevice } from '../services/api'
import { useSession } from '../stores/session'
import type { LabDevice } from '../types'

const session = useSession()
const devices = ref<LabDevice[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const roles = computed(() => new Set(session.state.user.roles || []))
const defaultLabType = computed(() => roles.value.has('江阴实验室') ? 2 : 1)
const labFilter = ref(defaultLabType.value)
const canSwitchLab = computed(() => Boolean(session.state.user.is_chairman))
const filteredDevices = computed(() => devices.value.filter((item) => item.lab_type === labFilter.value))
const form = reactive({
  device_code: '', device_name: '', lab_type: defaultLabType.value, model_spec: '', capability: '', device_status: 1, remark: '',
})

function statusType(status: string) {
  if (status === '实验中' || status === '设备正常') return 'success'
  if (status === '维修中') return 'warning'
  return 'danger'
}

async function loadDevices() {
  loading.value = true
  try {
    devices.value = await fetchLabDevices()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '设备读取失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    device_code: '', device_name: '', lab_type: labFilter.value, model_spec: '', capability: '', device_status: 1, remark: '',
  })
  dialogVisible.value = true
}

function openEdit(device: LabDevice) {
  editingId.value = device.id
  Object.assign(form, {
    device_code: device.device_code,
    device_name: device.name,
    lab_type: device.lab_type,
    model_spec: device.model_spec,
    capability: device.capability,
    device_status: device.status_key,
    remark: device.remark,
  })
  dialogVisible.value = true
}

async function saveDevice() {
  if (!form.device_name.trim() || (!editingId.value && !form.device_code.trim())) {
    ElMessage.warning('请填写设备编号和设备名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateLabDevice(editingId.value, form)
      ElMessage.success('设备信息已更新')
    } else {
      await createLabDevice(form)
      ElMessage.success('设备已新增')
    }
    dialogVisible.value = false
    await loadDevices()
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '设备保存失败')
  } finally {
    saving.value = false
  }
}

async function removeDevice(device: LabDevice) {
  try {
    await ElMessageBox.confirm(`确认删除设备“${device.name}”吗？已有排期的设备将不允许删除。`, '删除设备', { type: 'warning' })
    await deleteLabDevice(device.id)
    ElMessage.success('设备已删除')
    await loadDevices()
    await session.refreshDashboard()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error instanceof Error ? error.message : '设备删除失败')
  }
}

onMounted(loadDevices)
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>实验室设备管理</h2>
        <p>维护试验台基础信息和运行状态；“实验中”由当前执行订单自动判定。</p>
      </div>
      <div class="row-actions">
        <el-segmented v-if="canSwitchLab" v-model="labFilter" :options="[{ label: '苏州实验室', value: 1 }, { label: '江阴实验室', value: 2 }]" />
        <el-button type="primary" @click="openCreate">新增设备</el-button>
      </div>
    </div>

    <el-card shadow="never" class="hc-card">
      <el-table v-loading="loading" :data="filteredDevices" stripe empty-text="当前实验室暂无设备">
        <el-table-column prop="device_code" label="设备编号" min-width="130" />
        <el-table-column label="设备" min-width="220">
          <template #default="{ row }">
            <div class="cell-main">{{ row.name }}</div>
            <div class="cell-sub">{{ row.model_spec || '未填写规格型号' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="capability" label="试验能力" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" effect="plain">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="当前任务" min-width="210">
          <template #default="{ row }">
            <template v-if="row.order_no">
              <div class="cell-main">{{ row.order_no }}</div>
              <div class="cell-sub">预计结束 {{ row.end_time || '待定' }}</div>
            </template>
            <span v-else class="muted">当前无执行订单</span>
          </template>
        </el-table-column>
        <el-table-column label="未来排期" width="100">
          <template #default="{ row }">{{ row.future_orders.length }} 笔</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button size="small" plain @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="removeDevice(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑设备' : '新增设备'" width="min(720px, 94vw)">
      <el-form label-position="top" class="form-grid">
        <el-form-item label="所属实验室">
          <el-select v-model="form.lab_type" :disabled="!canSwitchLab || Boolean(editingId)">
            <el-option label="苏州实验室" :value="1" />
            <el-option label="江阴实验室" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备编号"><el-input v-model="form.device_code" :disabled="Boolean(editingId)" placeholder="例如 SZ-VIB-20T" /></el-form-item>
        <el-form-item label="设备名称"><el-input v-model="form.device_name" /></el-form-item>
        <el-form-item label="规格型号"><el-input v-model="form.model_spec" /></el-form-item>
        <el-form-item v-if="editingId" label="管理状态">
          <el-select v-model="form.device_status">
            <el-option label="设备正常" :value="1" />
            <el-option label="维修中" :value="2" />
            <el-option label="设备停用" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="试验能力" class="form-wide"><el-input v-model="form.capability" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="备注" class="form-wide"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDevice">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
