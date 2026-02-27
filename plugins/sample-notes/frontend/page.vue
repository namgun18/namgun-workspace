<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { appName } = useAppConfig()
const { user } = useAuth()
useHead({ title: computed(() => `메모 | ${appName.value}`) })

interface NoteItem {
  id: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

const notes = ref<NoteItem[]>([])
const loading = ref(false)
const saving = ref(false)
const selectedId = ref<string | null>(null)
const editTitle = ref('')
const editContent = ref('')

const selectedNote = computed(() =>
  notes.value.find(n => n.id === selectedId.value) || null
)

async function fetchNotes() {
  loading.value = true
  try {
    const data = await $fetch<{ notes: NoteItem[] }>('/api/plugins/notes')
    notes.value = data.notes
  } catch (e: any) {
    console.error('fetchNotes error:', e)
  } finally {
    loading.value = false
  }
}

function selectNote(note: NoteItem) {
  selectedId.value = note.id
  editTitle.value = note.title
  editContent.value = note.content
}

async function createNote() {
  saving.value = true
  try {
    const note = await $fetch<NoteItem>('/api/plugins/notes', {
      method: 'POST',
      body: { title: '새 메모', content: '' },
    })
    notes.value.unshift(note)
    selectNote(note)
  } catch (e: any) {
    console.error('createNote error:', e)
  } finally {
    saving.value = false
  }
}

async function saveNote() {
  if (!selectedId.value) return
  saving.value = true
  try {
    const updated = await $fetch<NoteItem>(`/api/plugins/notes/${selectedId.value}`, {
      method: 'PATCH',
      body: { title: editTitle.value, content: editContent.value },
    })
    const idx = notes.value.findIndex(n => n.id === updated.id)
    if (idx >= 0) notes.value[idx] = updated
  } catch (e: any) {
    console.error('saveNote error:', e)
  } finally {
    saving.value = false
  }
}

async function deleteNote(noteId: string) {
  if (!confirm('이 메모를 삭제하시겠습니까?')) return
  try {
    await $fetch(`/api/plugins/notes/${noteId}`, { method: 'DELETE' })
    notes.value = notes.value.filter(n => n.id !== noteId)
    if (selectedId.value === noteId) {
      selectedId.value = null
      editTitle.value = ''
      editContent.value = ''
    }
  } catch (e: any) {
    console.error('deleteNote error:', e)
  }
}

onMounted(() => {
  if (user.value) fetchNotes()
})
</script>

<template>
  <div v-if="user" class="h-full flex">
    <!-- Sidebar: note list -->
    <div class="w-64 border-r flex flex-col bg-card">
      <div class="p-3 border-b flex items-center justify-between">
        <h2 class="font-semibold text-sm">메모</h2>
        <button
          @click="createNote"
          :disabled="saving"
          class="w-7 h-7 rounded-md flex items-center justify-center hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               class="h-4 w-4">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-auto">
        <div v-if="loading" class="p-4 text-center text-sm text-muted-foreground">
          로딩 중...
        </div>
        <div v-else-if="notes.length === 0" class="p-4 text-center text-sm text-muted-foreground">
          메모가 없습니다
        </div>
        <button
          v-else
          v-for="note in notes"
          :key="note.id"
          @click="selectNote(note)"
          class="w-full text-left px-3 py-2.5 border-b text-sm transition-colors"
          :class="selectedId === note.id ? 'bg-accent' : 'hover:bg-accent/50'"
        >
          <div class="font-medium truncate">{{ note.title || '(제목 없음)' }}</div>
          <div class="text-xs text-muted-foreground mt-0.5 truncate">
            {{ note.content?.substring(0, 50) || '(내용 없음)' }}
          </div>
        </button>
      </div>
    </div>

    <!-- Editor -->
    <div class="flex-1 flex flex-col">
      <div v-if="selectedNote" class="flex-1 flex flex-col">
        <div class="p-3 border-b flex items-center gap-2">
          <input
            v-model="editTitle"
            placeholder="제목"
            class="flex-1 bg-transparent border-none text-lg font-semibold focus:outline-none"
          />
          <button
            @click="saveNote"
            :disabled="saving"
            class="px-3 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {{ saving ? '저장 중...' : '저장' }}
          </button>
          <button
            @click="deleteNote(selectedNote!.id)"
            class="px-3 py-1.5 text-sm font-medium rounded-md border hover:bg-destructive hover:text-destructive-foreground transition-colors"
          >
            삭제
          </button>
        </div>
        <textarea
          v-model="editContent"
          placeholder="내용을 입력하세요..."
          class="flex-1 p-4 bg-transparent resize-none focus:outline-none text-sm leading-relaxed"
        />
      </div>
      <div v-else class="flex-1 flex items-center justify-center text-muted-foreground">
        <div class="text-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
               class="h-12 w-12 mx-auto mb-3 opacity-40">
            <path d="M12 20h9 M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
          <p class="text-sm">메모를 선택하거나 새로 만드세요</p>
        </div>
      </div>
    </div>
  </div>
</template>
