<template>
  <el-container class="layout">
    <el-aside v-if="!isMobile" width="212px" class="aside">
      <NavMenu />
    </el-aside>
    <el-container class="content">
      <el-header class="header">
        <div class="header-left">
          <el-button v-if="isMobile" text class="nav-toggle" aria-label="打开导航" @click="drawerOpen = true">
            <el-icon :size="20"><Expand /></el-icon>
          </el-button>
          <div class="crumb">{{ route.meta.title || '' }}</div>
        </div>
        <div class="user">
          <div class="avatar">{{ (auth.username || 'A').slice(0, 1).toUpperCase() }}</div>
          <span v-if="!isMobile">{{ auth.username }}</span>
          <el-button link type="danger" @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <el-alert v-if="session.demo" title="演示模式：当前数据仅供体验" type="warning" :closable="false" />
        <el-alert v-if="session.notice" :title="session.notice" type="info" show-icon @close="session.notice = ''" />
        <router-view />
      </el-main>
    </el-container>

    <el-drawer
      v-model="drawerOpen"
      direction="ltr"
      :with-header="false"
      size="232px"
      class="mobile-nav-drawer"
      modal-class="mobile-nav-drawer-modal"
    >
      <NavMenu @navigate="drawerOpen = false" />
    </el-drawer>

    <LanAccessButton />
  </el-container>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import NavMenu from './NavMenu.vue'
import LanAccessButton from '../components/LanAccessButton.vue'
import { authApi } from '../api'
import { session, saveSession } from '../session'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mql = typeof window !== 'undefined' ? window.matchMedia('(max-width: 768px)') : null
const isMobile = ref(mql ? mql.matches : false)
const drawerOpen = ref(false)

function onMediaChange(e) {
  isMobile.value = e.matches
  if (!e.matches) drawerOpen.value = false
}

onMounted(async () => { mql?.addEventListener('change', onMediaChange); try { saveSession(await authApi.me()); if (session.mustChange) router.replace('/settings') } catch (_) {} })
onUnmounted(() => mql?.removeEventListener('change', onMediaChange))

watch(() => route.path, () => {
  drawerOpen.value = false
})

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100%; }
.content { min-width: 0; }
.aside { background: #1f2544; overflow: hidden; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 0 #edf0f7; height: 60px; }
.header-left { display: flex; align-items: center; min-width: 0; }
.crumb { font-size: 17px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user { display: flex; align-items: center; gap: 12px; color: #5a6178; flex: none; white-space: nowrap; }
.avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--brand); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 13px; }
.main { padding: 18px; overflow: auto; min-width: 0; }
@media (max-width: 768px) {
  .header { height: 56px; padding: 0 12px; }
  .header-left { gap: 2px; }
  .nav-toggle { width: 34px; height: 34px; padding: 0; margin-right: 2px; }
  .crumb { font-size: 16px; }
  .user { gap: 8px; }
  .avatar { width: 28px; height: 28px; font-size: 12px; }
  .main { padding: 12px; padding-bottom: calc(12px + env(safe-area-inset-bottom)); }
}
</style>
