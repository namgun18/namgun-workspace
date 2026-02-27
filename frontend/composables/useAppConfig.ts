const appName = ref('Workspace')
const domain = ref('localhost')
const appUrl = ref('')
const giteaUrl = ref('')
const brandLogo = ref('')
const brandColor = ref('#3B82F6')
const defaultTheme = ref('system')
const favicon = ref('')
const registrationMode = ref('approval')
const announcement = ref('')
const announcementType = ref('info')
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
        default_theme: string
        favicon: string
        registration_mode: string
        announcement: string
        announcement_type: string
      }>('/api/health')
      appName.value = data.service || 'Workspace'
      domain.value = data.domain || 'localhost'
      appUrl.value = data.app_url || ''
      giteaUrl.value = data.gitea_url || ''
      brandLogo.value = data.brand_logo || ''
      brandColor.value = data.brand_color || '#3B82F6'
      defaultTheme.value = data.default_theme || 'system'
      favicon.value = data.favicon || ''
      registrationMode.value = data.registration_mode || 'approval'
      announcement.value = data.announcement || ''
      announcementType.value = data.announcement_type || 'info'
      loaded.value = true
    } catch {
      // fallback to defaults
    }
  }

  async function refetchAppConfig() {
    loaded.value = false
    await fetchAppConfig()
  }

  return {
    appName: readonly(appName),
    domain: readonly(domain),
    appUrl: readonly(appUrl),
    giteaUrl: readonly(giteaUrl),
    brandLogo: readonly(brandLogo),
    brandColor: readonly(brandColor),
    defaultTheme: readonly(defaultTheme),
    favicon: readonly(favicon),
    registrationMode: readonly(registrationMode),
    announcement: readonly(announcement),
    announcementType: readonly(announcementType),
    fetchAppConfig,
    refetchAppConfig,
  }
}
