/**
 * PWA composable — install prompt + push notification subscription.
 */

const installPromptEvent = ref<any>(null)
const canInstall = ref(false)
const isInstalled = ref(false)
const pushSupported = ref(false)
const pushSubscribed = ref(false)

export function usePwa() {
  function init() {
    if (!import.meta.client) return

    // Detect if already installed (standalone mode)
    isInstalled.value = window.matchMedia('(display-mode: standalone)').matches
      || (navigator as any).standalone === true

    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault()
      installPromptEvent.value = e
      canInstall.value = true
    })

    // Detect successful install
    window.addEventListener('appinstalled', () => {
      canInstall.value = false
      isInstalled.value = true
      installPromptEvent.value = null
    })

    // Check push support
    pushSupported.value = 'PushManager' in window && 'serviceWorker' in navigator
  }

  async function promptInstall(): Promise<boolean> {
    if (!installPromptEvent.value) return false
    installPromptEvent.value.prompt()
    const { outcome } = await installPromptEvent.value.userChoice
    installPromptEvent.value = null
    canInstall.value = false
    return outcome === 'accepted'
  }

  async function subscribePush(): Promise<boolean> {
    if (!pushSupported.value) return false
    try {
      const registration = await navigator.serviceWorker.ready

      // Get VAPID public key from server
      const { vapid_public_key } = await $fetch<{ vapid_public_key: string }>('/api/push/vapid-key')
      if (!vapid_public_key) return false

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid_public_key),
      })

      // Send subscription to server
      await $fetch('/api/push/subscribe', {
        method: 'POST',
        body: subscription.toJSON(),
      })

      pushSubscribed.value = true
      return true
    } catch (e) {
      console.error('Push subscription failed:', e)
      return false
    }
  }

  async function unsubscribePush(): Promise<boolean> {
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (subscription) {
        await subscription.unsubscribe()
        await $fetch('/api/push/unsubscribe', {
          method: 'POST',
          body: subscription.toJSON(),
        })
      }
      pushSubscribed.value = false
      return true
    } catch (e) {
      console.error('Push unsubscribe failed:', e)
      return false
    }
  }

  async function checkPushSubscription() {
    if (!pushSupported.value) return
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      pushSubscribed.value = !!subscription
    } catch {
      pushSubscribed.value = false
    }
  }

  return {
    canInstall: readonly(canInstall),
    isInstalled: readonly(isInstalled),
    pushSupported: readonly(pushSupported),
    pushSubscribed: readonly(pushSubscribed),
    init,
    promptInstall,
    subscribePush,
    unsubscribePush,
    checkPushSubscription,
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
