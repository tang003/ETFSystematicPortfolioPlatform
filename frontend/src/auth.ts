import { computed, onMounted, ref } from 'vue'
import { fetchAuthStatus } from './api/client'

export type Role = 'admin' | 'researcher' | 'viewer'

export function normalizeRole(role: string | null | undefined): Role {
  if (role === 'admin' || role === 'researcher') return role
  return 'viewer'
}

export function roleLabel(role: Role) {
  const map: Record<Role, string> = {
    admin: '管理员',
    researcher: '研究员',
    viewer: '观察者',
  }
  return map[role]
}

export function useAuthRole() {
  const currentRole = ref<Role>('viewer')
  const authEnabled = ref(false)

  async function loadAuthRole() {
    const status = await fetchAuthStatus()
    authEnabled.value = status.enabled
    currentRole.value = normalizeRole(status.role)
  }

  onMounted(() => {
    void loadAuthRole()
  })

  return {
    authEnabled,
    currentRole,
    canAdmin: computed(() => currentRole.value === 'admin'),
    canResearch: computed(() => currentRole.value === 'admin' || currentRole.value === 'researcher'),
    loadAuthRole,
  }
}

export function errorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { status?: number; data?: { detail?: string } } })?.response
  if (response?.status === 401) return '登录状态已过期，请重新登录。'
  if (response?.status === 403) return '当前账号权限不足。请联系管理员，或切换到具备该操作权限的账号。'
  if (response?.data?.detail) return response.data.detail
  return error instanceof Error ? error.message : fallback
}
