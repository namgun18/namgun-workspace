<script setup lang="ts">
definePageMeta({ layout: false })

const { t } = useI18n()
const { appName } = useAppConfig()
const error = useError()

useHead({ title: computed(() => `${t('common.error')} | ${appName.value}`) })

const statusCode = computed(() => error.value?.statusCode ?? 500)

const errorInfo = computed(() => {
  switch (statusCode.value) {
    case 404:
      return {
        title: t('error.404.title'),
        description: t('error.404.description'),
        icon: 'M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
      }
    case 500:
      return {
        title: t('error.500.title'),
        description: t('error.500.description'),
        icon: 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z',
      }
    default:
      return {
        title: t('error.default.title'),
        description: error.value?.message || t('error.default.description'),
        icon: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z',
      }
  }
})

function handleGoHome() {
  clearError({ redirect: '/' })
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background px-4">
    <div class="text-center max-w-md space-y-6">
      <!-- Icon -->
      <div class="flex justify-center">
        <div class="w-20 h-20 rounded-full bg-destructive/10 flex items-center justify-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="w-10 h-10 text-destructive"
            aria-hidden="true"
          >
            <path :d="errorInfo.icon" />
          </svg>
        </div>
      </div>

      <!-- Error code -->
      <p class="text-6xl font-bold text-foreground/20">
        {{ statusCode }}
      </p>

      <!-- Title & description -->
      <div class="space-y-2">
        <h1 class="text-xl font-semibold text-foreground">
          {{ errorInfo.title }}
        </h1>
        <p class="text-sm text-muted-foreground leading-relaxed">
          {{ errorInfo.description }}
        </p>
      </div>

      <!-- Details (dev) -->
      <p
        v-if="error?.message && statusCode !== 404"
        class="text-xs text-muted-foreground/60 bg-muted rounded-md px-3 py-2 break-all"
      >
        {{ error.message }}
      </p>

      <!-- Action -->
      <div>
        <button
          class="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-6 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm transition-all active:scale-[0.98]"
          @click="handleGoHome"
        >
          {{ $t('common.goHome') }}
        </button>
      </div>
    </div>
  </div>
</template>
