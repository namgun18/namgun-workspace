<script setup lang="ts">
const { t } = useI18n()
import { timeAgo } from '~/lib/date'

interface MailPreview {
  id: string
  from_: { name: string | null; email: string }[]
  subject: string | null
  preview: string | null
  received_at: string | null
  is_unread: boolean
}

const mails = ref<MailPreview[]>([])
const loading = ref(true)

async function fetchRecentMails() {
  try {
    // Get inbox mailbox id first
    const mbData = await $fetch<{ mailboxes: { id: string; role: string | null }[] }>('/api/mail/mailboxes')
    const inbox = mbData.mailboxes.find(m => m.role === 'inbox')
    if (!inbox) return

    const data = await $fetch<{ messages: MailPreview[] }>('/api/mail/messages', {
      params: { mailbox_id: inbox.id, page: 0, limit: 5 },
    })
    mails.value = data.messages
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecentMails)

function senderName(from: MailPreview['from_']) {
  if (!from || from.length === 0) return t('mail.unknownSender')
  return from[0].name || from[0].email
}
</script>

<template>
  <UiCard class="col-span-1 lg:col-span-2">
    <UiCardHeader class="pb-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-blue-500" aria-hidden="true"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
          <UiCardTitle class="text-base">{{ $t('dashboard.recentMail.title') }}</UiCardTitle>
        </div>
        <NuxtLink to="/mail" class="text-xs text-primary hover:underline">{{ $t('common.viewAll') }}</NuxtLink>
      </div>
    </UiCardHeader>
    <UiCardContent>
      <!-- Loading -->
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="flex gap-3">
          <UiSkeleton class="h-4 w-24 shrink-0" />
          <UiSkeleton class="h-4 flex-1" />
        </div>
      </div>

      <!-- Empty -->
      <p v-else-if="mails.length === 0" class="text-sm text-muted-foreground">
        {{ $t('dashboard.recentMail.empty') }}
      </p>

      <!-- Mail list -->
      <div v-else class="space-y-1">
        <NuxtLink
          v-for="m in mails"
          :key="m.id"
          to="/mail"
          class="flex items-start gap-3 rounded-md px-2 py-2 -mx-2 hover:bg-accent/50 transition-colors"
        >
          <span
            v-if="m.is_unread"
            class="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full bg-primary"
          />
          <span v-else class="mt-1.5 inline-block h-2 w-2 shrink-0" />
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-sm font-medium truncate" :class="{ 'font-semibold': m.is_unread }">
                {{ senderName(m.from_) }}
              </span>
              <span class="text-xs text-muted-foreground shrink-0">
                {{ m.received_at ? timeAgo(m.received_at) : '' }}
              </span>
            </div>
            <p class="text-sm truncate" :class="m.is_unread ? 'text-foreground' : 'text-muted-foreground'">
              {{ m.subject || $t('mail.noSubject') }}
            </p>
          </div>
        </NuxtLink>
      </div>
    </UiCardContent>
  </UiCard>
</template>
