let id = 0
const listeners = new Set()

export function toast(msg, type = 'info') {
  const t = { id: ++id, msg, type }
  listeners.forEach(fn => fn('add', t))
  setTimeout(() => listeners.forEach(fn => fn('remove', t)), 3200)
}

export function onToast(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
