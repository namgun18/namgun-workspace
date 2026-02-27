<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('admin.modules.title')} | ${appName.value}`) })

const { user } = useAuth()
const { modules, toggleModule, fetchModules } = usePlatform()

const toggling = ref<string | null>(null)

async function onToggle(moduleId: string, currentEnabled: boolean) {
  toggling.value = moduleId
  try {
    await toggleModule(moduleId, !currentEnabled)
  } catch (e: any) {
    console.error('toggle failed:', e)
  } finally {
    toggling.value = null
  }
}

const iconMap: Record<string, string> = {
  mail: 'M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6',
  'message-square': 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  video: 'M23 7l-7 5 7 5V7z M16 3H1v18h15V3z',
  folder: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z',
  calendar: 'M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z M16 2v4 M8 2v4 M3 10h18',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75 M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  'git-branch': 'M6 3v12 M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M18 9a9 9 0 0 1-9 9',
}

onMounted(async () => {
  if (modules.value.length === 0) await fetchModules()
})
</script>

<template>
  <div v-if="user?.is_admin" class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('admin.modules.title') }}</h1>
      <p class="text-muted-foreground mt-1">{{ $t('admin.modules.description') }}</p>
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
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-primary text-primary"
        >
          {{ $t('admin.modules.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/settings"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.settings.title') }}
        </NuxtLink>
      </div>
    </div>

    <div class="max-w-3xl space-y-3">
      <div
        v-for="mod in modules"
        :key="mod.id"
        class="flex items-center justify-between p-4 border rounded-lg bg-card"
      >
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center"
               :class="mod.enabled ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="h-5 w-5">
              <path :d="iconMap[mod.icon] || iconMap['folder']" />
            </svg>
          </div>
          <div>
            <h3 class="font-medium">{{ mod.name }}</h3>
            <p class="text-xs text-muted-foreground">{{ mod.route }} &middot; {{ mod.type }}</p>
          </div>
        </div>
        <button
          @click="onToggle(mod.id, mod.enabled)"
          :disabled="toggling === mod.id"
          class="relative w-11 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          :class="mod.enabled ? 'bg-primary' : 'bg-muted'"
        >
          <span
            class="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
            :class="mod.enabled ? 'translate-x-5' : 'translate-x-0'"
          />
        </button>
      </div>
    </div>
  </div>
  <div v-else class="flex items-center justify-center h-96 text-muted-foreground">
    {{ $t('error.adminRequired') }}
  </div>
</template>
