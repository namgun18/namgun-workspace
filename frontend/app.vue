<script setup lang="ts">
const { fetchAppConfig, brandColor } = useAppConfig()
const { addToast } = useToast()
const { t } = useI18n()

fetchAppConfig()

onErrorCaptured((err: Error) => {
  console.error('[Global Error Boundary]', err)
  addToast('error', err.message || t('error.unexpectedError'))
  return false
})

// Inject brand color as CSS variable
watchEffect(() => {
  if (import.meta.client) {
    document.documentElement.style.setProperty('--brand-color', brandColor.value)
  }
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <UiToast />
</template>
