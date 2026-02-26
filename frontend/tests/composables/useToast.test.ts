import { describe, it, expect, vi, beforeEach } from 'vitest'

// Provide Vue reactivity as global (Nuxt auto-imports ref/readonly)
import { ref, readonly } from 'vue'
;(globalThis as any).ref = ref
;(globalThis as any).readonly = readonly

// Must import AFTER globals are set so module-level ref() call works
const { useToast } = await import('~/composables/useToast')

describe('useToast', () => {
  beforeEach(() => {
    // Clear all toasts between tests
    const { toasts, removeToast } = useToast()
    toasts.value.forEach(t => removeToast(t.id))
  })

  it('addToast adds a toast to the queue', () => {
    const { toasts, addToast } = useToast()
    const before = toasts.value.length

    addToast('success', 'Test message', 0) // duration 0 = no auto-dismiss

    expect(toasts.value.length).toBe(before + 1)
    expect(toasts.value[toasts.value.length - 1].type).toBe('success')
    expect(toasts.value[toasts.value.length - 1].message).toBe('Test message')
  })

  it('removeToast removes a specific toast from the queue', () => {
    const { toasts, addToast, removeToast } = useToast()

    addToast('info', 'To be removed', 0)
    const toastId = toasts.value[toasts.value.length - 1].id

    removeToast(toastId)

    const found = toasts.value.find(t => t.id === toastId)
    expect(found).toBeUndefined()
  })

  it('auto-dismisses toast after timeout', () => {
    vi.useFakeTimers()

    const { toasts, addToast } = useToast()
    addToast('warning', 'Temporary', 3000)

    const toastId = toasts.value[toasts.value.length - 1].id

    // Toast should still exist before timeout
    expect(toasts.value.find(t => t.id === toastId)).toBeDefined()

    // Advance time past the duration
    vi.advanceTimersByTime(3000)

    // Toast should be removed after timeout
    expect(toasts.value.find(t => t.id === toastId)).toBeUndefined()

    vi.useRealTimers()
  })
})
