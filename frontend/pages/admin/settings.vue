<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName, refetchAppConfig } = useAppConfig()
useHead({ title: computed(() => `${t('admin.settings.title')} | ${appName.value}`) })

const { user } = useAuth()
const route = useRoute()

watch(user, (u) => {
  if (u && !u.is_admin) navigateTo('/')
}, { immediate: true })

// ── Branding ──
const branding = ref({ site_name: '', primary_color: '#3B82F6', logo_url: '', default_theme: 'system', favicon_url: '' })
const brandingSaving = ref(false)
const logoUploading = ref(false)
const logoFile = ref<File | null>(null)
const faviconUploading = ref(false)
const faviconFile = ref<File | null>(null)

async function loadBranding() {
  try {
    branding.value = await $fetch('/api/admin/settings/branding')
  } catch {}
}

async function saveBranding() {
  brandingSaving.value = true
  try {
    await $fetch('/api/admin/settings/branding', {
      method: 'PATCH',
      body: {
        site_name: branding.value.site_name,
        primary_color: branding.value.primary_color,
        default_theme: branding.value.default_theme,
      },
    })
    await refetchAppConfig()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    brandingSaving.value = false
  }
}

async function uploadLogo() {
  if (!logoFile.value) return
  logoUploading.value = true
  try {
    const form = new FormData()
    form.append('file', logoFile.value)
    const res = await $fetch<{ logo_url: string }>('/api/admin/settings/branding/logo', {
      method: 'POST',
      body: form,
    })
    branding.value.logo_url = res.logo_url
    logoFile.value = null
    await refetchAppConfig()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    logoUploading.value = false
  }
}

async function deleteLogo() {
  if (!confirm(t('admin.settings.branding.deleteLogoConfirm'))) return
  try {
    await $fetch('/api/admin/settings/branding/logo', { method: 'DELETE' })
    branding.value.logo_url = ''
    await refetchAppConfig()
  } catch {}
}

function onLogoSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    logoFile.value = input.files[0]
  }
}

function onFaviconSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    faviconFile.value = input.files[0]
  }
}

async function uploadFavicon() {
  if (!faviconFile.value) return
  faviconUploading.value = true
  try {
    const form = new FormData()
    form.append('file', faviconFile.value)
    const res = await $fetch<{ favicon_url: string }>('/api/admin/settings/branding/favicon', {
      method: 'POST',
      body: form,
    })
    branding.value.favicon_url = res.favicon_url
    faviconFile.value = null
    await refetchAppConfig()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    faviconUploading.value = false
  }
}

async function deleteFavicon() {
  if (!confirm(t('admin.settings.branding.deleteFaviconConfirm'))) return
  try {
    await $fetch('/api/admin/settings/branding/favicon', { method: 'DELETE' })
    branding.value.favicon_url = ''
    await refetchAppConfig()
  } catch {}
}

// ── General ──
const general = ref({
  registration_mode: 'approval',
  upload_max_size_mb: 1024,
  session_hours: 8,
  session_remember_days: 30,
  announcement: '',
  announcement_type: 'info',
  git_visibility: 'private',
})
const generalSaving = ref(false)

async function loadGeneral() {
  try {
    general.value = await $fetch('/api/admin/settings/general')
  } catch {}
}

async function saveGeneral() {
  generalSaving.value = true
  try {
    await $fetch('/api/admin/settings/general', {
      method: 'PATCH',
      body: general.value,
    })
    await refetchAppConfig()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    generalSaving.value = false
  }
}

// ── SMTP ──
const smtp = ref({ host: '', port: 587, security: 'starttls', user: '', password: '', from_addr: '' })
const smtpSaving = ref(false)
const smtpTesting = ref(false)
const smtpTestEmail = ref('')

async function loadSmtp() {
  try {
    smtp.value = await $fetch('/api/admin/settings/smtp')
  } catch {}
}

async function saveSmtp() {
  smtpSaving.value = true
  try {
    const body: Record<string, any> = {
      host: smtp.value.host,
      port: smtp.value.port,
      security: smtp.value.security,
      user: smtp.value.user,
      from_addr: smtp.value.from_addr,
    }
    // Only send password if changed from masked value
    if (smtp.value.password && !smtp.value.password.startsWith('•')) {
      body.password = smtp.value.password
    }
    await $fetch('/api/admin/settings/smtp', { method: 'PATCH', body })
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    smtpSaving.value = false
  }
}

async function testSmtp() {
  if (!smtpTestEmail.value) return
  smtpTesting.value = true
  try {
    const res = await $fetch<{ message: string }>('/api/admin/settings/smtp/test', {
      method: 'POST',
      body: { to_email: smtpTestEmail.value },
    })
    alert(res.message)
  } catch (e: any) {
    alert(e?.data?.detail || t('admin.settings.smtp.testFail'))
  } finally {
    smtpTesting.value = false
  }
}

// ── SSL ──
const ssl = ref<any>({ installed: false })
const sslUploading = ref(false)

async function loadSsl() {
  try {
    ssl.value = await $fetch('/api/admin/settings/ssl')
  } catch {}
}

async function uploadSsl(e: Event) {
  const form = e.target as HTMLFormElement
  const formData = new FormData(form)
  if (!formData.get('cert') || !formData.get('key')) return
  sslUploading.value = true
  try {
    const res = await $fetch<{ message: string }>('/api/admin/settings/ssl', {
      method: 'POST',
      body: formData,
    })
    alert(res.message)
    await loadSsl()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    sslUploading.value = false
  }
}

async function deleteSsl() {
  if (!confirm(t('admin.settings.ssl.deleteConfirm'))) return
  try {
    await $fetch('/api/admin/settings/ssl', { method: 'DELETE' })
    await loadSsl()
  } catch {}
}

onMounted(async () => {
  await Promise.all([loadBranding(), loadGeneral(), loadSmtp(), loadSsl()])
})
</script>

<template>
  <div v-if="user?.is_admin" class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('admin.settings.title') }}</h1>
      <p class="text-muted-foreground mt-1">{{ $t('admin.settings.subtitle') }}</p>
    </div>

    <!-- Admin sub tabs -->
    <div class="flex items-center mb-6 border-b">
      <div class="flex gap-1">
        <NuxtLink
          to="/admin/dashboard"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('nav.dashboard') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/users"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.users.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/modules"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.modules.title') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/settings"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
          :class="route.path === '/admin/settings'
            ? 'border-primary text-primary'
            : 'border-transparent text-muted-foreground hover:text-foreground'"
        >
          {{ $t('admin.settings.title') }}
        </NuxtLink>
      </div>
    </div>

    <div class="max-w-3xl space-y-6">
      <!-- Branding Card -->
      <div class="border rounded-lg bg-card p-6">
        <h2 class="text-lg font-semibold mb-4">{{ $t('admin.settings.branding.title') }}</h2>

        <!-- Logo -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-2">{{ $t('admin.settings.branding.logo') }}</label>
          <div class="flex items-center gap-4">
            <div class="w-16 h-16 border rounded-lg flex items-center justify-center bg-muted overflow-hidden">
              <img v-if="branding.logo_url" :src="branding.logo_url" class="max-w-full max-h-full object-contain" />
              <span v-else class="text-muted-foreground text-xs">No logo</span>
            </div>
            <div class="flex gap-2">
              <label class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md border cursor-pointer hover:bg-accent transition-colors">
                {{ $t('admin.settings.branding.uploadLogo') }}
                <input type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" class="hidden" @change="onLogoSelect" />
              </label>
              <UiButton v-if="logoFile" size="sm" @click="uploadLogo" :disabled="logoUploading">
                {{ logoUploading ? $t('common.processing') : $t('common.save') }}
              </UiButton>
              <UiButton v-if="branding.logo_url" size="sm" variant="outline" class="text-destructive" @click="deleteLogo">
                {{ $t('common.delete') }}
              </UiButton>
            </div>
          </div>
          <p v-if="logoFile" class="text-xs text-muted-foreground mt-1">{{ logoFile.name }}</p>
          <p class="text-xs text-muted-foreground mt-1">{{ $t('admin.settings.branding.logoHint') }}</p>
        </div>

        <!-- Site Name -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.branding.siteName') }}</label>
          <input
            v-model="branding.site_name"
            type="text"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <!-- Primary Color -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.branding.primaryColor') }}</label>
          <div class="flex items-center gap-3">
            <input
              v-model="branding.primary_color"
              type="color"
              class="w-10 h-10 rounded border cursor-pointer"
            />
            <input
              v-model="branding.primary_color"
              type="text"
              class="w-32 px-3 py-2 text-sm border rounded-md bg-background font-mono focus:outline-none focus:ring-2 focus:ring-primary"
              maxlength="7"
            />
          </div>
        </div>

        <!-- Default Theme -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.branding.defaultTheme') }}</label>
          <select
            v-model="branding.default_theme"
            class="w-48 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="system">{{ $t('admin.settings.branding.themeSystem') }}</option>
            <option value="light">{{ $t('admin.settings.branding.themeLight') }}</option>
            <option value="dark">{{ $t('admin.settings.branding.themeDark') }}</option>
          </select>
        </div>

        <!-- Favicon -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-2">{{ $t('admin.settings.branding.favicon') }}</label>
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 border rounded flex items-center justify-center bg-muted overflow-hidden">
              <img v-if="branding.favicon_url" :src="branding.favicon_url" class="max-w-full max-h-full object-contain" />
              <span v-else class="text-muted-foreground text-xs">-</span>
            </div>
            <div class="flex gap-2">
              <label class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md border cursor-pointer hover:bg-accent transition-colors">
                {{ $t('admin.settings.branding.uploadFavicon') }}
                <input type="file" accept=".ico,.png,.svg,image/x-icon,image/png,image/svg+xml" class="hidden" @change="onFaviconSelect" />
              </label>
              <UiButton v-if="faviconFile" size="sm" @click="uploadFavicon" :disabled="faviconUploading">
                {{ faviconUploading ? $t('common.processing') : $t('common.save') }}
              </UiButton>
              <UiButton v-if="branding.favicon_url" size="sm" variant="outline" class="text-destructive" @click="deleteFavicon">
                {{ $t('common.delete') }}
              </UiButton>
            </div>
          </div>
          <p v-if="faviconFile" class="text-xs text-muted-foreground mt-1">{{ faviconFile.name }}</p>
          <p class="text-xs text-muted-foreground mt-1">{{ $t('admin.settings.branding.faviconHint') }}</p>
        </div>

        <UiButton @click="saveBranding" :disabled="brandingSaving">
          {{ brandingSaving ? $t('common.saving') : $t('common.save') }}
        </UiButton>
      </div>

      <!-- General Card -->
      <div class="border rounded-lg bg-card p-6">
        <h2 class="text-lg font-semibold mb-4">{{ $t('admin.settings.general.title') }}</h2>

        <!-- Registration Mode -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.registrationMode') }}</label>
          <select
            v-model="general.registration_mode"
            class="w-48 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="open">{{ $t('admin.settings.general.regOpen') }}</option>
            <option value="approval">{{ $t('admin.settings.general.regApproval') }}</option>
            <option value="closed">{{ $t('admin.settings.general.regClosed') }}</option>
          </select>
          <p class="text-xs text-muted-foreground mt-1">{{ $t('admin.settings.general.registrationModeHint') }}</p>
        </div>

        <!-- Upload Max Size -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.uploadMaxSize') }}</label>
          <div class="flex items-center gap-2">
            <input
              v-model.number="general.upload_max_size_mb"
              type="number"
              min="1"
              max="10240"
              class="w-32 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <span class="text-sm text-muted-foreground">MB</span>
          </div>
        </div>

        <!-- Session Hours -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.sessionHours') }}</label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="general.session_hours"
                type="number"
                min="1"
                max="720"
                class="w-24 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span class="text-sm text-muted-foreground">{{ $t('admin.settings.general.hours') }}</span>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.sessionRememberDays') }}</label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="general.session_remember_days"
                type="number"
                min="1"
                max="365"
                class="w-24 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span class="text-sm text-muted-foreground">{{ $t('admin.settings.general.days') }}</span>
            </div>
          </div>
        </div>

        <!-- Announcement -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.announcement') }}</label>
          <input
            v-model="general.announcement"
            type="text"
            :placeholder="$t('admin.settings.general.announcementPlaceholder')"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.announcementType') }}</label>
          <select
            v-model="general.announcement_type"
            class="w-48 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="info">{{ $t('admin.settings.general.typeInfo') }}</option>
            <option value="warning">{{ $t('admin.settings.general.typeWarning') }}</option>
            <option value="error">{{ $t('admin.settings.general.typeError') }}</option>
          </select>
        </div>

        <!-- Git Visibility -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.general.gitVisibility') }}</label>
          <select
            v-model="general.git_visibility"
            class="w-48 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="private">{{ $t('admin.settings.general.gitPrivate') }}</option>
            <option value="public">{{ $t('admin.settings.general.gitPublic') }}</option>
          </select>
          <p class="text-xs text-muted-foreground mt-1">{{ $t('admin.settings.general.gitVisibilityHint') }}</p>
        </div>

        <UiButton @click="saveGeneral" :disabled="generalSaving">
          {{ generalSaving ? $t('common.saving') : $t('common.save') }}
        </UiButton>
      </div>

      <!-- SMTP Card -->
      <div class="border rounded-lg bg-card p-6">
        <h2 class="text-lg font-semibold mb-4">{{ $t('admin.settings.smtp.title') }}</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.host') }}</label>
            <input v-model="smtp.host" type="text" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.port') }}</label>
            <input v-model.number="smtp.port" type="number" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.security') }}</label>
            <select v-model="smtp.security" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary">
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="none">{{ $t('common.none') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.user') }}</label>
            <input v-model="smtp.user" type="text" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.password') }}</label>
            <input v-model="smtp.password" type="password" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.fromAddr') }}</label>
            <input v-model="smtp.from_addr" type="email" class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
        </div>

        <div class="flex gap-2 mb-4">
          <UiButton @click="saveSmtp" :disabled="smtpSaving">
            {{ smtpSaving ? $t('common.saving') : $t('common.save') }}
          </UiButton>
        </div>

        <!-- Test -->
        <div class="border-t pt-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.smtp.testTitle') }}</label>
          <div class="flex gap-2">
            <input
              v-model="smtpTestEmail"
              type="email"
              :placeholder="$t('admin.settings.smtp.testPlaceholder')"
              class="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <UiButton @click="testSmtp" :disabled="smtpTesting || !smtpTestEmail" variant="outline">
              {{ smtpTesting ? $t('common.sending') : $t('admin.settings.smtp.testButton') }}
            </UiButton>
          </div>
        </div>
      </div>

      <!-- SSL Card -->
      <div class="border rounded-lg bg-card p-6">
        <h2 class="text-lg font-semibold mb-4">{{ $t('admin.settings.ssl.title') }}</h2>

        <div v-if="ssl.installed" class="mb-4">
          <div class="grid grid-cols-2 gap-2 text-sm">
            <div class="text-muted-foreground">{{ $t('admin.settings.ssl.subject') }}</div>
            <div>{{ ssl.subject || '-' }}</div>
            <div class="text-muted-foreground">{{ $t('admin.settings.ssl.issuer') }}</div>
            <div>{{ ssl.issuer || '-' }}</div>
            <div class="text-muted-foreground">{{ $t('admin.settings.ssl.notAfter') }}</div>
            <div>{{ ssl.not_after || '-' }}</div>
          </div>
          <UiButton size="sm" variant="outline" class="text-destructive mt-3" @click="deleteSsl">
            {{ $t('admin.settings.ssl.deleteCert') }}
          </UiButton>
        </div>
        <div v-else class="mb-4 text-sm text-muted-foreground">
          {{ $t('admin.settings.ssl.noCert') }}
        </div>

        <form @submit.prevent="uploadSsl" class="border-t pt-4">
          <label class="block text-sm font-medium mb-1">{{ $t('admin.settings.ssl.uploadTitle') }}</label>
          <div class="space-y-2">
            <div>
              <label class="text-xs text-muted-foreground">{{ $t('admin.settings.ssl.certFile') }}</label>
              <input name="cert" type="file" accept=".pem,.crt,.cer" class="block w-full text-sm file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border file:border-border file:text-sm file:font-medium file:bg-background hover:file:bg-accent" />
            </div>
            <div>
              <label class="text-xs text-muted-foreground">{{ $t('admin.settings.ssl.keyFile') }}</label>
              <input name="key" type="file" accept=".pem,.key" class="block w-full text-sm file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border file:border-border file:text-sm file:font-medium file:bg-background hover:file:bg-accent" />
            </div>
          </div>
          <UiButton type="submit" class="mt-3" :disabled="sslUploading">
            {{ sslUploading ? $t('common.processing') : $t('admin.settings.ssl.upload') }}
          </UiButton>
          <p class="text-xs text-muted-foreground mt-2">{{ $t('admin.settings.ssl.nginxHint') }}</p>
        </form>
      </div>
    </div>
  </div>
</template>
