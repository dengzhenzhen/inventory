import { expect, test, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
vi.mock('../src/api', () => ({ productApi: { list: vi.fn(), getByCode: vi.fn() } }))
import { productApi } from '../src/api'
import ProductPicker from '../src/components/ProductPicker.vue'
const stubs = { ElSelect: { name: 'ElSelect', props: ['remoteMethod'], template: '<div><slot /></div>' }, ElOption: true }
afterEach(() => vi.useRealTimers())
test('scanned product is resolved directly even outside the first search page', async () => {
  vi.useFakeTimers(); productApi.list.mockResolvedValue({ items: [] })
  productApi.getByCode.mockResolvedValue({ id: 900, style_code: 'S900', retail_price: 99 })
  const wrapper = mount(ProductPicker, { props: { modelValue: 'S900' }, global: { stubs } })
  await flushPromises()
  expect(productApi.getByCode).toHaveBeenCalledWith('S900')
  expect(wrapper.emitted('resolved').at(-1)[0].retail_price).toBe(99)
  wrapper.unmount()
})
test('late product lookup cannot overwrite a newer selection', async () => {
  vi.useFakeTimers(); let first
  productApi.getByCode.mockImplementation(code => code === 'A' ? new Promise(resolve => { first = resolve }) : Promise.resolve({ id: 2, style_code: 'B', retail_price: 20 }))
  const wrapper = mount(ProductPicker, { props: { modelValue: 'A' }, global: { stubs } })
  await wrapper.setProps({ modelValue: 'B' }); await flushPromises()
  first({ id: 1, style_code: 'A', retail_price: 10 }); await flushPromises()
  expect(wrapper.emitted('resolved').at(-1)[0].style_code).toBe('B')
  wrapper.unmount()
})
