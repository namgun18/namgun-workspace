<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const { appName, registrationMode } = useAppConfig()
const { register } = useAuth()

// Block access if registration is closed
watch(registrationMode, (mode) => {
  if (mode === 'closed') navigateTo('/login')
}, { immediate: true })

useHead({ title: computed(() => `${t('register.title')} | ${appName.value}`) })

const form = reactive({
  username: '',
  password: '',
  passwordConfirm: '',
  display_name: '',
  recovery_email: '',
})
const error = ref('')
const submitting = ref(false)
const success = ref(false)

const domain = import.meta.client ? window.location.hostname : 'localhost'
const emailPreview = computed(() =>
  form.username ? `${form.username.toLowerCase()}@${domain}` : ''
)

async function handleSubmit() {
  error.value = ''

  if (!form.username || !form.password || !form.display_name || !form.recovery_email) {
    error.value = t('validation.allFieldsRequired')
    return
  }

  if (form.password !== form.passwordConfirm) {
    error.value = t('validation.passwordMismatch')
    return
  }

  if (form.password.length < 8) {
    error.value = t('validation.passwordTooShort')
    return
  }

  if (form.recovery_email.endsWith(`@${domain}`)) {
    error.value = t('validation.recoveryEmailMustBeExternal')
    return
  }

  submitting.value = true
  try {
    await register({
      username: form.username.trim().toLowerCase(),
      password: form.password,
      display_name: form.display_name.trim(),
      recovery_email: form.recovery_email.trim(),
    })
    success.value = true
  } catch (e: any) {
    const detail = e?.data?.detail
    if (Array.isArray(detail)) {
      error.value = detail.map((d: any) => d.msg?.replace('Value error, ', '') || d.msg).join(', ')
    } else if (typeof detail === 'string') {
      error.value = detail
    } else {
      error.value = t('register.errorGeneric')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm space-y-6">
    <div class="text-center space-y-2">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto text-primary" aria-hidden="true">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
      <h1 class="text-2xl font-bold">{{ $t('register.title') }}</h1>
      <p class="text-sm text-muted-foreground">
        {{ $t('register.subtitle') }}
      </p>
    </div>

    <!-- Success message -->
    <div v-if="success" class="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4 space-y-3">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5 text-green-600 dark:text-green-400" aria-hidden="true">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
        </svg>
        <p class="font-medium text-green-800 dark:text-green-200">{{ $t('register.successTitle') }}</p>
      </div>
      <p class="text-sm text-green-700 dark:text-green-300">
        {{ $t('register.successMessage') }}
      </p>
      <NuxtLink
        to="/login"
        class="inline-block text-sm font-medium text-primary hover:underline"
      >
        {{ $t('common.backToLogin') }}
      </NuxtLink>
    </div>

    <!-- Registration form -->
    <form v-else @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label for="username" class="block text-sm font-medium mb-1.5">{{ $t('fields.username') }}</label>
        <input
          id="username"
          v-model="form.username"
          type="text"
          autocomplete="username"
          :placeholder="$t('register.usernamePlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
          autofocus
        />
        <p v-if="emailPreview" class="mt-1 text-xs text-muted-foreground">
          {{ $t('register.emailPreviewLabel') }} <span class="font-medium">{{ emailPreview }}</span>
        </p>
      </div>

      <div>
        <label for="display_name" class="block text-sm font-medium mb-1.5">{{ $t('fields.displayName') }}</label>
        <input
          id="display_name"
          v-model="form.display_name"
          type="text"
          :placeholder="$t('register.displayNamePlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
        />
      </div>

      <div>
        <label for="password" class="block text-sm font-medium mb-1.5">{{ $t('fields.password') }}</label>
        <input
          id="password"
          v-model="form.password"
          type="password"
          autocomplete="new-password"
          :placeholder="$t('register.passwordPlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
        />
      </div>

      <div>
        <label for="passwordConfirm" class="block text-sm font-medium mb-1.5">{{ $t('fields.passwordConfirm') }}</label>
        <input
          id="passwordConfirm"
          v-model="form.passwordConfirm"
          type="password"
          autocomplete="new-password"
          :placeholder="$t('register.passwordConfirmPlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
        />
      </div>

      <div>
        <label for="recovery_email" class="block text-sm font-medium mb-1.5">{{ $t('fields.recoveryEmail') }}</label>
        <input
          id="recovery_email"
          v-model="form.recovery_email"
          type="email"
          :placeholder="$t('register.recoveryEmailPlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
        />
        <p class="mt-1 text-xs text-muted-foreground">
          {{ $t('register.recoveryEmailHint', { domain }) }}
        </p>
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
        {{ submitting ? $t('common.processing') : $t('register.submitButton') }}
      </UiButton>

      <p class="text-center text-sm text-muted-foreground">
        {{ $t('register.hasAccount') }}
        <NuxtLink to="/login" class="text-primary hover:underline font-medium">{{ $t('common.login') }}</NuxtLink>
      </p>
    </form>
  </div>
</template>
