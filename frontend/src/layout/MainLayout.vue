<template>
  <el-container class="layout">
    <el-aside width="212px" class="aside">
      <div class="logo"><span class="dot"></span> 服装进销存</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon><span>工作台</span></el-menu-item>
        <el-sub-menu index="purchase">
          <template #title><el-icon><SoldOut /></el-icon><span>进货管理</span></template>
          <el-menu-item index="/purchase-entry">进货录入</el-menu-item>
          <el-menu-item index="/purchase-list">进货记录</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="sale">
          <template #title><el-icon><ShoppingCart /></el-icon><span>销售管理</span></template>
          <el-menu-item index="/sale-create">销售开单</el-menu-item>
          <el-menu-item index="/sale-list">销售记录</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/stock"><el-icon><Box /></el-icon><span>库存查询</span></el-menu-item>
        <el-menu-item index="/products"><el-icon><Goods /></el-icon><span>商品档案</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><TrendCharts /></el-icon><span>统计报表</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="crumb">{{ route.meta.title || '' }}</div>
        <div class="user">
          <div class="avatar">{{ (auth.username || 'A').slice(0, 1).toUpperCase() }}</div>
          <span>{{ auth.username }}</span>
          <el-button link type="danger" @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const activeMenu = computed(() => route.path)

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #1f2544; overflow: hidden; }
.logo {
  height: 60px; display: flex; align-items: center; gap: 10px; padding: 0 20px;
  color: #fff; font-weight: 700; font-size: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo .dot { width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, #5b6ef5, #b06ab3); display: inline-block; }
.aside :deep(.el-menu) { border-right: none; background: transparent; }
.aside :deep(.el-menu-item), .aside :deep(.el-sub-menu__title) { color: #aab1cc; height: 46px; }
.aside :deep(.el-menu-item:hover), .aside :deep(.el-sub-menu__title:hover) { background: rgba(255, 255, 255, 0.06); color: #fff; }
.aside :deep(.el-menu-item.is-active) { color: #fff; background: linear-gradient(90deg, var(--brand), rgba(91, 110, 245, 0.35)); border-left: 3px solid #fff; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 0 #edf0f7; height: 60px; }
.crumb { font-size: 17px; font-weight: 600; }
.user { display: flex; align-items: center; gap: 12px; color: #5a6178; }
.avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--brand); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 13px; }
.main { padding: 18px; overflow: auto; }
</style>
