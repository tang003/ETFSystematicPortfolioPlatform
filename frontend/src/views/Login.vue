<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-brand">
        <div class="brand-mark">ETF</div>
        <div>
          <h1>系统化资产配置</h1>
          <p>ETF Systematic Portfolio Platform</p>
        </div>
      </div>

      <el-alert v-if="configurationError" type="error" :closable="false" title="服务器尚未完成登录配置" />
      <el-form label-position="top" @submit.prevent="submitLogin">
        <el-form-item label="用户名">
          <el-input v-model="username" autocomplete="username" autofocus />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" autocomplete="current-password" show-password @keyup.enter="submitLogin" />
        </el-form-item>
        <el-button class="login-submit" type="primary" native-type="submit" :loading="loading" :disabled="configurationError">
          登录控制台
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { fetchAuthStatus, login } from '../api/client'

const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const configurationError = ref(false)

onMounted(async () => {
  try {
    const status = await fetchAuthStatus()
    configurationError.value = status.enabled && !status.configured
    if (status.authenticated) await goToRequestedPage()
  } catch {
    ElMessage.error('无法连接服务器，请检查 API 服务')
  }
})

async function submitLogin() {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await login({ username: username.value.trim(), password: password.value })
    password.value = ''
    await goToRequestedPage()
  } catch (error: any) {
    const message = error?.response?.data?.detail || '登录失败'
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

async function goToRequestedPage() {
  const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : '/dashboard'
  await router.replace(target)
}
</script>
