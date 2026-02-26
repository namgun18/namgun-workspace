<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const { nativeLogin, user } = useAuth()
const { appName } = useAppConfig()
const route = useRoute()

const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const error = ref('')
const submitting = ref(false)

// Redirect destination after login (from query param or default to dashboard)
const redirectTo = computed(() => {
  const r = route.query.redirect as string | undefined
  if (!r) return '/'
  // Allow relative paths (e.g. /oauth/authorize?...)
  if (r.startsWith('/')) return r
  // Allow HTTPS URLs from our domain (strict hostname check)
  if (r.startsWith('https://')) {
    try {
      const parsed = new URL(r)
      if (parsed.hostname === window.location.hostname || parsed.hostname.endsWith(`.${window.location.hostname}`)) return r
    } catch { /* invalid URL */ }
  }
  return '/'
})

// If already logged in, redirect
watch(user, (u) => {
  if (u) {
    const dest = redirectTo.value
    if (dest.startsWith('https://') || dest.startsWith('/oauth/')) {
      if (import.meta.client) {
        window.location.href = dest
      } else {
        navigateTo(dest, { external: true })
      }
    } else {
      navigateTo(dest)
    }
  }
}, { immediate: true })

async function handleSubmit() {
  if (!username.value.trim() || !password.value) {
    error.value = t('auth.enterCredentials')
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await nativeLogin(username.value.trim(), password.value, rememberMe.value)
    const dest = redirectTo.value
    if (dest.startsWith('https://') || dest.startsWith('/oauth/')) {
      window.location.href = dest
    } else {
      navigateTo(dest)
    }
  } catch (e: any) {
    const detail = e?.data?.detail || ''
    const statusCode = e?.statusCode || e?.status || 0
    if (detail) {
      error.value = detail
    } else if (statusCode === 401) {
      error.value = t('auth.invalidCredentials')
    } else if (statusCode === 502) {
      error.value = t('auth.authServerUnavailable')
    } else {
      error.value = t('auth.loginError')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-sm space-y-6">
    <div class="text-center space-y-2">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto text-primary">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
      <h1 class="text-2xl font-bold">{{ appName }}</h1>
      <p class="text-sm text-muted-foreground">
        {{ $t('auth.loginRequired') }}
      </p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label for="username" class="block text-sm font-medium mb-1.5">{{ $t('auth.usernameOrEmail') }}</label>
        <input
          id="username"
          v-model="username"
          type="text"
          autocomplete="username"
          :placeholder="$t('auth.usernameOrEmailPlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
          autofocus
        />
      </div>

      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label for="password" class="block text-sm font-medium">{{ $t('auth.password') }}</label>
          <NuxtLink to="/forgot-password" class="text-xs text-primary hover:underline">{{ $t('auth.forgotPassword') }}</NuxtLink>
        </div>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          :placeholder="$t('auth.passwordPlaceholder')"
          class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
        />
      </div>

      <div class="flex items-center gap-2">
        <input
          id="rememberMe"
          v-model="rememberMe"
          type="checkbox"
          class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary/50"
        />
        <label for="rememberMe" class="text-sm text-muted-foreground select-none cursor-pointer">{{ $t('auth.rememberMe') }}</label>
      </div>

      <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

      <UiButton
        type="submit"
        class="w-full"
        size="lg"
        :disabled="submitting"
      >
        <svg v-if="submitting" class="h-4 w-4 mr-2 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ submitting ? $t('auth.loggingIn') : $t('auth.login') }}
      </UiButton>

      <p class="text-center text-sm text-muted-foreground">
        {{ $t('auth.noAccount') }}
        <NuxtLink to="/register" class="text-primary hover:underline font-medium">{{ $t('auth.register') }}</NuxtLink>
      </p>
    </form>

  </div>
</template>
