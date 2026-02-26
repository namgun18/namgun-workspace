/**
 * Global middleware: redirect to dashboard if navigating to a disabled module page.
 */
export default defineNuxtRouteMiddleware((to) => {
  const { isModuleEnabled, loaded } = usePlatform()

  // Don't guard until modules are loaded
  if (!loaded.value) return

  // Module route mapping
  const moduleRoutes: Record<string, string> = {
    '/mail': 'mail',
    '/chat': 'chat',
    '/meetings': 'meetings',
    '/files': 'files',
    '/calendar': 'calendar',
    '/contacts': 'contacts',
    '/git': 'git',
  }

  for (const [prefix, moduleId] of Object.entries(moduleRoutes)) {
    if (to.path === prefix || to.path.startsWith(prefix + '/')) {
      if (!isModuleEnabled(moduleId)) {
        return navigateTo('/')
      }
      break
    }
  }
})
