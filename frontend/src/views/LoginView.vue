<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100">
    <div class="w-full max-w-md">
      <!-- Logo & Title -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 rounded-2xl bg-primary-600 flex items-center justify-center mx-auto mb-4 shadow-lg">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-secondary-800">简历解析与问答助手</h1>
        <p class="text-secondary-500 mt-2">请登录以继续使用</p>
      </div>

      <!-- Login Form -->
      <div class="card p-8 shadow-xl">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              size="large"
              prefix-icon="User"
              :disabled="loading"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              size="large"
              prefix-icon="Lock"
              show-password
              :disabled="loading"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="w-full"
              :loading="loading"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- Demo Account Hint -->
        <div class="mt-6 p-4 bg-secondary-50 rounded-lg">
          <p class="text-sm text-secondary-600 font-medium mb-2">测试账号：</p>
          <div class="grid grid-cols-2 gap-2 text-sm">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 bg-primary-100 text-primary-700 rounded text-xs">管理员</span>
              <span class="text-secondary-600">admin / admin123</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 bg-secondary-200 text-secondary-700 rounded text-xs">用户</span>
              <span class="text-secondary-600">user / user123</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-secondary-400 text-sm mt-6">
        POC Demo Version
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { login } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await login({
        username: form.username,
        password: form.password
      })

      ElMessage.success('登录成功')

      // 跳转到之前的页面或首页
      const redirect = route.query.redirect as string
      router.push(redirect || '/')
    } catch (error: any) {
      // 错误已在 request.ts 中处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.card {
  background: white;
  border-radius: 16px;
}
</style>
