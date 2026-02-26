const appName = ref('Workspace')
const domain = ref('localhost')
const appUrl = ref('')
const giteaUrl = ref('')
const brandLogo = ref('')
const brandColor = ref('#3B82F6')
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
        brand_logo: string
        brand_color: string
      }>('/api/health')
      appName.value = data.service || 'Workspace'
      domain.value = data.domain || 'localhost'
      appUrl.value = data.app_url || ''
      giteaUrl.value = data.gitea_url || ''
      brandLogo.value = data.brand_logo || ''
      brandColor.value = data.brand_color || '#3B82F6'
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
    brandLogo: readonly(brandLogo),
    brandColor: readonly(brandColor),
    fetchAppConfig,
  }
}
