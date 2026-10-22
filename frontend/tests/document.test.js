import { beforeEach, expect, test, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
vi.mock('../src/api', () => ({
  documentApi: { list: vi.fn(), create: vi.fn(), audit: vi.fn(), preview: vi.fn() },
  dictApi: { list: vi.fn() }, stockApi: { current: vi.fn() }, productApi: { list: vi.fn(), getByCode: vi.fn() }, uploadApi: { image: vi.fn() }, downloadFile: vi.fn(),
}))
vi.mock('element-plus', () => ({ ElMessage: { success: vi.fn(), warning: vi.fn() }, ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() } }))
import { documentApi, dictApi, stockApi } from '../src/api'
import DocumentCenter from '../src/views/DocumentCenter.vue'
const box = { template: '<div><slot /><slot name="footer" /></div>' }
const stubs = Object.fromEntries(['ElSelect','ElOption','ElButton','ElPagination','ElDatePicker','ElInput','ElForm','ElFormItem','ElDialog','ElAlert','ElInputNumber','ElRadioGroup','ElRadio'].map(k => [k, box]))
Object.assign(stubs, { ElTable: true, ElTableColumn: true, ProductPicker: true, ScanDialog: true })
beforeEach(() => {
  dictApi.list.mockResolvedValue([]); documentApi.list.mockResolvedValue({ items: [], total: 0 })
  stockApi.current.mockResolvedValue({ stock: 10, stock_version: 1 })
})
test('multiple products post atomically and a network retry reuses the same key', async () => {
  const wrapper = mount(DocumentCenter, { props: { initialKind: 'sale' }, global: { stubs, directives: { loading: () => {} } } })
  await flushPromises(); wrapper.vm.newOrder()
  wrapper.vm.form.lines = [
    { style_code: 'A', size: 'M', quantity: 1, price: 10, counted: 0, adjustment_sign: 1 },
    { style_code: 'B', size: 'L', quantity: 2, price: 20, counted: 0, adjustment_sign: 1 },
  ]
  documentApi.create.mockRejectedValueOnce(new Error('timeout')).mockResolvedValue({ id: 5 })
  await expect(wrapper.vm.save()).rejects.toThrow('timeout')
  await wrapper.vm.save()
  const [first, second] = documentApi.create.mock.calls
  expect(first[0].lines).toHaveLength(2); expect(first[1]).toBe(second[1])
  expect(wrapper.vm.editing).toBe(false)
  wrapper.unmount()
})
test('changing sale product clears stale price before resolving', async () => {
  const wrapper = mount(DocumentCenter, { props: { initialKind: 'sale' }, global: { stubs, directives: { loading: () => {} } } })
  await flushPromises(); const line={ style_code: 'B', size: '', price: 99 }
  wrapper.vm.resolved(line, null); expect(line.price).toBe(0)
  wrapper.vm.resolved(line, { retail_price: 25 }); expect(line.price).toBe(25)
  wrapper.unmount()
})
