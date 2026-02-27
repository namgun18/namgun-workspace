<script setup lang="ts">
const { t } = useI18n()
const { fetchModules, loaded } = usePlatform()
const { announcement, announcementType } = useAppConfig()
const { addToast } = useToast()

const moduleError = ref(false)
const announcementDismissed = ref(false)

// Restore dismissed state from localStorage (key includes announcement text to reset on change)
watchEffect(() => {
  if (!import.meta.client) return
  const stored = localStorage.getItem('announcement-dismissed')
  announcementDismissed.value = stored === announcement.value
})

function dismissAnnouncement() {
  announcementDismissed.value = true
  if (import.meta.client) {
    localStorage.setItem('announcement-dismissed', announcement.value)
  }
}

const announcementClasses = computed(() => {
  const type = announcementType.value
  if (type === 'warning') return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-700 dark:text-yellow-400'
  if (type === 'error') return 'bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400'
  return 'bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-400'
})

onMounted(async () => {
  if (!loaded.value) {
    try {
      await fetchModules()
    } catch (e: any) {
      console.error('[Layout] fetchModules failed:', e)
      moduleError.value = true
      addToast('warning', t('error.moduleLoadFailed'))
    }
  }
})

onErrorCaptured((err: Error) => {
  console.error('[Layout Error]', err)
  addToast('error', err.message || t('error.renderError'))
  return false
})
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <LayoutAppHeader />

    <!-- Announcement banner -->
    <div
      v-if="announcement && !announcementDismissed"
      :class="['border-b px-4 py-2 text-sm flex items-center gap-2', announcementClasses]"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 flex-shrink-0" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </svg>
      <span class="flex-1">{{ announcement }}</span>
      <button
        class="hover:opacity-70 transition-opacity"
        @click="dismissAnnouncement"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4" aria-hidden="true">
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>

    <!-- Module loading error banner -->
    <div
      v-if="moduleError"
      class="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-2 text-sm text-yellow-700 dark:text-yellow-400 flex items-center gap-2"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 flex-shrink-0" aria-hidden="true">
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <span>{{ $t('error.moduleLoadFailed') }}</span>
      <button
        class="ml-auto text-yellow-700 dark:text-yellow-400 hover:text-yellow-900 dark:hover:text-yellow-200 transition-colors"
        @click="moduleError = false"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4" aria-hidden="true">
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>

    <main class="flex-1 min-h-0">
      <slot />
    </main>
  </div>
</template>
