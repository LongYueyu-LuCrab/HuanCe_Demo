<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Box,
  Calendar,
  Clock,
  Cpu,
  DataBoard,
  DocumentChecked,
  Menu,
  Money,
  Operation,
  Tickets,
  UserFilled,
  Van,
} from '@element-plus/icons-vue'
import { getMenuGroups } from '../permissions'
import { useSession } from '../stores/session'
import companyLogo from '../assets/suzhou-huance-logo.png'

const route = useRoute()
const router = useRouter()
const session = useSession()

const menuGroups = computed(() => getMenuGroups(session.state.user))
const activePath = computed(() => route.path)
const roleText = computed(() => session.state.user.roles?.join(' / ') || '普通用户')
const displayName = computed(() => session.state.user.display_name || session.state.user.username || '用户')
const currentTitle = computed(() => {
  const item = menuGroups.value.flatMap((group) => group.items).find((menuItem) => menuItem.path === route.path)
  return item?.label || String(route.meta.title || '工作台')
})

const iconMap = {
  Box,
  Calendar,
  Clock,
  Cpu,
  DataBoard,
  DocumentChecked,
  Menu,
  Money,
  Operation,
  Tickets,
  UserFilled,
  Van,
}

function iconFor(name?: string) {
  if (!name) return Menu
  return iconMap[name as keyof typeof iconMap] || Menu
}

async function logout() {
  await session.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside width="268px" class="shell-aside">
      <div class="brand-block">
        <img :src="companyLogo" alt="苏州环测检测技术有限公司 logo">
        <div>
          <strong>环测 LIMS</strong>
          <span>{{ roleText }}</span>
        </div>
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
        <div>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>苏州环测检测技术有限公司</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
          <h1>{{ currentTitle }}</h1>
        </div>
        <div class="header-actions">
          <el-button v-if="session.canAccessAdmin.value" tag="a" href="/admin/" type="primary" plain>进入 Django 后台</el-button>
          <el-dropdown>
            <el-button>
              {{ displayName }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ roleText }}</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="shell-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
