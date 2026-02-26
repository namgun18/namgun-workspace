<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const { appName } = useAppConfig()
const route = useRoute()
const status = ref<'loading' | 'success' | 'error'>('loading')
const message = ref('')

useHead({ title: computed(() => `${t('verifyEmail.title')} | ${appName.value}`) })

onMounted(async () => {
  const token = route.query.token as string
  if (!token) {
    status.value = 'error'
    message.value = t('verifyEmail.invalidToken')
    return
  }

  try {
    const data = await $fetch<{ message: string }>('/api/auth/verify-email', {
      params: { token },
    })
    status.value = 'success'
    message.value = data.message
  } catch (e: any) {
    status.value = 'error'
    message.value = e?.data?.detail || t('verifyEmail.errorGeneric')
  }
})
</script>

<template>
  <div class="w-full max-w-sm space-y-6">
    <div class="text-center space-y-2">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto text-primary" aria-hidden="true">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
      <h1 class="text-2xl font-bold">{{ $t('verifyEmail.title') }}</h1>
    </div>

    <!-- Loading -->
    <div v-if="status === 'loading'" class="text-center space-y-3">
      <div class="h-8 w-8 mx-auto animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <p class="text-sm text-muted-foreground">{{ $t('verifyEmail.loading') }}</p>
    </div>

    <!-- Success -->
    <div v-else-if="status === 'success'" class="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4 space-y-3">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5 text-green-600 dark:text-green-400" aria-hidden="true">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
        </svg>
        <p class="font-medium text-green-800 dark:text-green-200">{{ $t('verifyEmail.successTitle') }}</p>
      </div>
      <p class="text-sm text-green-700 dark:text-green-300">{{ message }}</p>
      <NuxtLink to="/login" class="inline-block text-sm font-medium text-primary hover:underline">
        {{ $t('common.goToLogin') }}
      </NuxtLink>
    </div>

    <!-- Error -->
    <div v-else class="rounded-lg border border-destructive/30 bg-destructive/10 p-4 space-y-3">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5 text-destructive" aria-hidden="true">
          <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        <p class="font-medium text-destructive">{{ $t('verifyEmail.errorTitle') }}</p>
      </div>
      <p class="text-sm">{{ message }}</p>
      <NuxtLink to="/register" class="inline-block text-sm font-medium text-primary hover:underline">
        {{ $t('verifyEmail.goToRegister') }}
      </NuxtLink>
    </div>
  </div>
</template>
