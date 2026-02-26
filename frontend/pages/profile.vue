<script setup lang="ts">
import type { Signature } from '~/composables/useMailSignature'

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
const { user, updateProfile, changePassword, uploadAvatar } = useAuth()

useHead({ title: computed(() => `${t('profile.title')} | ${appName.value}`) })
const domain = import.meta.client ? window.location.hostname : 'localhost'
const { signatures, loading: sigLoading, fetchSignatures, createSignature, updateSignature, deleteSignature } = useMailSignature()

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '').slice(0, 100)
}

// Avatar
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const avatarError = ref('')

async function handleAvatarChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  avatarError.value = ''
  avatarUploading.value = true
  try {
    await uploadAvatar(file)
  } catch (err: any) {
    avatarError.value = err?.data?.detail || t('profile.avatarUploadError')
  } finally {
    avatarUploading.value = false
    if (target) target.value = ''
  }
}

// Profile form
const profileForm = reactive({
  display_name: user.value?.display_name || '',
  recovery_email: user.value?.recovery_email || '',
})
const profileError = ref('')
const profileSuccess = ref('')
const profileSubmitting = ref(false)

// Password form
const passwordForm = reactive({
  current: '',
  newPassword: '',
  confirm: '',
})
const passwordError = ref('')
const passwordSuccess = ref('')
const passwordSubmitting = ref(false)

// Signature management
const showSigForm = ref(false)
const editingSig = ref<Signature | null>(null)
const sigForm = reactive({ name: '', html_content: '', is_default: false })
const sigError = ref('')
const sigSubmitting = ref(false)

onMounted(() => {
  fetchSignatures()
})

function openSigCreate() {
  editingSig.value = null
  sigForm.name = ''
  sigForm.html_content = ''
  sigForm.is_default = false
  sigError.value = ''
  showSigForm.value = true
}

function openSigEdit(sig: Signature) {
  editingSig.value = sig
  sigForm.name = sig.name
  sigForm.html_content = sig.html_content
  sigForm.is_default = sig.is_default
  sigError.value = ''
  showSigForm.value = true
}

async function handleSigSubmit() {
  if (!sigForm.name.trim() || !sigForm.html_content.trim()) {
    sigError.value = t('profile.sigNameAndContentRequired')
    return
  }
  sigSubmitting.value = true
  sigError.value = ''
  try {
    if (editingSig.value) {
      await updateSignature(editingSig.value.id, {
        name: sigForm.name,
        html_content: sigForm.html_content,
        is_default: sigForm.is_default,
      })
    } else {
      await createSignature({
        name: sigForm.name,
        html_content: sigForm.html_content,
        is_default: sigForm.is_default,
      })
    }
    showSigForm.value = false
  } catch (e: any) {
    sigError.value = e?.data?.detail || t('profile.sigSaveError')
  } finally {
    sigSubmitting.value = false
  }
}

async function handleSigDelete(id: string) {
  if (!confirm(t('profile.sigDeleteConfirm'))) return
  await deleteSignature(id)
}

async function handleSetDefault(id: string) {
  await updateSignature(id, { is_default: true })
}

// Track original recovery_email for change detection
const originalRecoveryEmail = ref(user.value?.recovery_email || '')

// Sync profile form when user loads
watch(user, (u) => {
  if (u) {
    profileForm.display_name = u.display_name || ''
    profileForm.recovery_email = u.recovery_email || ''
    originalRecoveryEmail.value = u.recovery_email || ''
  }
}, { immediate: true })

async function handleProfileSubmit() {
  profileError.value = ''
  profileSuccess.value = ''
  profileSubmitting.value = true

  try {
    const updates: { display_name?: string; recovery_email?: string } = {}
    if (profileForm.display_name !== (user.value?.display_name || '')) {
      updates.display_name = profileForm.display_name.trim()
    }
    if (profileForm.recovery_email !== originalRecoveryEmail.value) {
      updates.recovery_email = profileForm.recovery_email.trim()
    }

    if (Object.keys(updates).length === 0) {
      profileError.value = t('profile.noChanges')
      return
    }

    await updateProfile(updates)
    originalRecoveryEmail.value = profileForm.recovery_email
    profileSuccess.value = t('profile.updateSuccess')
  } catch (e: any) {
    const detail = e?.data?.detail
    if (Array.isArray(detail)) {
      profileError.value = detail.map((d: any) => d.msg?.replace('Value error, ', '') || d.msg).join(', ')
    } else {
      profileError.value = typeof detail === 'string' ? detail : t('profile.updateError')
    }
  } finally {
    profileSubmitting.value = false
  }
}

async function handlePasswordSubmit() {
  passwordError.value = ''
  passwordSuccess.value = ''

  if (!passwordForm.current || !passwordForm.newPassword) {
    passwordError.value = t('validation.allFieldsRequired')
    return
  }

  if (passwordForm.newPassword !== passwordForm.confirm) {
    passwordError.value = t('profile.newPasswordMismatch')
    return
  }

  if (passwordForm.newPassword.length < 8) {
    passwordError.value = t('validation.passwordTooShort')
    return
  }

  passwordSubmitting.value = true
  try {
    await changePassword(passwordForm.current, passwordForm.newPassword)
    passwordSuccess.value = t('profile.passwordChangeSuccess')
    passwordForm.current = ''
    passwordForm.newPassword = ''
    passwordForm.confirm = ''
  } catch (e: any) {
    passwordError.value = e?.data?.detail || t('profile.passwordChangeError')
  } finally {
    passwordSubmitting.value = false
  }
}
</script>

<template>
  <div class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-4">
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('profile.title') }}</h1>
      <p class="text-muted-foreground mt-1">{{ $t('profile.subtitle') }}</p>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- Profile section -->
      <div class="rounded-lg border bg-card p-6 space-y-4">
        <h2 class="text-lg font-semibold">{{ $t('profile.sectionUserInfo') }}</h2>

        <!-- Avatar -->
        <div class="flex items-center gap-4">
          <UiAvatar
            :src="user?.avatar_url"
            :alt="user?.display_name || user?.username || ''"
            :fallback="(user?.display_name || user?.username || '?').charAt(0).toUpperCase()"
            class="h-16 w-16 text-xl"
          />
          <div>
            <button
              type="button"
              @click="avatarInput?.click()"
              :disabled="avatarUploading"
              class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {{ avatarUploading ? $t('profile.avatarUploading') : $t('profile.avatarChange') }}
            </button>
            <p class="mt-1 text-xs text-muted-foreground">{{ $t('profile.avatarHint') }}</p>
            <p v-if="avatarError" class="text-xs text-destructive mt-0.5">{{ avatarError }}</p>
          </div>
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" @change="handleAvatarChange" />
        </div>

        <form @submit.prevent="handleProfileSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1.5 text-muted-foreground">{{ $t('fields.username') }}</label>
            <input
              :value="user?.username"
              disabled
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-muted cursor-not-allowed"
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-1.5 text-muted-foreground">{{ $t('fields.email') }}</label>
            <input
              :value="user?.email"
              disabled
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-muted cursor-not-allowed"
            />
          </div>

          <div>
            <label for="display_name" class="block text-sm font-medium mb-1.5">{{ $t('fields.displayName') }}</label>
            <input
              id="display_name"
              v-model="profileForm.display_name"
              type="text"
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
          </div>

          <div>
            <label for="recovery_email" class="block text-sm font-medium mb-1.5">{{ $t('fields.recoveryEmail') }}</label>
            <input
              id="recovery_email"
              v-model="profileForm.recovery_email"
              type="email"
              :placeholder="$t('register.recoveryEmailPlaceholder')"
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
            <p class="mt-1 text-xs text-muted-foreground">{{ $t('profile.recoveryEmailHint') }}</p>
          </div>

          <p v-if="profileError" class="text-sm text-destructive">{{ profileError }}</p>
          <p v-if="profileSuccess" class="text-sm text-green-600 dark:text-green-400">{{ profileSuccess }}</p>

          <UiButton type="submit" :disabled="profileSubmitting">
            {{ profileSubmitting ? $t('common.saving') : $t('common.save') }}
          </UiButton>
        </form>
      </div>

      <!-- Signature section -->
      <div class="rounded-lg border bg-card p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">{{ $t('profile.sectionSignatures') }}</h2>
          <button
            @click="openSigCreate"
            class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {{ $t('profile.sigNew') }}
          </button>
        </div>

        <!-- Signature list -->
        <div v-if="sigLoading" class="text-sm text-muted-foreground">{{ $t('common.loading') }}</div>
        <div v-else-if="signatures.length === 0" class="text-sm text-muted-foreground">
          {{ $t('profile.sigEmpty') }}
        </div>
        <div v-else class="space-y-2 max-h-[200px] overflow-auto">
          <div
            v-for="sig in signatures"
            :key="sig.id"
            class="flex items-center gap-3 p-3 border rounded-lg"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-medium text-sm">{{ sig.name }}</span>
                <span v-if="sig.is_default" class="px-1.5 py-0.5 text-xs rounded bg-primary/10 text-primary">{{ $t('common.default') }}</span>
              </div>
              <div class="text-xs text-muted-foreground mt-1 truncate">{{ stripHtml(sig.html_content) }}</div>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                v-if="!sig.is_default"
                @click="handleSetDefault(sig.id)"
                class="px-2 py-1 text-xs rounded hover:bg-accent"
                :title="$t('profile.sigSetDefaultTitle')"
              >{{ $t('profile.sigSetDefault') }}</button>
              <button
                @click="openSigEdit(sig)"
                class="px-2 py-1 text-xs rounded hover:bg-accent"
              >{{ $t('common.edit') }}</button>
              <button
                @click="handleSigDelete(sig.id)"
                class="px-2 py-1 text-xs rounded hover:bg-accent text-destructive"
              >{{ $t('common.delete') }}</button>
            </div>
          </div>
        </div>

        <!-- Signature form (inline) -->
        <div v-if="showSigForm" class="border rounded-lg p-4 space-y-3 bg-muted/30">
          <h3 class="text-sm font-medium">{{ editingSig ? $t('profile.sigEditTitle') : $t('profile.sigNew') }}</h3>
          <div>
            <label class="block text-sm mb-1">{{ $t('profile.sigNameLabel') }}</label>
            <input
              v-model="sigForm.name"
              type="text"
              :placeholder="$t('profile.sigNamePlaceholder')"
              class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">{{ $t('profile.sigContentLabel') }}</label>
            <textarea
              v-model="sigForm.html_content"
              rows="4"
              placeholder="<p>홍길동<br>회사명</p>"
              class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono resize-none"
            />
          </div>
          <div class="flex items-center gap-2">
            <input
              id="sigDefault"
              v-model="sigForm.is_default"
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-primary"
            />
            <label for="sigDefault" class="text-sm">{{ $t('profile.sigSetDefaultLabel') }}</label>
          </div>
          <p v-if="sigError" class="text-sm text-destructive">{{ sigError }}</p>
          <div class="flex gap-2">
            <button
              @click="handleSigSubmit"
              :disabled="sigSubmitting"
              class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {{ sigSubmitting ? $t('common.saving') : $t('common.save') }}
            </button>
            <button
              @click="showSigForm = false"
              class="px-3 py-1.5 text-sm rounded-md hover:bg-accent"
            >{{ $t('common.cancel') }}</button>
          </div>
        </div>
      </div>

      <!-- Sync settings section -->
      <div class="rounded-lg border bg-card p-6 space-y-4">
        <h2 class="text-lg font-semibold">{{ $t('profile.sectionSync') }}</h2>
        <p class="text-sm text-muted-foreground">{{ $t('profile.syncDescription') }}</p>

        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('profile.caldavLabel') }}</label>
            <div class="flex items-center gap-2">
              <input
                :value="`https://mail.${domain}/dav/calendars/${user?.email || ''}/`"
                readonly
                class="flex-1 px-3 py-2 text-sm border rounded-lg bg-muted font-mono cursor-text"
              />
              <button
                @click="navigator.clipboard.writeText(`https://mail.${domain}/dav/calendars/${user?.email || ''}/`)"
                class="px-3 py-2 text-sm border rounded-lg hover:bg-accent transition-colors shrink-0"
                :title="$t('common.copy')"
                :aria-label="$t('common.copy')"
              >
                {{ $t('common.copy') }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('profile.carddavLabel') }}</label>
            <div class="flex items-center gap-2">
              <input
                :value="`https://mail.${domain}/dav/addressbooks/${user?.email || ''}/`"
                readonly
                class="flex-1 px-3 py-2 text-sm border rounded-lg bg-muted font-mono cursor-text"
              />
              <button
                @click="navigator.clipboard.writeText(`https://mail.${domain}/dav/addressbooks/${user?.email || ''}/`)"
                class="px-3 py-2 text-sm border rounded-lg hover:bg-accent transition-colors shrink-0"
                :title="$t('common.copy')"
                :aria-label="$t('common.copy')"
              >
                {{ $t('common.copy') }}
              </button>
            </div>
          </div>

          <div class="text-xs text-muted-foreground space-y-1">
            <p>{{ $t('profile.syncUsernameHint', { email: user?.email || '' }) }}</p>
            <p>{{ $t('profile.syncPasswordHint') }}</p>
          </div>
        </div>
      </div>

      <!-- Password section -->
      <div class="rounded-lg border bg-card p-6 space-y-4">
        <h2 class="text-lg font-semibold">{{ $t('profile.sectionPasswordChange') }}</h2>

        <form @submit.prevent="handlePasswordSubmit" class="space-y-4">
          <div>
            <label for="current_password" class="block text-sm font-medium mb-1.5">{{ $t('fields.currentPassword') }}</label>
            <input
              id="current_password"
              v-model="passwordForm.current"
              type="password"
              autocomplete="current-password"
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
          </div>

          <div>
            <label for="new_password" class="block text-sm font-medium mb-1.5">{{ $t('fields.newPassword') }}</label>
            <input
              id="new_password"
              v-model="passwordForm.newPassword"
              type="password"
              autocomplete="new-password"
              :placeholder="$t('resetPassword.newPasswordPlaceholder')"
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
          </div>

          <div>
            <label for="confirm_password" class="block text-sm font-medium mb-1.5">{{ $t('fields.newPasswordConfirm') }}</label>
            <input
              id="confirm_password"
              v-model="passwordForm.confirm"
              type="password"
              autocomplete="new-password"
              class="w-full px-3 py-2.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
          </div>

          <p v-if="passwordError" class="text-sm text-destructive">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="text-sm text-green-600 dark:text-green-400">{{ passwordSuccess }}</p>

          <UiButton type="submit" :disabled="passwordSubmitting">
            {{ passwordSubmitting ? $t('profile.passwordChanging') : $t('profile.passwordChangeButton') }}
          </UiButton>
        </form>
      </div>
    </div>
  </div>
</template>
