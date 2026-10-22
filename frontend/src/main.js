import { createApp } from 'vue'
import { ElAlert, ElAside, ElButton, ElCheckbox, ElCol, ElContainer, ElDatePicker, ElDialog, ElDivider, ElDrawer, ElEmpty, ElForm, ElFormItem, ElHeader, ElIcon, ElInput, ElInputNumber, ElMain, ElMenu, ElMenuItem, ElOption, ElPagination, ElProgress, ElRadio, ElRadioGroup, ElRow, ElSelect, ElSpace, ElSubMenu, ElSwitch, ElTabPane, ElTable, ElTableColumn, ElTabs, ElTag, ElLoading } from 'element-plus'
import 'element-plus/dist/index.css'
import { Camera, DataBoard, SoldOut, ShoppingCart, Box, Goods, TrendCharts, Setting, Expand, Close, Link, Cellphone, Iphone, CopyDocument, User, Lock } from '@element-plus/icons-vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)
for (const [key, component] of Object.entries({ Camera, DataBoard, SoldOut, ShoppingCart, Box, Goods, TrendCharts, Setting, Expand, Close, Link, Cellphone, Iphone, CopyDocument, User, Lock })) {
  app.component(key, component)
}
app.use(createPinia())
app.use(router)
for (const component of [ElAlert, ElAside, ElButton, ElCheckbox, ElCol, ElContainer, ElDatePicker, ElDialog, ElDivider, ElDrawer, ElEmpty, ElForm, ElFormItem, ElHeader, ElIcon, ElInput, ElInputNumber, ElMain, ElMenu, ElMenuItem, ElOption, ElPagination, ElProgress, ElRadio, ElRadioGroup, ElRow, ElSelect, ElSpace, ElSubMenu, ElSwitch, ElTabPane, ElTable, ElTableColumn, ElTabs, ElTag]) app.component(component.name, component)
app.use(ElLoading)
app.mount('#app')
