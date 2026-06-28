import { computed, reactive } from 'vue'
import { fetchCurrentUser, fetchDashboard, logout as logoutApi } from '../services/api'
import type { Dashboard, User } from '../types'

const state = reactive<{
  user: User
  dashboard: Dashboard | null
  bootstrapped: boolean
  loading: boolean
}>({
  user: { authenticated: false },
  dashboard: null,
  bootstrapped: false,
  loading: false,
})

export function useSession() {
  const roles = computed(() => new Set(state.user.roles || []))
  const isAuthenticated = computed(() => Boolean(state.user.authenticated))
  const isChairman = computed(() => Boolean(state.user.is_chairman))
  const canSeeAllBusiness = computed(() => isChairman.value || roles.value.has('总经理'))
  const canCreateOrder = computed(() => isChairman.value || roles.value.has('销售'))
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
    } finally {
      state.bootstrapped = true
      state.loading = false
    }
  }

  async function refreshDashboard() {
    if (!state.user.authenticated) return
    state.dashboard = await fetchDashboard()
  }

  async function setUser(user: User) {
    state.user = user
    await refreshDashboard()
  }

  async function logout() {
    await logoutApi()
    state.user = { authenticated: false }
    state.dashboard = null
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
