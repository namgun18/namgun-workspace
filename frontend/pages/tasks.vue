<script setup lang="ts">
definePageMeta({ layout: 'default', middleware: 'auth' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('tasks.title')} | ${appName.value}`) })

const { tasks, total, loading, fetchTasks, createTask, updateTask, deleteTask, toggleTask } = useTasks()

// Filters
const filterStatus = ref<string | null>(null)
const filterPriority = ref<string | null>(null)

// New task form
const showForm = ref(false)
const newTitle = ref('')
const newDescription = ref('')
const newPriority = ref<'low' | 'medium' | 'high'>('medium')
const newDueDate = ref('')
const submitting = ref(false)

// Edit task
const editingTask = ref<any>(null)
const editTitle = ref('')
const editDescription = ref('')
const editPriority = ref<'low' | 'medium' | 'high'>('medium')
const editDueDate = ref('')
const editSaving = ref(false)

async function loadTasks() {
  await fetchTasks({
    status: filterStatus.value,
    priority: filterPriority.value,
    sort_by: 'created_at',
    sort_dir: 'desc',
    limit: 200,
  })
}

watch([filterStatus, filterPriority], () => loadTasks())
onMounted(() => loadTasks())

async function handleCreate() {
  if (!newTitle.value.trim()) return
  submitting.value = true
  try {
    await createTask({
      title: newTitle.value.trim(),
      description: newDescription.value.trim() || undefined,
      priority: newPriority.value,
      due_date: newDueDate.value || undefined,
    })
    newTitle.value = ''
    newDescription.value = ''
    newPriority.value = 'medium'
    newDueDate.value = ''
    showForm.value = false
    await loadTasks()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    submitting.value = false
  }
}

async function handleToggle(id: string) {
  try {
    await toggleTask(id)
    await loadTasks()
  } catch {}
}

async function handleDelete(id: string) {
  if (!confirm(t('tasks.deleteConfirm'))) return
  try {
    await deleteTask(id)
    await loadTasks()
  } catch {}
}

function startEdit(task: any) {
  editingTask.value = task
  editTitle.value = task.title
  editDescription.value = task.description || ''
  editPriority.value = task.priority
  editDueDate.value = task.due_date ? task.due_date.slice(0, 10) : ''
}

function cancelEdit() {
  editingTask.value = null
}

async function handleEditSave() {
  if (!editTitle.value.trim()) return
  editSaving.value = true
  try {
    await updateTask(editingTask.value.id, {
      title: editTitle.value.trim(),
      description: editDescription.value.trim() || undefined,
      priority: editPriority.value,
      due_date: editDueDate.value || null,
    })
    editingTask.value = null
    await loadTasks()
  } catch (e: any) {
    alert(e?.data?.detail || t('error.genericError'))
  } finally {
    editSaving.value = false
  }
}

function priorityColor(p: string) {
  if (p === 'high') return 'text-red-500'
  if (p === 'medium') return 'text-yellow-500'
  return 'text-blue-400'
}

function priorityLabel(p: string) {
  if (p === 'high') return t('tasks.priorityHigh')
  if (p === 'medium') return t('tasks.priorityMedium')
  return t('tasks.priorityLow')
}

function statusLabel(s: string) {
  if (s === 'done') return t('tasks.statusDone')
  if (s === 'in_progress') return t('tasks.statusInProgress')
  return t('tasks.statusTodo')
}

function formatDate(d: string | null) {
  if (!d) return ''
  return new Date(d).toLocaleDateString()
}
</script>

<template>
  <div class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">{{ $t('tasks.title') }}</h1>
        <p class="text-muted-foreground mt-1">{{ $t('tasks.subtitle') }}</p>
      </div>
      <UiButton @click="showForm = !showForm">
        {{ showForm ? $t('common.cancel') : $t('tasks.newTask') }}
      </UiButton>
    </div>

    <!-- New task form -->
    <div v-if="showForm" class="border rounded-lg bg-card p-4 mb-6">
      <form @submit.prevent="handleCreate" class="space-y-3">
        <div>
          <input
            v-model="newTitle"
            type="text"
            :placeholder="$t('tasks.titlePlaceholder')"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            autofocus
          />
        </div>
        <div>
          <textarea
            v-model="newDescription"
            :placeholder="$t('tasks.descriptionPlaceholder')"
            rows="2"
            class="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>
        <div class="flex gap-3 items-center">
          <select
            v-model="newPriority"
            class="px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="low">{{ $t('tasks.priorityLow') }}</option>
            <option value="medium">{{ $t('tasks.priorityMedium') }}</option>
            <option value="high">{{ $t('tasks.priorityHigh') }}</option>
          </select>
          <input
            v-model="newDueDate"
            type="date"
            class="px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <UiButton type="submit" :disabled="submitting || !newTitle.trim()">
            {{ submitting ? $t('common.creating') : $t('common.create') }}
          </UiButton>
        </div>
      </form>
    </div>

    <!-- Filters -->
    <div class="flex gap-2 mb-4 flex-wrap">
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', !filterStatus ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent']"
        @click="filterStatus = null"
      >{{ $t('common.all') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterStatus === 'todo' ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent']"
        @click="filterStatus = 'todo'"
      >{{ $t('tasks.statusTodo') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterStatus === 'in_progress' ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent']"
        @click="filterStatus = 'in_progress'"
      >{{ $t('tasks.statusInProgress') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterStatus === 'done' ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent']"
        @click="filterStatus = 'done'"
      >{{ $t('tasks.statusDone') }}</button>

      <div class="border-l mx-2" />

      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', !filterPriority ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-accent']"
        @click="filterPriority = null"
      >{{ $t('common.all') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterPriority === 'high' ? 'bg-red-500 text-white border-red-500' : 'hover:bg-accent']"
        @click="filterPriority = 'high'"
      >{{ $t('tasks.priorityHigh') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterPriority === 'medium' ? 'bg-yellow-500 text-white border-yellow-500' : 'hover:bg-accent']"
        @click="filterPriority = 'medium'"
      >{{ $t('tasks.priorityMedium') }}</button>
      <button
        :class="['px-3 py-1.5 text-sm rounded-full border transition-colors', filterPriority === 'low' ? 'bg-blue-400 text-white border-blue-400' : 'hover:bg-accent']"
        @click="filterPriority = 'low'"
      >{{ $t('tasks.priorityLow') }}</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-muted-foreground">
      {{ $t('common.loading') }}
    </div>

    <!-- Empty -->
    <div v-else-if="tasks.length === 0" class="text-center py-12 text-muted-foreground">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto mb-3 opacity-40">
        <rect x="3" y="5" width="6" height="6" rx="1" />
        <path d="m3.5 5.5 2.5 2.5 3-3" />
        <line x1="13" y1="6" x2="21" y2="6" />
        <line x1="13" y1="10" x2="18" y2="10" />
        <rect x="3" y="15" width="6" height="6" rx="1" />
        <line x1="13" y1="16" x2="21" y2="16" />
        <line x1="13" y1="20" x2="18" y2="20" />
      </svg>
      <p>{{ $t('tasks.empty') }}</p>
    </div>

    <!-- Task list -->
    <div v-else class="space-y-2">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="group border rounded-lg bg-card p-4 flex items-start gap-3 hover:shadow-sm transition-shadow"
      >
        <!-- Checkbox -->
        <button
          @click="handleToggle(task.id)"
          class="mt-0.5 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
          :class="task.status === 'done' ? 'bg-primary border-primary' : 'border-muted-foreground/40 hover:border-primary'"
        >
          <svg v-if="task.status === 'done'" class="w-3 h-3 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </button>

        <!-- Edit mode -->
        <div v-if="editingTask?.id === task.id" class="flex-1 space-y-2">
          <input
            v-model="editTitle"
            type="text"
            class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <textarea
            v-model="editDescription"
            rows="2"
            class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
          <div class="flex gap-2 items-center">
            <select v-model="editPriority" class="px-2 py-1 text-sm border rounded-md bg-background">
              <option value="low">{{ $t('tasks.priorityLow') }}</option>
              <option value="medium">{{ $t('tasks.priorityMedium') }}</option>
              <option value="high">{{ $t('tasks.priorityHigh') }}</option>
            </select>
            <input v-model="editDueDate" type="date" class="px-2 py-1 text-sm border rounded-md bg-background" />
            <UiButton size="sm" @click="handleEditSave" :disabled="editSaving">{{ $t('common.save') }}</UiButton>
            <UiButton size="sm" variant="outline" @click="cancelEdit">{{ $t('common.cancel') }}</UiButton>
          </div>
        </div>

        <!-- Display mode -->
        <div v-else class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span :class="['text-sm font-medium', task.status === 'done' ? 'line-through text-muted-foreground' : '']">
              {{ task.title }}
            </span>
            <span :class="['text-xs font-medium', priorityColor(task.priority)]">
              {{ priorityLabel(task.priority) }}
            </span>
            <span v-if="task.status === 'in_progress'" class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              {{ statusLabel(task.status) }}
            </span>
          </div>
          <p v-if="task.description" class="text-xs text-muted-foreground mt-0.5 line-clamp-2">{{ task.description }}</p>
          <div class="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span v-if="task.due_date">{{ $t('tasks.dueDate') }}: {{ formatDate(task.due_date) }}</span>
            <span>{{ formatDate(task.created_at) }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div v-if="editingTask?.id !== task.id" class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button @click="startEdit(task)" class="p-1.5 rounded hover:bg-accent" :title="$t('common.edit')">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button @click="handleDelete(task.id)" class="p-1.5 rounded hover:bg-destructive/10 text-destructive" :title="$t('common.delete')">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Total count -->
    <p v-if="total > 0" class="text-xs text-muted-foreground mt-4 text-right">
      {{ $t('tasks.totalCount', { n: total }) }}
    </p>
  </div>
</template>
