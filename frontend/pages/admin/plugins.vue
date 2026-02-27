<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('admin.plugins.title')} | ${appName.value}`) })

const route = useRoute()
const { user } = useAuth()

interface PluginInfo {
  id: string
  name: string
  name_en: string
  icon: string
  route: string
  api_prefix: string
  version: string
  description: string
  author: string
  enabled: boolean
}

const plugins = ref<PluginInfo[]>([])
const loading = ref(false)
const toggling = ref<string | null>(null)

async function fetchPlugins() {
  loading.value = true
  try {
    const data = await $fetch<{ plugins: PluginInfo[] }>('/api/admin/plugins')
    plugins.value = data.plugins
  } catch (e: any) {
    console.error('fetchPlugins error:', e)
  } finally {
    loading.value = false
  }
}

async function onToggle(pluginId: string, currentEnabled: boolean) {
  toggling.value = pluginId
  try {
    await $fetch(`/api/admin/plugins/${pluginId}`, {
      method: 'PATCH',
      body: { enabled: !currentEnabled },
    })
    const p = plugins.value.find(x => x.id === pluginId)
    if (p) p.enabled = !currentEnabled
    // Refresh platform modules so navigation updates
    const { fetchModules } = usePlatform()
    await fetchModules()
  } catch (e: any) {
    console.error('toggle plugin failed:', e)
  } finally {
    toggling.value = null
  }
}

const iconMap: Record<string, string> = {
  'edit-3': 'M12 20h9 M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z',
  puzzle: 'M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5',
  folder: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z',
}

onMounted(() => {
  if (user.value?.is_admin) fetchPlugins()
})

watch(() => user.value?.is_admin, (isAdmin) => {
  if (!isAdmin) navigateTo('/')
})
</script>

<template>
  <div v-if="user?.is_admin" class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('admin.plugins.title') }}</h1>
      <p class="text-muted-foreground mt-1">{{ $t('admin.plugins.subtitle') }}</p>
    </div>

    <!-- Admin sub tabs -->
    <div class="flex items-center mb-6 border-b">
      <div class="flex gap-1">
        <NuxtLink
          to="/admin/dashboard"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('nav.dashboard') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/users"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.users.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/modules"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.modules.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/plugins"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-primary text-primary"
        >
          {{ $t('admin.plugins.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/settings"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.settings.title') }}
        </NuxtLink>
      </div>
    </div>

    <!-- Plugin list -->
    <div class="max-w-3xl space-y-3">
      <div v-if="loading" class="text-center py-12 text-muted-foreground">
        {{ $t('common.loading') }}
      </div>

      <div v-else-if="plugins.length === 0" class="text-center py-12">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
             class="h-12 w-12 mx-auto mb-3 text-muted-foreground/40">
          <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5" />
        </svg>
        <p class="text-muted-foreground">{{ $t('admin.plugins.empty') }}</p>
        <p class="text-sm text-muted-foreground/70 mt-1">{{ $t('admin.plugins.emptyHint') }}</p>
      </div>

      <div
        v-else
        v-for="plugin in plugins"
        :key="plugin.id"
        class="flex items-center justify-between p-4 border rounded-lg bg-card"
      >
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center"
               :class="plugin.enabled ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="h-5 w-5">
              <path :d="iconMap[plugin.icon] || iconMap['puzzle']" />
            </svg>
          </div>
          <div>
            <h3 class="font-medium">{{ plugin.name }}</h3>
            <p class="text-xs text-muted-foreground">
              v{{ plugin.version }}
              <span v-if="plugin.author"> &middot; {{ plugin.author }}</span>
            </p>
            <p v-if="plugin.description" class="text-xs text-muted-foreground/70 mt-0.5">{{ plugin.description }}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs px-2 py-0.5 rounded-full"
                :class="plugin.enabled ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-muted text-muted-foreground'">
            {{ plugin.enabled ? $t('admin.plugins.active') : $t('admin.plugins.inactive') }}
          </span>
          <button
            @click="onToggle(plugin.id, plugin.enabled)"
            :disabled="toggling === plugin.id"
            class="relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            :class="plugin.enabled ? 'bg-primary' : 'bg-muted'"
          >
            <span
              class="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
              :class="plugin.enabled ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="flex items-center justify-center h-96 text-muted-foreground">
    {{ $t('error.adminRequired') }}
  </div>
</template>
