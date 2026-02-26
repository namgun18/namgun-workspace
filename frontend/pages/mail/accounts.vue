<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('mail.accounts.title')} | ${appName.value}`) })

const { accounts, fetchAccounts } = useMail()

const showForm = ref(false)
const editing = ref<string | null>(null)
const testing = ref<string | null>(null)
const testResult = ref<any>(null)
const saving = ref(false)

const hasBuiltin = computed(() => accounts.value.some(a => a.is_builtin))

const form = ref({
  display_name: '',
  email: '',
  imap_host: '',
  imap_port: 993,
  imap_security: 'ssl',
  smtp_host: '',
  smtp_port: 587,
  smtp_security: 'starttls',
  username: '',
  password: '',
  is_default: false,
})

function resetForm() {
  form.value = {
    display_name: '', email: '',
    imap_host: '', imap_port: 993, imap_security: 'ssl',
    smtp_host: '', smtp_port: 587, smtp_security: 'starttls',
    username: '', password: '', is_default: false,
  }
  editing.value = null
}

function openCreate() {
  resetForm()
  showForm.value = true
}

function openEdit(account: any) {
  editing.value = account.id
  form.value = {
    display_name: account.display_name,
    email: account.email,
    imap_host: account.imap_host,
    imap_port: account.imap_port,
    imap_security: account.imap_security,
    smtp_host: account.smtp_host,
    smtp_port: account.smtp_port,
    smtp_security: account.smtp_security,
    username: account.username,
    password: '',
    is_default: account.is_default,
  }
  showForm.value = true
}

async function saveAccount() {
  saving.value = true
  try {
    if (editing.value) {
      const body: any = { ...form.value }
      if (!body.password) delete body.password
      await $fetch(`/api/mail/accounts/${editing.value}`, { method: 'PATCH', body })
    } else {
      await $fetch('/api/mail/accounts', { method: 'POST', body: form.value })
    }
    showForm.value = false
    resetForm()
    await fetchAccounts()
  } catch (e: any) {
    alert(e.data?.detail || t('mail.accounts.saveFail'))
  } finally {
    saving.value = false
  }
}

async function deleteAccount(id: string) {
  if (!confirm(t('mail.accounts.deleteConfirm'))) return
  try {
    await $fetch(`/api/mail/accounts/${id}`, { method: 'DELETE' })
    await fetchAccounts()
  } catch (e: any) {
    alert(e.data?.detail || t('mail.accounts.deleteFail'))
  }
}

async function testConnection(id: string) {
  testing.value = id
  testResult.value = null
  try {
    testResult.value = await $fetch(`/api/mail/accounts/${id}/test`, { method: 'POST' })
  } catch (e: any) {
    testResult.value = { error: e.data?.detail || t('mail.accounts.testFail') }
  } finally {
    testing.value = null
  }
}

onMounted(() => fetchAccounts())
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">{{ $t('mail.accounts.title') }}</h1>
        <p class="text-muted-foreground text-sm mt-1">
          {{ hasBuiltin ? $t('mail.accounts.descBuiltin') : $t('mail.accounts.descExternal') }}
        </p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90">
        {{ $t('mail.accounts.add') }}
      </button>
    </div>

    <!-- Account list -->
    <div class="space-y-3 mb-6">
      <div
        v-for="acct in accounts"
        :key="acct.id"
        class="border rounded-lg p-4 bg-card"
      >
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="font-medium">{{ acct.display_name }}</h3>
              <span v-if="acct.is_builtin" class="text-xs px-2 py-0.5 bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded">{{ $t('mail.accounts.builtin') }}</span>
            </div>
            <p class="text-sm text-muted-foreground">{{ acct.email }}</p>
            <p v-if="!acct.is_builtin" class="text-xs text-muted-foreground mt-1">
              IMAP: {{ acct.imap_host }}:{{ acct.imap_port }} &middot;
              SMTP: {{ acct.smtp_host }}:{{ acct.smtp_port }}
            </p>
            <span v-if="acct.is_default" class="inline-block mt-1 text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">{{ $t('mail.accounts.default') }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button @click="testConnection(acct.id)" :disabled="testing === acct.id"
                    class="px-3 py-1.5 text-xs border rounded-md hover:bg-accent">
              {{ testing === acct.id ? $t('mail.accounts.testing') : $t('mail.accounts.test') }}
            </button>
            <template v-if="!acct.is_builtin">
              <button @click="openEdit(acct)" class="px-3 py-1.5 text-xs border rounded-md hover:bg-accent">{{ $t('common.edit') }}</button>
              <button @click="deleteAccount(acct.id)" class="px-3 py-1.5 text-xs border rounded-md hover:bg-destructive/10 text-destructive">{{ $t('common.delete') }}</button>
            </template>
          </div>
        </div>
        <div v-if="testResult && testing === null && testResult !== null" class="mt-3 text-sm">
          <template v-if="testResult.error">
            <p class="text-destructive">{{ testResult.error }}</p>
          </template>
          <template v-else>
            <p :class="testResult.imap?.ok ? 'text-green-600' : 'text-destructive'">
              IMAP: {{ testResult.imap?.message }}
            </p>
            <p :class="testResult.smtp?.ok ? 'text-green-600' : 'text-destructive'">
              SMTP: {{ testResult.smtp?.message }}
            </p>
          </template>
        </div>
      </div>
      <div v-if="accounts.length === 0" class="text-center py-12 text-muted-foreground">
        {{ $t('mail.accounts.empty') }}
      </div>
    </div>

    <!-- Add/Edit form modal -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showForm = false" role="dialog" aria-modal="true">
      <div class="bg-background border rounded-lg shadow-lg w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 class="text-lg font-bold mb-4">{{ editing ? $t('mail.accounts.editTitle') : $t('mail.accounts.addTitle') }}</h2>

        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.displayName') }}</label>
            <input v-model="form.display_name" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" :placeholder="$t('mail.accounts.displayName')" />
          </div>
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.email') }}</label>
            <input v-model="form.email" type="email" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="user@gmail.com" />
          </div>
          <hr />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm font-medium">{{ $t('mail.accounts.imapHost') }}</label>
              <input v-model="form.imap_host" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="imap.gmail.com" />
            </div>
            <div>
              <label class="text-sm font-medium">{{ $t('mail.accounts.imapPort') }}</label>
              <input v-model.number="form.imap_port" type="number" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.imapSecurity') }}</label>
            <select v-model="form.imap_security" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm">
              <option value="ssl">SSL/TLS</option>
              <option value="starttls">STARTTLS</option>
              <option value="none">{{ $t('common.none') }}</option>
            </select>
          </div>
          <hr />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm font-medium">{{ $t('mail.accounts.smtpHost') }}</label>
              <input v-model="form.smtp_host" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="smtp.gmail.com" />
            </div>
            <div>
              <label class="text-sm font-medium">{{ $t('mail.accounts.smtpPort') }}</label>
              <input v-model.number="form.smtp_port" type="number" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.smtpSecurity') }}</label>
            <select v-model="form.smtp_security" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm">
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="none">{{ $t('common.none') }}</option>
            </select>
          </div>
          <hr />
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.username') }}</label>
            <input v-model="form.username" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="user@gmail.com" />
          </div>
          <div>
            <label class="text-sm font-medium">{{ $t('mail.accounts.password') }}{{ editing ? ` ${$t('mail.accounts.passwordEditHint')}` : '' }}</label>
            <input v-model="form.password" type="password" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_default" type="checkbox" class="rounded" />
            {{ $t('mail.accounts.setDefault') }}
          </label>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button @click="showForm = false" class="px-4 py-2 border rounded-md text-sm hover:bg-accent">{{ $t('common.cancel') }}</button>
          <button @click="saveAccount" :disabled="saving" class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90">
            {{ saving ? $t('common.saving') : (editing ? $t('common.edit') : $t('common.add')) }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
