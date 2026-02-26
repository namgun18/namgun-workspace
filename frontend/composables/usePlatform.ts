export interface PlatformModule {
  id: string
  name: string
  icon: string
  route: string
  type: string
  requires: string[]
  enabled: boolean
}

const modules = ref<PlatformModule[]>([])
const loaded = ref(false)

export function usePlatform() {
  async function fetchModules() {
    try {
      const data = await $fetch<{ modules: PlatformModule[] }>('/api/platform/modules')
      modules.value = data.modules
      loaded.value = true
    } catch (e: any) {
      console.error('fetchModules error:', e)
    }
  }

  function isModuleEnabled(id: string): boolean {
    const mod = modules.value.find(m => m.id === id)
    return mod?.enabled ?? true
  }

  const enabledModules = computed(() =>
    modules.value.filter(m => m.enabled)
  )

  async function toggleModule(id: string, enabled: boolean) {
    try {
      await $fetch(`/api/admin/modules/${id}`, {
        method: 'PATCH',
        body: { enabled },
      })
      const mod = modules.value.find(m => m.id === id)
      if (mod) mod.enabled = enabled
    } catch (e: any) {
      console.error('toggleModule error:', e)
      throw e
    }
  }

  return {
    modules: readonly(modules),
    loaded: readonly(loaded),
    enabledModules,
    fetchModules,
    isModuleEnabled,
    toggleModule,
  }
}
