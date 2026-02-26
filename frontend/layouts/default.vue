<script setup lang="ts">
const { fetchModules, loaded } = usePlatform()
const { addToast } = useToast()

const moduleError = ref(false)

onMounted(async () => {
  if (!loaded.value) {
    try {
      await fetchModules()
    } catch (e: any) {
      console.error('[Layout] fetchModules failed:', e)
      moduleError.value = true
      addToast('warning', '모듈 정보를 불러오지 못했습니다. 일부 기능이 제한될 수 있습니다.')
    }
  }
})

onErrorCaptured((err: Error) => {
  console.error('[Layout Error]', err)
  addToast('error', err.message || '화면을 표시하는 중 오류가 발생했습니다.')
  return false
})
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <LayoutAppHeader />

    <!-- Module loading error banner -->
    <div
      v-if="moduleError"
      class="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-2 text-sm text-yellow-700 dark:text-yellow-400 flex items-center gap-2"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 flex-shrink-0">
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <span>모듈 정보를 불러오지 못했습니다. 일부 기능이 제한될 수 있습니다.</span>
      <button
        class="ml-auto text-yellow-700 dark:text-yellow-400 hover:text-yellow-900 dark:hover:text-yellow-200 transition-colors"
        @click="moduleError = false"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
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
