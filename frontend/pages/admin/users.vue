<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('admin.users.title')} | ${appName.value}`) })

const { user } = useAuth()

// Redirect non-admin users
watch(user, (u) => {
  if (u && !u.is_admin) navigateTo('/')
}, { immediate: true })

interface AdminUser {
  id: string
  username: string
  display_name: string | null
  email: string | null
  recovery_email: string | null
  is_admin: boolean
  is_active: boolean
  created_at: string | null
}

const activeTab = ref<'pending' | 'all'>('pending')
const pendingUsers = ref<AdminUser[]>([])
const allUsers = ref<AdminUser[]>([])
const loading = ref(false)
const actionLoading = ref<string | null>(null)

async function fetchPending() {
  try {
    pendingUsers.value = await $fetch<AdminUser[]>('/api/admin/users/pending')
  } catch {
    pendingUsers.value = []
  }
}

async function fetchAll() {
  try {
    allUsers.value = await $fetch<AdminUser[]>('/api/admin/users')
  } catch {
    allUsers.value = []
  }
}

async function loadData() {
  loading.value = true
  await Promise.all([fetchPending(), fetchAll()])
  loading.value = false
}

onMounted(loadData)

async function approveUser(userId: string) {
  actionLoading.value = userId
  try {
    await $fetch(`/api/admin/users/${userId}/approve`, { method: 'POST' })
    await loadData()
  } catch (e: any) {
    alert(e?.data?.detail || t('admin.users.approveError'))
  } finally {
    actionLoading.value = null
  }
}

async function rejectUser(userId: string) {
  if (!confirm(t('admin.users.confirmReject'))) return
  actionLoading.value = userId
  try {
    await $fetch(`/api/admin/users/${userId}/reject`, { method: 'POST' })
    await loadData()
  } catch (e: any) {
    alert(e?.data?.detail || t('admin.users.rejectError'))
  } finally {
    actionLoading.value = null
  }
}

async function deactivateUser(userId: string) {
  if (!confirm(t('admin.users.confirmDeactivate'))) return
  actionLoading.value = userId
  try {
    await $fetch(`/api/admin/users/${userId}/deactivate`, { method: 'POST' })
    await loadData()
  } catch (e: any) {
    alert(e?.data?.detail || t('admin.users.deactivateError'))
  } finally {
    actionLoading.value = null
  }
}

async function toggleAdmin(u: AdminUser) {
  const newRole = !u.is_admin
  const name = u.display_name || u.username
  const msg = newRole
    ? t('admin.users.confirmGrantAdmin', { name })
    : t('admin.users.confirmRevokeAdmin', { name })
  if (!confirm(msg)) return
  actionLoading.value = u.id
  try {
    await $fetch(`/api/admin/users/${u.id}/set-role`, {
      method: 'POST',
      body: { is_admin: newRole },
    })
    await loadData()
  } catch (e: any) {
    alert(e?.data?.detail || t('admin.users.roleChangeError'))
  } finally {
    actionLoading.value = null
  }
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div v-if="user?.is_admin" class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight">{{ $t('admin.users.title') }}</h1>
      <p class="text-muted-foreground mt-1">{{ $t('admin.users.subtitle') }}</p>
    </div>

    <!-- Admin sub tabs -->
    <div class="flex items-center justify-between mb-6 border-b">
      <div class="flex gap-1">
        <NuxtLink
          to="/admin/dashboard"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('nav.dashboard') }}
        </NuxtLink>
        <NuxtLink
          to="/admin/users"
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-primary text-primary"
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
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px border-transparent text-muted-foreground hover:text-foreground"
        >
          {{ $t('admin.settings.title') }}
        </NuxtLink>
      </div>
    </div>

    <!-- User tabs -->
    <div class="flex gap-1 mb-6 border-b">
      <button
        @click="activeTab = 'pending'"
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === 'pending'
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        {{ $t('admin.users.tabs.pending') }}
        <span
          v-if="pendingUsers.length > 0"
          class="ml-1.5 inline-flex items-center justify-center h-5 min-w-5 px-1.5 rounded-full text-xs font-medium bg-destructive text-destructive-foreground"
        >
          {{ pendingUsers.length }}
        </span>
      </button>
      <button
        @click="activeTab = 'all'"
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === 'all'
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        {{ $t('admin.users.tabs.all') }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <svg class="h-6 w-6 animate-spin text-muted-foreground" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Pending users tab -->
    <div v-else-if="activeTab === 'pending'">
      <div v-if="pendingUsers.length === 0" class="text-center py-12 text-muted-foreground">
        {{ $t('admin.users.pendingEmpty') }}
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="u in pendingUsers"
          :key="u.id"
          class="flex items-center justify-between p-4 rounded-lg border bg-card"
        >
          <div class="space-y-1">
            <div class="font-medium">{{ u.display_name || u.username }}</div>
            <div class="text-sm text-muted-foreground">
              {{ u.username }} &middot; {{ u.email }}
            </div>
            <div v-if="u.recovery_email" class="text-xs text-muted-foreground">
              {{ $t('admin.users.recoveryEmail') }} {{ u.recovery_email }}
            </div>
            <div class="text-xs text-muted-foreground">
              {{ formatDate(u.created_at) }}
            </div>
          </div>
          <div class="flex gap-2 shrink-0">
            <UiButton
              size="sm"
              @click="approveUser(u.id)"
              :disabled="actionLoading === u.id"
            >
              {{ $t('admin.users.approve') }}
            </UiButton>
            <UiButton
              size="sm"
              variant="outline"
              class="text-destructive hover:text-destructive"
              @click="rejectUser(u.id)"
              :disabled="actionLoading === u.id"
            >
              {{ $t('admin.users.reject') }}
            </UiButton>
          </div>
        </div>
      </div>
    </div>

    <!-- All users tab -->
    <div v-else-if="activeTab === 'all'">
      <div v-if="allUsers.length === 0" class="text-center py-12 text-muted-foreground">
        {{ $t('admin.users.allEmpty') }}
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b">
              <th class="text-left py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.user') }}</th>
              <th class="text-left py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.email') }}</th>
              <th class="text-left py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.status') }}</th>
              <th class="text-left py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.role') }}</th>
              <th class="text-left py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.joinedAt') }}</th>
              <th class="text-right py-3 px-4 font-medium text-muted-foreground">{{ $t('admin.users.table.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in allUsers" :key="u.id" class="border-b last:border-0">
              <td class="py-3 px-4">
                <div class="font-medium">{{ u.display_name || u.username }}</div>
                <div class="text-xs text-muted-foreground">{{ u.username }}</div>
              </td>
              <td class="py-3 px-4 text-muted-foreground">{{ u.email }}</td>
              <td class="py-3 px-4">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="u.is_active
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'"
                >
                  {{ u.is_active ? $t('common.status.active') : $t('common.status.inactive') }}
                </span>
              </td>
              <td class="py-3 px-4">
                <button
                  v-if="u.is_active && u.id !== user?.id"
                  @click="toggleAdmin(u)"
                  :disabled="actionLoading === u.id"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer transition-colors"
                  :class="u.is_admin
                    ? 'bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'"
                >
                  {{ u.is_admin ? $t('common.role.admin') : $t('common.role.user') }}
                </button>
                <span
                  v-else-if="u.is_admin"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                >
                  {{ $t('common.role.admin') }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                >
                  {{ $t('common.role.user') }}
                </span>
              </td>
              <td class="py-3 px-4 text-muted-foreground text-xs">{{ formatDate(u.created_at) }}</td>
              <td class="py-3 px-4 text-right">
                <UiButton
                  v-if="u.is_active && u.id !== user?.id"
                  size="sm"
                  variant="outline"
                  class="text-destructive hover:text-destructive"
                  @click="deactivateUser(u.id)"
                  :disabled="actionLoading === u.id"
                >
                  {{ $t('admin.users.deactivate') }}
                </UiButton>
                <UiButton
                  v-else-if="!u.is_active"
                  size="sm"
                  @click="approveUser(u.id)"
                  :disabled="actionLoading === u.id"
                >
                  {{ $t('admin.users.activate') }}
                </UiButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
