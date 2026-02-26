const appName = ref('Workspace')
const domain = ref('localhost')
const appUrl = ref('')
const giteaUrl = ref('')
const loaded = ref(false)

export function useAppConfig() {
  async function fetchAppConfig() {
    if (loaded.value) return
    try {
      const data = await $fetch<{
        service: string
        domain: string
        app_url: string
        gitea_url: string
      }>('/api/health')
      appName.value = data.service || 'Workspace'
      domain.value = data.domain || 'localhost'
      appUrl.value = data.app_url || ''
      giteaUrl.value = data.gitea_url || ''
      loaded.value = true
    } catch {
      // fallback to defaults
    }
  }

  return {
    appName: readonly(appName),
    domain: readonly(domain),
    appUrl: readonly(appUrl),
    giteaUrl: readonly(giteaUrl),
    fetchAppConfig,
  }
}
