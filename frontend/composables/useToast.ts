/**
 * Toast composable — singleton pattern (like useNotifications.ts).
 * Queue-based toast notifications with auto-dismiss.
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration: number
}

// Module-level singleton state
const toasts = ref<Toast[]>([])
let idCounter = 0

export function useToast() {
  function addToast(type: ToastType, message: string, duration: number = 5000) {
    const id = `toast-${++idCounter}-${Date.now()}`
    const toast: Toast = { id, type, message, duration }
    toasts.value = [...toasts.value, toast]

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return {
    toasts: readonly(toasts),
    addToast,
    removeToast,
  }
}
