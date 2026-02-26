<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const { appName } = useAppConfig()
const { forgotPassword } = useAuth()

useHead({ title: computed(() => `${t('forgotPassword.title')} | ${appName.value}`) })

const username = ref('')
const error = ref('')
const submitting = ref(false)
const success = ref(false)
const successMessage = ref('')

async function handleSubmit() {
  if (!username.value.trim()) {
    error.value = t('forgotPassword.usernameRequired')
    return
  }

  submitting.value = true
  error.value = ''

  try {
    const result = await forgotPassword(username.value.trim())
    success.value = true
    successMessage.value = result.message
  } catch (e: any) {
    error.value = e?.data?.detail || t('error.genericError')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm space-y-6">
    <div class="text-center space-y-2">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto text-primary" aria-hidden="true">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
      <h1 class="text-2xl font-bold">{{ $t('forgotPassword.title') }}</h1>
      <p class="text-sm text-muted-foreground">
        {{ $t('forgotPassword.subtitle') }}
      </p>
    </div>

    <!-- Success message -->
    <div v-if="success" class="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4 space-y-3">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5 text-green-600 dark:text-green-400" aria-hidden="true">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
        </svg>
        <p class="font-medium text-green-800 dark:text-green-200">{{ $t('forgotPassword.successTitle') }}</p>
      </div>
      <p class="text-sm text-green-700 dark:text-green-300">{{ successMessage }}</p>
      <NuxtLink
        to="/login"
        class="inline-block text-sm font-medium text-primary hover:underline"
      >
        {{ $t('common.backToLogin') }}
      </NuxtLink>
    </div>

    <!-- Form -->
    <form v-else @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label for="username" class="block text-sm font-medium mb-1.5">{{ $t('fields.username') }}</label>
        <input
          id="username"
          v-model="username"
          type="text"
          autocomplete="username"
          :placeholder="$t('forgotPassword.usernamePlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
          autofocus
        />
      </div>

      <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

      <UiButton
        type="submit"
        class="w-full"
        size="lg"
        :disabled="submitting"
      >
        <svg v-if="submitting" class="h-4 w-4 mr-2 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ submitting ? $t('common.processing') : $t('forgotPassword.submitButton') }}
      </UiButton>

      <p class="text-center text-sm text-muted-foreground">
        <NuxtLink to="/login" class="text-primary hover:underline font-medium">{{ $t('common.returnToLogin') }}</NuxtLink>
      </p>
    </form>
  </div>
</template>
