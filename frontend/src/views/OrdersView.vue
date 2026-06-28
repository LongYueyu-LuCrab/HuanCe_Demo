<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import OrderTable from '../components/OrderTable.vue'
import { createOrder } from '../services/api'
import { useSession } from '../stores/session'

const session = useSession()
const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  customer_name: '',
  contact_name: '',
  phone: '',
  project_name: '',
  test_requirements: '',
  expected_sample_arrival: '',
  expected_delivery_date: '',
  quoted_amount: '',
  is_urgent: false,
})

const orders = computed(() => session.state.dashboard?.order_groups?.orders ?? session.state.dashboard?.recent_orders ?? [])

async function submit() {
  submitting.value = true
  try {
    await createOrder(form)
    ElMessage.success('订单已提交，等待商务技术评审')
    dialogVisible.value = false
    Object.assign(form, {
      customer_name: '',
      contact_name: '',
      phone: '',
      project_name: '',
      test_requirements: '',
      expected_sample_arrival: '',
      expected_delivery_date: '',
      quoted_amount: '',
      is_urgent: false,
    })
    await session.refreshDashboard()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-toolbar">
      <div>
        <h2>订单管理</h2>
        <p>按当前角色显示可查看订单；销售可从这里发起新订单。</p>
      </div>
      <el-button v-if="session.canCreateOrder.value" type="primary" @click="dialogVisible = true">销售下单</el-button>
    </div>

    <OrderTable :orders="orders" />

    <el-dialog v-model="dialogVisible" title="销售下单" width="760px">
      <el-form label-position="top" class="form-grid">
        <el-form-item label="客户名称"><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="项目名称"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="预计样品到达"><el-date-picker v-model="form.expected_sample_arrival" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="预计交付日期"><el-date-picker v-model="form.expected_delivery_date" value-format="YYYY-MM-DD" type="date" /></el-form-item>
        <el-form-item label="报价金额"><el-input v-model="form.quoted_amount" type="number" /></el-form-item>
        <el-form-item label="加急"><el-switch v-model="form.is_urgent" /></el-form-item>
        <el-form-item label="试验需求" class="form-wide"><el-input v-model="form.test_requirements" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交订单</el-button>
      </template>
    </el-dialog>
  </div>
</template>
