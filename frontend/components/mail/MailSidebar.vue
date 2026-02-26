<script setup lang="ts">
const emit = defineEmits<{
  navigate: []
}>()

const { mailboxes, selectedMailboxId, selectMailbox, createMailbox, renameMailbox, deleteMailbox } = useMail()
const { t } = useI18n()

const ROLE_LABELS: Record<string, string> = {
  inbox: 'mail.folder.inbox',
  sent: 'mail.folder.sent',
  drafts: 'mail.folder.drafts',
  trash: 'mail.folder.trash',
  junk: 'mail.folder.junk',
  archive: 'mail.folder.archive',
}

const ROLE_ICONS: Record<string, string> = {
  inbox: 'inbox',
  sent: 'send',
  drafts: 'file-edit',
  trash: 'trash',
  junk: 'shield-alert',
  archive: 'archive',
}

const PROTECTED_ROLES = new Set(['inbox', 'sent', 'drafts', 'trash', 'junk', 'archive'])

const showCreateInput = ref(false)
const newMailboxName = ref('')
const creating = ref(false)

const contextMenu = ref<{ x: number; y: number; mailbox: any } | null>(null)
const renaming = ref<string | null>(null)
const renameValue = ref('')

function getLabel(mb: any) {
  if (mb.role && ROLE_LABELS[mb.role]) return t(ROLE_LABELS[mb.role])
  return mb.name
}

function getIcon(mb: any) {
  if (mb.role && ROLE_ICONS[mb.role]) return ROLE_ICONS[mb.role]
  return 'folder'
}

function handleSelect(id: string) {
  selectMailbox(id)
  emit('navigate')
}

async function handleCreate() {
  const name = newMailboxName.value.trim()
  if (!name) return
  creating.value = true
  try {
    await createMailbox(name)
    newMailboxName.value = ''
    showCreateInput.value = false
  } catch { /* handled in composable */ }
  creating.value = false
}

function handleContextMenu(e: MouseEvent, mb: any) {
  if (mb.role && PROTECTED_ROLES.has(mb.role)) return
  e.preventDefault()
  contextMenu.value = { x: e.clientX, y: e.clientY, mailbox: mb }
}

function startRename(mb: any) {
  renaming.value = mb.id
  renameValue.value = mb.name
  contextMenu.value = null
}

async function handleRename(mb: any) {
  const newName = renameValue.value.trim()
  if (!newName || newName === mb.id) {
    renaming.value = null
    return
  }
  try {
    await renameMailbox(mb.id, newName)
  } catch { /* handled */ }
  renaming.value = null
}

async function handleDeleteMailbox(mb: any) {
  contextMenu.value = null
  if (!confirm(t('mail.folder.deleteConfirm', { name: mb.name }))) return
  try {
    await deleteMailbox(mb.id)
  } catch { /* handled */ }
}

// Close context menu on click outside
let _sidebarClickRegistered = false
if (import.meta.client && !_sidebarClickRegistered) {
  _sidebarClickRegistered = true
  window.addEventListener('click', () => { contextMenu.value = null })
}
</script>

<template>
  <aside class="flex flex-col h-full border-r bg-muted/30">
    <div class="flex items-center justify-between px-3 py-3 border-b">
      <h2 class="text-sm font-semibold text-foreground">{{ $t('mail.sidebar.title') }}</h2>
      <button
        @click="showCreateInput = !showCreateInput"
        class="h-6 w-6 flex items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        :title="$t('mail.folder.addTitle')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>

    <!-- Create mailbox input -->
    <div v-if="showCreateInput" class="px-3 py-2 border-b">
      <form @submit.prevent="handleCreate" class="flex gap-1">
        <input
          v-model="newMailboxName"
          type="text"
          :placeholder="$t('mail.folder.namePlaceholder')"
          class="flex-1 px-2 py-1 text-sm bg-background border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
          :disabled="creating"
        />
        <button type="submit" :disabled="creating || !newMailboxName.trim()" class="px-2 py-1 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          {{ $t('common.add') }}
        </button>
      </form>
    </div>

    <nav class="flex-1 p-3 space-y-0.5 overflow-auto">
      <template v-for="mb in mailboxes" :key="mb.id">
        <!-- Rename mode -->
        <form v-if="renaming === mb.id" @submit.prevent="handleRename(mb)" class="flex gap-1 px-1 py-1">
          <input
            v-model="renameValue"
            type="text"
            class="flex-1 px-2 py-1 text-sm bg-background border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
            @keydown.escape="renaming = null"
          />
          <button type="submit" class="px-2 py-1 text-xs rounded-md bg-primary text-primary-foreground">{{ $t('common.confirm') }}</button>
        </form>
        <!-- Normal mode -->
        <button
          v-else
          @click="handleSelect(mb.id)"
          @contextmenu="handleContextMenu($event, mb)"
          class="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors"
          :class="selectedMailboxId === mb.id
            ? 'bg-accent text-accent-foreground font-medium'
            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'"
        >
        <!-- Inbox -->
        <svg v-if="getIcon(mb) === 'inbox'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
        </svg>
        <!-- Send -->
        <svg v-else-if="getIcon(mb) === 'send'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
        <!-- Drafts -->
        <svg v-else-if="getIcon(mb) === 'file-edit'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <path d="M4 13.5V4a2 2 0 0 1 2-2h8.5L20 7.5V20a2 2 0 0 1-2 2h-5.5" /><polyline points="14 2 14 8 20 8" /><path d="M10.42 12.61a2.1 2.1 0 1 1 2.97 2.97L7.95 21 4 22l.99-3.95 5.43-5.44Z" />
        </svg>
        <!-- Trash -->
        <svg v-else-if="getIcon(mb) === 'trash'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
        <!-- Junk/Spam -->
        <svg v-else-if="getIcon(mb) === 'shield-alert'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <!-- Archive -->
        <svg v-else-if="getIcon(mb) === 'archive'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <polyline points="21 8 21 21 3 21 3 8" /><rect x="1" y="3" width="22" height="5" /><line x1="10" y1="12" x2="14" y2="12" />
        </svg>
        <!-- Folder (default) -->
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0">
          <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
        </svg>

        <span class="flex-1 text-left truncate">{{ getLabel(mb) }}</span>

        <!-- Unread badge -->
        <span
          v-if="mb.unread_count > 0"
          class="text-xs font-medium px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground"
        >
          {{ mb.unread_count > 99 ? '99+' : mb.unread_count }}
        </span>
      </button>
      </template>
    </nav>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu"
        class="fixed z-50 bg-popover border rounded-md shadow-md py-1 min-w-[140px]"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <button
          @click="startRename(contextMenu.mailbox)"
          class="w-full px-3 py-1.5 text-sm text-left hover:bg-accent transition-colors"
        >{{ $t('mail.folder.rename') }}</button>
        <button
          @click="handleDeleteMailbox(contextMenu.mailbox)"
          class="w-full px-3 py-1.5 text-sm text-left hover:bg-accent text-destructive transition-colors"
        >{{ $t('common.delete') }}</button>
      </div>
    </Teleport>
  </aside>
</template>
