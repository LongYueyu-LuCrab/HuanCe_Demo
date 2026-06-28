<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../services/api'
import { useSession } from '../stores/session'
import companyLogo from '../assets/suzhou-huance-logo.png'
import backgroundImage from '../assets/lims-background.png'

const router = useRouter()
const session = useSession()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  loading.value = true
  try {
    const data = await login(form.username, form.password)
    await session.setUser(data.user)
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page" :style="{ backgroundImage: `linear-gradient(90deg, rgba(5, 14, 28, 0.56), rgba(5, 14, 28, 0.24)), url(${backgroundImage})` }">
    <div class="login-brand">
      <img :src="companyLogo" alt="苏州环测检测技术有限公司 logo">
      <div>
        <strong>苏州环测检测技术有限公司</strong>
        <span>Laboratory Information Management System</span>
      </div>
    </div>

    <el-card class="login-card" shadow="always">
      <p class="panel-kicker">LIMS LOGIN</p>
      <h1>环测实验室系统</h1>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" autocomplete="current-password" />
        </el-form-item>
        <el-button :loading="loading" size="large" type="primary" class="full-button" @click="submit">登录系统</el-button>
      </el-form>
    </el-card>
  </main>
</template>
