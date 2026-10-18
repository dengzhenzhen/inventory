<template>
  <div class="nav-menu">
    <div class="logo"><span class="dot"></span> 服装进销存</div>
    <el-menu :default-active="route.path" router @select="onSelect">
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
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const emit = defineEmits(['navigate'])
const route = useRoute()

function onSelect() {
  emit('navigate')
}
</script>

<style scoped>
.nav-menu { min-height: 100%; display: flex; flex-direction: column; }
.logo {
  height: 60px; display: flex; align-items: center; gap: 10px; padding: 0 20px; flex: none;
  color: #fff; font-weight: 700; font-size: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo .dot { width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, #5b6ef5, #b06ab3); display: inline-block; }
.nav-menu > :deep(.el-menu) {
  border-right: none; background: transparent; flex: 1; overflow-y: auto;
  scrollbar-width: none;
}
.nav-menu > :deep(.el-menu)::-webkit-scrollbar { display: none; }
.nav-menu :deep(.el-menu--inline) { overflow: visible; }
.nav-menu :deep(.el-menu-item), .nav-menu :deep(.el-sub-menu__title) { color: #aab1cc; height: 46px; }
.nav-menu :deep(.el-menu-item:hover), .nav-menu :deep(.el-sub-menu__title:hover) { background: rgba(255, 255, 255, 0.06); color: #fff; }
.nav-menu :deep(.el-menu-item.is-active) { color: #fff; background: linear-gradient(90deg, var(--brand), rgba(91, 110, 245, 0.35)); border-left: 3px solid #fff; }
</style>
