<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { addEmployee } from '../services/api'

const submitting = ref(false)
const form = reactive({
  username: '', password: '', display_name: '', email: '', role: '销售', lab_type: 1,
})
const roles = ['销售', '商务', '技术', '苏州实验室', '江阴实验室', '实验操作员', '委外供应商', '总经理', '会计', '董事长']
const showLab = computed(() => form.role === '实验操作员')

async function submit() {
  submitting.value = true
  try {
    await addEmployee(form)
    ElMessage.success('员工账号已创建')
    Object.assign(form, { username: '', password: '', display_name: '', email: '', role: '销售', lab_type: 1 })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-card shadow="never" class="hc-card form-card">
    <template #header>
      <div class="card-heading">
        <div>
          <h2>添加员工</h2>
          <p>创建员工账号并分配岗位。实验操作员还必须指定所属实验室。</p>
        </div>
      </div>
    </template>
    <el-form label-position="top" class="form-grid">
      <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
      <el-form-item label="姓名 / 昵称"><el-input v-model="form.display_name" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="form.email" type="email" /></el-form-item>
      <el-form-item label="初始密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
      <el-form-item label="岗位"><el-select v-model="form.role"><el-option v-for="role in roles" :key="role" :label="role" :value="role" /></el-select></el-form-item>
      <el-form-item v-if="showLab" label="所属实验室">
        <el-select v-model="form.lab_type">
          <el-option label="苏州实验室" :value="1" />
          <el-option label="江阴实验室" :value="2" />
        </el-select>
      </el-form-item>
    </el-form>
    <el-button type="primary" :loading="submitting" @click="submit">创建员工</el-button>
  </el-card>
</template>
