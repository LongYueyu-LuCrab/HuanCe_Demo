<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Calendar,
  CollectionTag,
  Connection,
  DataAnalysis,
  DocumentChecked,
  List,
  Menu,
  Memo,
  Monitor,
  OfficeBuilding,
  SetUp,
  UserFilled,
  Wallet,
} from '@element-plus/icons-vue'
import { getMenuGroups, getRoleDisplayText } from '../permissions'
import { changePassword } from '../services/api'
import { useSession } from '../stores/session'
import companyLogo from '../assets/suzhou-huance-logo.png'

const route = useRoute()
const router = useRouter()
const session = useSession()
const mobileNavVisible = ref(false)
const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordForm = reactive({ current: '', next: '', confirm: '' })

const menuGroups = computed(() => getMenuGroups(session.state.user))
const activePath = computed(() => route.path)
const roleText = computed(() => getRoleDisplayText(session.state.user))
const displayName = computed(() => session.state.user.display_name || session.state.user.username || '用户')
const currentTitle = computed(() => {
  const item = menuGroups.value.flatMap((group) => group.items).find((menuItem) => menuItem.path === route.path)
  return item?.label || String(route.meta.title || '工作台')
})

const iconMap = {
  Calendar,
  CollectionTag,
  Connection,
  DataAnalysis,
  DocumentChecked,
  List,
  Menu,
  Memo,
  Monitor,
  OfficeBuilding,
  SetUp,
  UserFilled,
  Wallet,
}

function iconFor(name?: string) {
  if (!name) return Menu
  return iconMap[name as keyof typeof iconMap] || Menu
}

async function logout() {
  await session.logout()
  router.push('/login')
}

function openPasswordDialog() {
  passwordForm.current = ''
  passwordForm.next = ''
  passwordForm.confirm = ''
  passwordDialogVisible.value = true
}

async function submitPasswordChange() {
  if (!passwordForm.current || !passwordForm.next || !passwordForm.confirm) {
    ElMessage.warning('请完整填写密码信息')
    return
  }
  if (passwordForm.next !== passwordForm.confirm) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (passwordForm.next.length < 8 || !/[A-Za-z]/.test(passwordForm.next) || !/\d/.test(passwordForm.next) || !/[^A-Za-z0-9]/.test(passwordForm.next)) {
    ElMessage.error('新密码至少 8 位，且必须包含字母、数字和符号')
    return
  }
  passwordSubmitting.value = true
  try {
    await changePassword(passwordForm.current, passwordForm.next, passwordForm.confirm)
    passwordDialogVisible.value = false
    await session.logout()
    ElMessage.success('密码修改成功，请使用新密码重新登录')
    await router.push('/login')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '密码修改失败')
  } finally {
    passwordSubmitting.value = false
  }
}

async function retryConnection() {
  try {
    await session.checkHealth()
    await session.refreshDashboard()
  } catch {
    // Keep the connection state visible so the user can retry again.
  }
}

async function clearAccessNotice() {
  const query = { ...route.query }
  delete query.denied
  await router.replace({ query })
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside width="268px" class="shell-aside">
      <div class="brand-block">
        <img :src="companyLogo" alt="苏州环测检测技术有限公司 logo">
        <div>
          <strong>环测 LIMS</strong>
          <span>Laboratory Operations</span>
        </div>
      </div>

      <div class="role-card">
        <span>当前岗位</span>
        <strong>{{ roleText }}</strong>
        <small>按权责隔离菜单与数据</small>
      </div>

      <el-scrollbar class="menu-scroll">
        <div v-for="group in menuGroups" :key="group.title" class="menu-group">
          <p>{{ group.title }}</p>
          <el-menu :default-active="activePath" router class="side-menu">
            <el-menu-item v-for="item in group.items" :key="item.key" :index="item.path">
              <el-icon><component :is="iconFor(item.icon)" /></el-icon>
              <span>{{ item.label }}</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-scrollbar>
    </el-aside>

    <el-container>
      <el-header class="shell-header">
        <div class="mobile-shell-bar">
          <el-button class="mobile-menu-button" text aria-label="打开导航" @click="mobileNavVisible = true">
            <el-icon><Menu /></el-icon>
          </el-button>
          <strong>{{ currentTitle }}</strong>
        </div>
        <div>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>苏州环测检测技术有限公司</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
          <h1>{{ currentTitle }}</h1>
        </div>
        <div class="header-actions">
          <div class="system-health">
            <span :class="{ 'is-error': session.state.health.status === 'error' || session.state.connectionError, 'is-loading': session.state.loading || session.state.health.status === 'checking' }"></span>
            {{ session.state.loading ? '连接中' : session.state.health.message }}
            <el-button v-if="session.state.health.status === 'error' || session.state.connectionError" text size="small" @click="retryConnection">重试</el-button>
          </div>
          <el-button v-if="session.canAccessAdmin.value" tag="a" href="/admin/" type="primary" plain>进入 Django 后台</el-button>
          <el-dropdown>
            <el-button>
              {{ displayName }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ roleText }}</el-dropdown-item>
                <el-dropdown-item @click="openPasswordDialog">修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="shell-main">
        <el-alert
          v-if="route.query.denied"
          title="当前岗位没有访问该功能的权限，已返回可用工作区。"
          type="warning"
          show-icon
          closable
          class="access-notice"
          @close="clearAccessNotice"
        />
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-drawer v-model="mobileNavVisible" title="环测 LIMS" direction="ltr" size="min(320px, 88vw)" class="mobile-nav-drawer">
    <div class="mobile-nav-role">
      <span>当前岗位</span>
      <strong>{{ roleText }}</strong>
    </div>
    <div v-for="group in menuGroups" :key="`mobile-${group.title}`" class="menu-group mobile-menu-group">
      <p>{{ group.title }}</p>
      <el-menu :default-active="activePath" router class="side-menu" @select="mobileNavVisible = false">
        <el-menu-item v-for="item in group.items" :key="item.key" :index="item.path">
          <el-icon><component :is="iconFor(item.icon)" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </div>
  </el-drawer>

  <el-dialog v-model="passwordDialogVisible" title="修改密码" width="440px" destroy-on-close>
    <el-form label-position="top" @submit.prevent="submitPasswordChange">
      <el-form-item label="当前密码">
        <el-input v-model="passwordForm.current" type="password" show-password autocomplete="current-password" placeholder="请输入当前密码" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="passwordForm.next" type="password" show-password autocomplete="new-password" placeholder="至少 8 位，含字母、数字和符号" />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input v-model="passwordForm.confirm" type="password" show-password autocomplete="new-password" placeholder="请再次输入新密码" @keyup.enter="submitPasswordChange" />
      </el-form-item>
      <p class="password-hint">密码必须同时包含字母、数字和符号。修改成功后需要重新登录。</p>
    </el-form>
    <template #footer>
      <el-button @click="passwordDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="passwordSubmitting" @click="submitPasswordChange">确认修改</el-button>
    </template>
  </el-dialog>
</template>
