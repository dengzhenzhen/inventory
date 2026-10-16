export const imgUrl = (path) => (path ? '/static/' + path : '')

export const fmtMoney = (n) =>
  (Number(n) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })

export const today = () => new Date().toISOString().slice(0, 10)
