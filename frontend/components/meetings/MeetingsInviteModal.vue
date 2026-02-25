<script setup lang="ts">
interface Invitee {
  type: 'internal' | 'external'
  user_id?: string
  username?: string
  display_name?: string
  email?: string
  label: string  // UI display
}

interface SearchResult {
  id: string
  username: string
  display_name: string
  email: string
}

const emit = defineEmits<{
  close: []
  create: [payload: {
    name: string
    invitees: Omit<Invitee, 'label'>[]
    scheduled_at: string | null
    duration_minutes: number
  }]
}>()

const roomName = ref('')
const invitees = ref<Invitee[]>([])
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searching = ref(false)
const showDropdown = ref(false)
const scheduledDate = ref('')
const scheduledTime = ref('')
const durationMinutes = ref(60)
const creating = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const inputRef = ref<HTMLInputElement | null>(null)

// Duration options
const durationOptions = [
  { value: 30, label: '30분' },
  { value: 60, label: '1시간' },
  { value: 120, label: '2시간' },
]

// Email validation
function isValidEmail(str: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str)
}

// Search users with debounce
function onSearchInput() {
  const q = searchQuery.value.trim()
  if (debounceTimer) clearTimeout(debounceTimer)

  if (q.length < 1) {
    searchResults.value = []
    showDropdown.value = false
    return
  }

  debounceTimer = setTimeout(async () => {
    searching.value = true
    try {
      const results = await $fetch<SearchResult[]>('/api/auth/users/search', {
        params: { q },
        credentials: 'include',
      })
      // Filter out already-added users
      const addedIds = new Set(invitees.value.filter(i => i.user_id).map(i => i.user_id))
      searchResults.value = results.filter(r => !addedIds.has(r.id))
      showDropdown.value = true
    } catch {
      searchResults.value = []
    } finally {
      searching.value = false
    }
  }, 300)
}

function addInternalUser(user: SearchResult) {
  if (invitees.value.some(i => i.user_id === user.id)) return
  invitees.value.push({
    type: 'internal',
    user_id: user.id,
    username: user.username,
    display_name: user.display_name,
    email: user.email,
    label: user.display_name || user.username,
  })
  searchQuery.value = ''
  searchResults.value = []
  showDropdown.value = false
  inputRef.value?.focus()
}

function addExternalEmail() {
  const email = searchQuery.value.trim()
  if (!isValidEmail(email)) return
  if (invitees.value.some(i => i.email === email)) return
  invitees.value.push({
    type: 'external',
    email,
    label: email,
  })
  searchQuery.value = ''
  searchResults.value = []
  showDropdown.value = false
  inputRef.value?.focus()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    const q = searchQuery.value.trim()
    // If dropdown has results and user presses Enter, add first result
    if (searchResults.value.length > 0) {
      addInternalUser(searchResults.value[0])
    } else if (isValidEmail(q)) {
      addExternalEmail()
    }
  }
  if (e.key === 'Escape') {
    showDropdown.value = false
  }
}

function removeInvitee(idx: number) {
  invitees.value.splice(idx, 1)
}

function handleSubmit() {
  if (!roomName.value.trim() || creating.value) return
  creating.value = true

  let scheduled_at: string | null = null
  if (scheduledDate.value && scheduledTime.value) {
    scheduled_at = `${scheduledDate.value}T${scheduledTime.value}:00`
  } else if (scheduledDate.value) {
    scheduled_at = `${scheduledDate.value}T00:00:00`
  }

  emit('create', {
    name: roomName.value.trim(),
    invitees: invitees.value.map(({ label, ...rest }) => rest),
    scheduled_at,
    duration_minutes: durationMinutes.value,
  })
}

function handleBackdropClick() {
  if (!creating.value) emit('close')
}

// Close dropdown on outside click
function onBlurInput() {
  // Delay to allow click on dropdown item
  setTimeout(() => { showDropdown.value = false }, 200)
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleBackdropClick"
    >
      <div class="bg-background rounded-lg border shadow-lg w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-semibold mb-4">새 회의실</h3>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- Room name -->
          <div>
            <label class="block text-sm font-medium mb-1.5">회의실 이름</label>
            <input
              v-model="roomName"
              type="text"
              placeholder="예: 주간회의"
              class="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              autofocus
            />
          </div>

          <!-- Invitees -->
          <div>
            <label class="block text-sm font-medium mb-1.5">참가자 초대 <span class="text-muted-foreground font-normal">(선택)</span></label>

            <!-- Chips -->
            <div v-if="invitees.length" class="flex flex-wrap gap-1.5 mb-2">
              <span
                v-for="(inv, idx) in invitees"
                :key="idx"
                class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full border"
                :class="inv.type === 'internal' ? 'bg-primary/10 text-primary border-primary/20' : 'bg-muted text-muted-foreground'"
              >
                {{ inv.label }}
                <button type="button" @click="removeInvitee(idx)" class="hover:text-destructive ml-0.5">&times;</button>
              </span>
            </div>

            <!-- Search input -->
            <div class="relative">
              <input
                ref="inputRef"
                v-model="searchQuery"
                type="text"
                placeholder="사용자 검색 또는 외부 이메일 입력"
                class="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                @input="onSearchInput"
                @keydown="handleKeydown"
                @blur="onBlurInput"
                @focus="searchQuery.trim() && searchResults.length && (showDropdown = true)"
              />

              <!-- Dropdown -->
              <div
                v-if="showDropdown && (searchResults.length > 0 || (searchQuery.trim() && isValidEmail(searchQuery.trim())))"
                class="absolute left-0 right-0 top-full mt-1 bg-popover border rounded-md shadow-lg z-10 max-h-48 overflow-y-auto"
              >
                <!-- User results -->
                <button
                  v-for="user in searchResults"
                  :key="user.id"
                  type="button"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors flex items-center gap-2"
                  @mousedown.prevent="addInternalUser(user)"
                >
                  <span class="font-medium">{{ user.display_name }}</span>
                  <span class="text-muted-foreground text-xs">@{{ user.username }}</span>
                </button>

                <!-- External email option -->
                <button
                  v-if="isValidEmail(searchQuery.trim()) && !searchResults.some(r => r.email === searchQuery.trim())"
                  type="button"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors border-t"
                  @mousedown.prevent="addExternalEmail"
                >
                  <span class="text-muted-foreground">외부 초대:</span>
                  <span class="font-medium ml-1">{{ searchQuery.trim() }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Scheduled time -->
          <div>
            <label class="block text-sm font-medium mb-1.5">예약 시간 <span class="text-muted-foreground font-normal">(선택, 비워두면 즉시)</span></label>
            <div class="flex gap-2">
              <input
                v-model="scheduledDate"
                type="date"
                class="flex-1 px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <input
                v-model="scheduledTime"
                type="time"
                class="w-28 px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>

          <!-- Duration -->
          <div>
            <label class="block text-sm font-medium mb-1.5">회의 시간</label>
            <select
              v-model="durationMinutes"
              class="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option v-for="opt in durationOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <p class="text-xs text-muted-foreground">
            {{ invitees.length > 0 ? `${invitees.length}명에게 초대 메일(ICS)이 발송됩니다` : '최대 10명까지 참여할 수 있습니다' }}
          </p>

          <!-- Buttons -->
          <div class="flex justify-end gap-2 pt-1">
            <button
              type="button"
              @click="emit('close')"
              :disabled="creating"
              class="px-4 py-2 text-sm rounded-md border hover:bg-accent transition-colors disabled:opacity-50"
            >
              취소
            </button>
            <button
              type="submit"
              :disabled="creating || !roomName.trim()"
              class="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {{ creating ? '생성 중...' : (invitees.length > 0 ? '생성 및 초대' : '생성 및 참여') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
