<template>
  <el-select :model-value="modelValue" filterable remote :remote-method="search" :loading="loading" :allow-create="allowCreate" default-first-option placeholder="搜索或扫码款号" @update:model-value="choose" style="width:100%">
    <el-option v-for="p in choices" :key="p.id" :label="`${p.style_code} ${p.name || ''}`" :value="p.style_code" />
  </el-select>
</template>
<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { productApi } from '../api'
const props = defineProps({ modelValue: String, allowCreate: Boolean })
const emit = defineEmits(['update:modelValue', 'resolved'])
const choices = ref([]), loading = ref(false)
let timer, sequence = 0
function search(keyword) {
  clearTimeout(timer)
  const ticket = ++sequence
  timer = setTimeout(async () => {
    loading.value = true
    try { const result = await productApi.list({ keyword, page_size: 30 }); if (ticket === sequence) choices.value = result.items }
    finally { if (ticket === sequence) loading.value = false }
  }, 250)
}
function choose(value) { emit('update:modelValue', value) }
let resolveSequence = 0
watch(() => props.modelValue, async (code) => {
  const ticket = ++resolveSequence
  emit('resolved', null)
  if (!code) return
  try {
    // Lookup is independent of the current search page, including scanned products.
    const result = await (props.allowCreate ? productApi.getByCode(code, { silentNotFound: true }) : productApi.getByCode(code))
    if (ticket === resolveSequence) { if (!choices.value.some(p => p.id === result.id)) choices.value.unshift(result); emit('resolved', result) }
  } catch (_) { /* New purchase styles may be created when posting. */ }
}, { immediate: true })
search('')
onBeforeUnmount(() => { clearTimeout(timer); sequence++; resolveSequence++ })
</script>
