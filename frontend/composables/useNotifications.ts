/**
 * Notifications composable — singleton pattern (like useChat.ts).
 * Manages @mention notifications + browser Notification API.
 */

export interface AppNotification {
  id: string
  user_id: string
  type: 'mention' | 'system'
  title: string
  body: string
  link: string | null
  is_read: boolean
  created_at: string
}

// Module-level singleton state
const notifications = ref<AppNotification[]>([])
const unreadCount = ref(0)
const showDropdown = ref(false)

export function useNotifications() {
  async function fetchNotifications() {
    try {
      const data = await $fetch<{ notifications: AppNotification[]; unread_count: number }>(
        '/api/chat/notifications'
      )
      notifications.value = data.notifications
      unreadCount.value = data.unread_count
    } catch (e: any) {
      console.error('fetchNotifications error:', e)
    }
  }

  async function markAsRead(ids?: string[]) {
    try {
      await $fetch('/api/chat/notifications/read', {
        method: 'POST',
        body: { notification_ids: ids || null },
      })
      if (ids) {
        for (const n of notifications.value) {
          if (ids.includes(n.id)) n.is_read = true
        }
        unreadCount.value = Math.max(0, unreadCount.value - ids.length)
      }
    } catch (e: any) {
      console.error('markAsRead error:', e)
    }
  }

  async function markAllAsRead() {
    try {
      await $fetch('/api/chat/notifications/read-all', {
        method: 'POST',
      })
      for (const n of notifications.value) {
        n.is_read = true
      }
      unreadCount.value = 0
    } catch (e: any) {
      console.error('markAllAsRead error:', e)
    }
  }

  function handleNotificationEvent(notif: AppNotification) {
    // Prepend to list
    notifications.value = [notif, ...notifications.value]
    unreadCount.value++

    // Browser Notification
    if (import.meta.client && Notification.permission === 'granted') {
      try {
        const n = new Notification(notif.title, {
          body: notif.body,
          icon: '/favicon.ico',
          tag: notif.id,
        })
        n.onclick = () => {
          window.focus()
          if (notif.link) {
            navigateTo(notif.link)
          }
          n.close()
        }
      } catch {
        // Notification API not available
      }
    }
  }

  function requestBrowserPermission() {
    if (!import.meta.client) return
    if (typeof Notification === 'undefined') return
    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }

  return {
    notifications: readonly(notifications),
    unreadCount: readonly(unreadCount),
    showDropdown,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    handleNotificationEvent,
    requestBrowserPermission,
  }
}
