<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const { t } = useI18n()
const { appName } = useAppConfig()
const { user } = useAuth()
const { isModuleEnabled, loaded } = usePlatform()

const pluginId = computed(() => route.params.id as string)

// Redirect if module disabled
watch([pluginId, loaded], () => {
  if (loaded.value && !isModuleEnabled(pluginId.value)) {
    navigateTo('/')
  }
}, { immediate: true })

useHead({ title: computed(() => `${pluginId.value} | ${appName.value}`) })
</script>

<template>
  <div v-if="user" class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="text-center py-20 text-muted-foreground">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
           class="h-16 w-16 mx-auto mb-4 opacity-40">
        <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5" />
      </svg>
      <h2 class="text-lg font-medium mb-2">{{ $t('plugins.placeholder') }}</h2>
      <p class="text-sm">{{ $t('plugins.rebuildHint') }}</p>
    </div>
  </div>
</template>
