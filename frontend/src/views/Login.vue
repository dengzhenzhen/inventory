<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">服</div>
      <div class="login-title">服装进销存管理系统</div>
      <div class="login-sub">进货 · 销售 · 库存 一站式管理</div>
      <el-form @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" size="large" placeholder="账号">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="密码" @keyup.enter="onSubmit">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onSubmit">登 录</el-button>
      </el-form>
      <div class="login-tip">默认账号：admin / admin123</div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ username: 'admin', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  position: relative; overflow: hidden;
  height: 100vh; height: 100dvh; display: flex; align-items: center; justify-content: center;
  padding-bottom: env(safe-area-inset-bottom);
  background-color: #ffe3ef;
  background-image: url('/hello-kitty-pattern.svg');
  background-size: 200px 200px;
  background-repeat: repeat;
  background-position: center;
}
.login-wrap::before,
.login-wrap::after {
  content: ""; position: absolute; pointer-events: none;
  background: url('/hello-kitty.svg') center / contain no-repeat;
}
.login-wrap::before { left: -70px; bottom: -60px; width: 320px; height: 320px; opacity: 0.95; }
.login-wrap::after { right: -60px; top: -50px; width: 260px; height: 260px; opacity: 0.9; }
.login-card { position: relative; z-index: 1; width: min(380px, calc(100vw - 32px)); background: #fff; border-radius: 16px; padding: 40px 36px 30px; box-shadow: 0 20px 60px rgba(20, 25, 60, 0.35); }
.login-logo {
  width: 56px; height: 56px; border-radius: 14px; margin: 0 auto 16px; display: flex; align-items: center;
  justify-content: center; background: linear-gradient(135deg, #5b6ef5, #8a7bf5); color: #fff; font-size: 26px; font-weight: 700;
}
.login-title { text-align: center; font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.login-sub { text-align: center; color: #98a0b3; font-size: 13px; margin-bottom: 26px; }
.login-tip { text-align: center; color: #b3bacb; font-size: 12px; margin-top: 16px; }
@media (max-width: 768px) {
  .login-card { padding: 30px 22px 24px; border-radius: 14px; }
  .login-title { font-size: 20px; }
  .login-sub { margin-bottom: 22px; }
  .login-wrap::before { width: 220px; height: 220px; left: -90px; bottom: -70px; opacity: 0.55; }
  .login-wrap::after { width: 180px; height: 180px; right: -80px; top: -60px; opacity: 0.5; }
}
@media (max-width: 480px) {
  .login-wrap::before, .login-wrap::after { opacity: 0.35; }
}
</style>
