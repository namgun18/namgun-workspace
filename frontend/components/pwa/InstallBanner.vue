<script setup lang="ts">
const { canInstall, isInstalled, promptInstall } = usePwa()
const { t } = useI18n()
const dismissed = ref(false)

async function handleInstall() {
  await promptInstall()
}
</script>

<template>
  <div
    v-if="canInstall && !isInstalled && !dismissed"
    class="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-50 bg-card border rounded-lg shadow-lg p-4 flex items-start gap-3"
  >
    <div class="shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-primary">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
      </svg>
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium">{{ t('pwa.installTitle') }}</p>
      <p class="text-xs text-muted-foreground mt-0.5">{{ t('pwa.installDescription') }}</p>
      <div class="flex items-center gap-2 mt-2">
        <button
          @click="handleInstall"
          class="px-3 py-1 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          {{ t('pwa.install') }}
        </button>
        <button
          @click="dismissed = true"
          class="px-3 py-1 text-xs font-medium rounded-md hover:bg-accent transition-colors text-muted-foreground"
        >
          {{ t('pwa.dismiss') }}
        </button>
      </div>
    </div>
  </div>
</template>
