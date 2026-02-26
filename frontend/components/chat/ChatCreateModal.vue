<script setup lang="ts">
const emit = defineEmits<{
  close: []
}>()

const { createChannel, searchUsers, selectChannel } = useChat()
const { t } = useI18n()

const name = ref('')
const type = ref<'public' | 'private'>('public')
const description = ref('')
const memberQuery = ref('')
const memberResults = ref<Array<{ id: string; username: string; display_name: string | null; avatar_url: string | null }>>([])
const selectedMembers = ref<Array<{ id: string; username: string; display_name: string | null }>>([])
const creating = ref(false)
const errorMessage = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

function onSearchInput() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(async () => {
    if (memberQuery.value.trim().length < 1) {
      memberResults.value = []
      return
    }
    memberResults.value = await searchUsers(memberQuery.value)
  }, 300)
}

function addMember(u: { id: string; username: string; display_name: string | null }) {
  if (!selectedMembers.value.find(m => m.id === u.id)) {
    selectedMembers.value.push({ id: u.id, username: u.username, display_name: u.display_name })
  }
  memberQuery.value = ''
  memberResults.value = []
}

function removeMember(id: string) {
  selectedMembers.value = selectedMembers.value.filter(m => m.id !== id)
}

async function onSubmit() {
  if (!name.value.trim()) return
  creating.value = true
  errorMessage.value = ''
  try {
    const result = await createChannel(
      name.value.trim(),
      type.value,
      description.value.trim() || undefined,
      selectedMembers.value.map(m => m.id),
    )
    await selectChannel(result.id)
    emit('close')
  } catch (e: any) {
    const detail = e?.data?.detail || e?.message || t('chat.create.error')
    errorMessage.value = typeof detail === 'string' ? detail : t('chat.create.error')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="$emit('close')" role="dialog" aria-modal="true">
    <div class="bg-background border rounded-lg shadow-xl w-full max-w-md mx-4">
      <div class="flex items-center justify-between px-5 py-4 border-b">
        <h3 class="text-base font-semibold">{{ $t('chat.create.title') }}</h3>
        <button @click="$emit('close')" class="h-8 w-8 flex items-center justify-center rounded-md hover:bg-accent" :aria-label="$t('common.close')">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <form @submit.prevent="onSubmit" class="p-5 space-y-4">
        <!-- Name -->
        <div>
          <label class="block text-sm font-medium mb-1">{{ $t('chat.create.name') }}</label>
          <input
            v-model="name"
            type="text"
            :placeholder="$t('chat.create.namePlaceholder')"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            maxlength="100"
            required
          />
        </div>

        <!-- Type -->
        <div>
          <label class="block text-sm font-medium mb-1">{{ $t('chat.create.type') }}</label>
          <div class="flex gap-4">
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" v-model="type" value="public" class="accent-primary" />
              {{ $t('chat.create.public') }}
            </label>
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" v-model="type" value="private" class="accent-primary" />
              {{ $t('chat.create.private') }}
            </label>
          </div>
        </div>

        <!-- Description -->
        <div>
          <label class="block text-sm font-medium mb-1">{{ $t('chat.create.description') }}</label>
          <input
            v-model="description"
            type="text"
            :placeholder="$t('chat.create.descriptionPlaceholder')"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            maxlength="500"
          />
        </div>

        <!-- Members -->
        <div>
          <label class="block text-sm font-medium mb-1">{{ $t('chat.create.members') }}</label>
          <input
            v-model="memberQuery"
            @input="onSearchInput"
            type="text"
            :placeholder="$t('chat.create.memberSearch')"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <!-- Search results -->
          <div v-if="memberResults.length > 0" class="mt-1 border rounded-md bg-background max-h-32 overflow-y-auto">
            <button
              v-for="u in memberResults"
              :key="u.id"
              type="button"
              @click="addMember(u)"
              class="w-full px-3 py-1.5 text-sm text-left hover:bg-accent transition-colors"
            >
              {{ u.display_name || u.username }}
              <span class="text-muted-foreground ml-1">@{{ u.username }}</span>
            </button>
          </div>
          <!-- Selected members -->
          <div v-if="selectedMembers.length > 0" class="flex flex-wrap gap-1 mt-2">
            <span
              v-for="m in selectedMembers"
              :key="m.id"
              class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-accent"
            >
              {{ m.display_name || m.username }}
              <button type="button" @click="removeMember(m.id)" class="hover:text-destructive">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </span>
          </div>
        </div>

        <!-- Error -->
        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <!-- Submit -->
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" @click="$emit('close')" class="px-4 py-2 text-sm border rounded-md hover:bg-accent transition-colors">
            {{ $t('common.cancel') }}
          </button>
          <button
            type="submit"
            :disabled="!name.trim() || creating"
            class="px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {{ creating ? $t('chat.create.creating') : $t('chat.create.submit') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
