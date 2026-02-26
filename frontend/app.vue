<script setup lang="ts">
const { fetchAppConfig } = useAppConfig()
const { addToast } = useToast()

fetchAppConfig()

onErrorCaptured((err: Error) => {
  console.error('[Global Error Boundary]', err)
  addToast('error', err.message || '예기치 않은 오류가 발생했습니다.')
  return false
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <UiToast />
</template>
