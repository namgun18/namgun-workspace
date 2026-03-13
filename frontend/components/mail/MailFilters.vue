<script setup lang="ts">
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const { mailboxes } = useMail()

interface FilterRule {
  id: string
  name: string
  field: string
  match_type: string
  value: string
  action: string
  target_folder: string
  priority: number
  is_active: boolean
}

const rules = ref<FilterRule[]>([])
const loading = ref(false)
const saving = ref(false)
const applying = ref(false)

// New rule form
const showForm = ref(false)
const editingId = ref<string | null>(null)
const form = ref({
  name: '',
  field: 'from',
  match_type: 'contains',
  value: '',
  target_folder: '',
})

const FIELDS = [
  { value: 'from', label: 'mail.filters.fieldFrom' },
  { value: 'to', label: 'mail.filters.fieldTo' },
  { value: 'subject', label: 'mail.filters.fieldSubject' },
  { value: 'any', label: 'mail.filters.fieldAny' },
]

const MATCH_TYPES = [
  { value: 'contains', label: 'mail.filters.matchContains' },
  { value: 'equals', label: 'mail.filters.matchEquals' },
  { value: 'starts_with', label: 'mail.filters.matchStartsWith' },
]

// Non-protected mailboxes for target folder selection
const folderOptions = computed(() =>
  mailboxes.value.map(mb => ({ value: mb.id, label: mb.name || mb.id }))
)

async function fetchRules() {
  loading.value = true
  try {
    const data = await $fetch<{ rules: FilterRule[] }>('/api/mail/filters')
    rules.value = data.rules
  } catch (e: any) {
    console.error('fetchRules error:', e)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = { name: '', field: 'from', match_type: 'contains', value: '', target_folder: '' }
  editingId.value = null
  showForm.value = false
}

function startEdit(rule: FilterRule) {
  editingId.value = rule.id
  form.value = {
    name: rule.name,
    field: rule.field,
    match_type: rule.match_type,
    value: rule.value,
    target_folder: rule.target_folder,
  }
  showForm.value = true
}

async function saveRule() {
  if (!form.value.name.trim() || !form.value.value.trim() || !form.value.target_folder) return
  saving.value = true
  try {
    if (editingId.value) {
      await $fetch(`/api/mail/filters/${editingId.value}`, {
        method: 'PATCH',
        body: form.value,
      })
    } else {
      await $fetch('/api/mail/filters', {
        method: 'POST',
        body: form.value,
      })
    }
    resetForm()
    await fetchRules()
  } catch (e: any) {
    console.error('saveRule error:', e)
  } finally {
    saving.value = false
  }
}

async function deleteRule(id: string) {
  if (!confirm(t('mail.filters.deleteConfirm'))) return
  try {
    await $fetch(`/api/mail/filters/${id}`, { method: 'DELETE' })
    await fetchRules()
  } catch (e: any) {
    console.error('deleteRule error:', e)
  }
}

async function toggleActive(rule: FilterRule) {
  try {
    await $fetch(`/api/mail/filters/${rule.id}`, {
      method: 'PATCH',
      body: { is_active: !rule.is_active },
    })
    rule.is_active = !rule.is_active
  } catch (e: any) {
    console.error('toggleActive error:', e)
  }
}

async function applyFilters() {
  applying.value = true
  try {
    const data = await $fetch<{ moved: number }>('/api/mail/filters/apply', { method: 'POST' })
    if (data.moved > 0) {
      alert(t('mail.filters.applyResult', { count: data.moved }))
    } else {
      alert(t('mail.filters.applyNone'))
    }
  } catch (e: any) {
    console.error('applyFilters error:', e)
  } finally {
    applying.value = false
  }
}

function getFieldLabel(field: string) {
  const f = FIELDS.find(f => f.value === field)
  return f ? t(f.label) : field
}

function getMatchLabel(match: string) {
  const m = MATCH_TYPES.find(m => m.value === match)
  return m ? t(m.label) : match
}

function getFolderLabel(folderId: string) {
  const mb = mailboxes.value.find(m => m.id === folderId)
  return mb?.name || folderId
}

onMounted(() => fetchRules())
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="emit('close')">
    <div class="bg-background border rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b">
        <h2 class="text-lg font-semibold">{{ $t('mail.filters.title') }}</h2>
        <div class="flex items-center gap-2">
          <button
            @click="applyFilters"
            :disabled="applying || rules.length === 0"
            class="px-3 py-1.5 text-sm rounded-md border hover:bg-accent transition-colors disabled:opacity-50"
          >
            {{ applying ? $t('common.processing') : $t('mail.filters.applyNow') }}
          </button>
          <button @click="emit('close')" class="h-8 w-8 flex items-center justify-center rounded-md hover:bg-accent transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-5 space-y-4">
        <!-- Rule list -->
        <div v-if="loading" class="text-center py-8 text-muted-foreground text-sm">
          {{ $t('common.loading') }}
        </div>

        <div v-else-if="rules.length === 0 && !showForm" class="text-center py-8">
          <p class="text-muted-foreground text-sm">{{ $t('mail.filters.empty') }}</p>
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="rule in rules"
            :key="rule.id"
            class="flex items-center gap-3 p-3 border rounded-lg"
            :class="rule.is_active ? 'bg-card' : 'bg-muted/50 opacity-60'"
          >
            <div class="flex-1 min-w-0">
              <div class="font-medium text-sm">{{ rule.name }}</div>
              <div class="text-xs text-muted-foreground mt-0.5">
                {{ getFieldLabel(rule.field) }}
                {{ getMatchLabel(rule.match_type) }}
                "<span class="font-medium">{{ rule.value }}</span>"
                → {{ getFolderLabel(rule.target_folder) }}
              </div>
            </div>
            <button
              @click="toggleActive(rule)"
              class="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
              :class="rule.is_active ? 'bg-primary' : 'bg-muted'"
            >
              <span
                class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
                :class="rule.is_active ? 'translate-x-4' : 'translate-x-0'"
              />
            </button>
            <button @click="startEdit(rule)" class="h-7 w-7 flex items-center justify-center rounded hover:bg-accent text-muted-foreground">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
                <path d="M12 20h9 M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            </button>
            <button @click="deleteRule(rule.id)" class="h-7 w-7 flex items-center justify-center rounded hover:bg-accent text-destructive">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Add/Edit form -->
        <div v-if="showForm" class="border rounded-lg p-4 space-y-3 bg-card">
          <h3 class="text-sm font-semibold">{{ editingId ? $t('mail.filters.edit') : $t('mail.filters.add') }}</h3>

          <div>
            <label class="block text-xs font-medium mb-1">{{ $t('mail.filters.ruleName') }}</label>
            <input v-model="form.name" type="text" :placeholder="$t('mail.filters.ruleNamePlaceholder')"
                   class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium mb-1">{{ $t('mail.filters.condition') }}</label>
              <select v-model="form.field" class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary">
                <option v-for="f in FIELDS" :key="f.value" :value="f.value">{{ $t(f.label) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium mb-1">{{ $t('mail.filters.matchType') }}</label>
              <select v-model="form.match_type" class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary">
                <option v-for="m in MATCH_TYPES" :key="m.value" :value="m.value">{{ $t(m.label) }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium mb-1">{{ $t('mail.filters.value') }}</label>
            <input v-model="form.value" type="text" :placeholder="$t('mail.filters.valuePlaceholder')"
                   class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary" />
          </div>

          <div>
            <label class="block text-xs font-medium mb-1">{{ $t('mail.filters.targetFolder') }}</label>
            <select v-model="form.target_folder" class="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary">
              <option value="" disabled>{{ $t('mail.filters.selectFolder') }}</option>
              <option v-for="f in folderOptions" :key="f.value" :value="f.value">{{ f.label }}</option>
            </select>
          </div>

          <div class="flex justify-end gap-2 pt-1">
            <button @click="resetForm" class="px-3 py-1.5 text-sm rounded-md border hover:bg-accent transition-colors">
              {{ $t('common.cancel') }}
            </button>
            <button
              @click="saveRule"
              :disabled="saving || !form.name.trim() || !form.value.trim() || !form.target_folder"
              class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {{ saving ? $t('common.processing') : $t('common.save') }}
            </button>
          </div>
        </div>

        <!-- Add button -->
        <button
          v-if="!showForm"
          @click="showForm = true"
          class="w-full py-2 text-sm text-muted-foreground hover:text-foreground border border-dashed rounded-lg hover:bg-accent/50 transition-colors"
        >
          + {{ $t('mail.filters.add') }}
        </button>
      </div>
    </div>
  </div>
</template>
