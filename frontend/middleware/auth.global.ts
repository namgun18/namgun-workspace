export default defineNuxtRouteMiddleware(async (to) => {
  const { user, loading } = useAuth()

  // Allow public pages
  const publicPages = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email']
  if (publicPages.includes(to.path)) return
  if (to.path.startsWith('/meetings/join/')) return
  if (to.path.startsWith('/meetings/room/')) return

  // If not loading and no user, check demo mode
  if (!loading.value && !user.value) {
    const { demoMode, fetchAppConfig } = useAppConfig()
    await fetchAppConfig()

    if (demoMode.value) {
      // Auto-login via demo endpoint
      try {
        await $fetch('/api/auth/demo-login', { method: 'POST' })
        // Reload user after demo login
        const { fetchUser } = useAuth()
        await fetchUser()
        return
      } catch {
        // Fallback to login page
      }
    }

    return navigateTo('/login')
  }
})
