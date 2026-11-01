import { computed, reactive } from 'vue'
import { fetchCurrentUser, fetchDashboard, logout as logoutApi } from '../services/api'
import type { Dashboard, User } from '../types'

const state = reactive<{
  user: User
  dashboard: Dashboard | null
  bootstrapped: boolean
  loading: boolean
  connectionError: string
}>({
  user: { authenticated: false },
  dashboard: null,
  bootstrapped: false,
  loading: false,
  connectionError: '',
})

export function useSession() {
  const roles = computed(() => new Set(state.user.roles || []))
  const isAuthenticated = computed(() => Boolean(state.user.authenticated))
  const isChairman = computed(() => Boolean(state.user.is_chairman))
  const canSeeAllBusiness = computed(() => isChairman.value || roles.value.has('总经理'))
  const canCreateOrder = computed(() => isChairman.value || roles.value.has('销售') || roles.value.has('商务部'))
  const canAccessAdmin = computed(() => isChairman.value || roles.value.has('总经理'))

  function hasRole(role: string) {
    return roles.value.has(role)
  }

  async function bootstrap() {
    if (state.bootstrapped) return
    state.loading = true
    try {
      state.user = await fetchCurrentUser()
      if (state.user.authenticated) {
        state.dashboard = await fetchDashboard()
      }
      state.connectionError = ''
    } catch (error) {
      state.connectionError = error instanceof Error ? error.message : '系统连接失败'
    } finally {
      state.bootstrapped = true
      state.loading = false
    }
  }

  async function refreshDashboard() {
    if (!state.user.authenticated) return
    try {
      state.dashboard = await fetchDashboard()
      state.connectionError = ''
    } catch (error) {
      state.connectionError = error instanceof Error ? error.message : '系统连接失败'
      throw error
    }
  }

  async function setUser(user: User) {
    state.user = user
    await refreshDashboard()
  }

  async function logout() {
    await logoutApi()
    state.user = { authenticated: false }
    state.dashboard = null
    state.connectionError = ''
  }

  return {
    state,
    roles,
    isAuthenticated,
    isChairman,
    canSeeAllBusiness,
    canCreateOrder,
    canAccessAdmin,
    hasRole,
    bootstrap,
    refreshDashboard,
    setUser,
    logout,
  }
}
