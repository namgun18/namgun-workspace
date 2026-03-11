<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
const { user } = useAuth()
const { addToast } = useToast()

useHead({ title: computed(() => `${t('wiki.title')} | ${appName.value}`) })

const {
  spaces, currentSpace, pageTree, currentPage, loading, saving,
  fetchSpaces, fetchSpace, fetchPages, fetchPage,
  createSpace, createPage, updatePage, deletePage, deleteSpace,
  buildTree, searchPages, searchResults, fetchVersions, versions,
} = useWiki()

// UI state
const showCreateSpace = ref(false)
const showCreatePage = ref(false)
const showVersions = ref(false)
const editing = ref(false)
const editContent = ref('')
const editTitle = ref('')
const newSpaceName = ref('')
const newSpaceSlug = ref('')
const newPageTitle = ref('')
const searchQuery = ref('')
const searchTimeout = ref<any>(null)

const tree = computed(() => buildTree(pageTree.value))

// Auto-generate slug from name
watch(newSpaceName, (v) => {
  newSpaceSlug.value = v.toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-|-$/g, '')
})

onMounted(async () => {
  if (user.value) await fetchSpaces()
})

async function handleCreateSpace() {
  if (!newSpaceName.value.trim()) return
  try {
    const result = await createSpace({
      name: newSpaceName.value,
      slug: newSpaceSlug.value || newSpaceName.value.toLowerCase().replace(/\s+/g, '-'),
    })
    showCreateSpace.value = false
    newSpaceName.value = ''
    newSpaceSlug.value = ''
    await selectSpace(result.id)
  } catch (e: any) {
    addToast('error', e.data?.detail || e.message)
  }
}

async function selectSpace(spaceId: string) {
  await fetchSpace(spaceId)
  await fetchPages(spaceId)
  currentPage.value = null
  editing.value = false
}

async function selectPage(pageId: string) {
  await fetchPage(pageId)
  editing.value = false
  showVersions.value = false
}

async function handleCreatePage() {
  if (!newPageTitle.value.trim() || !currentSpace.value) return
  const slug = newPageTitle.value.toLowerCase().replace(/[^a-z0-9가-힣]+/g, '-').replace(/^-|-$/g, '') || 'untitled'
  try {
    const page = await createPage(currentSpace.value.id, { title: newPageTitle.value, slug })
    showCreatePage.value = false
    newPageTitle.value = ''
    if (page) await selectPage(page.id)
  } catch (e: any) {
    addToast('error', e.data?.detail || e.message)
  }
}

const collabEditorRef = ref<any>(null)

function startEdit() {
  if (!currentPage.value) return
  editTitle.value = currentPage.value.title
  editContent.value = currentPage.value.content
  editing.value = true
}

async function savePage() {
  if (!currentPage.value) return
  const content = collabEditorRef.value?.getContent() || editContent.value
  await updatePage(currentPage.value.id, { title: editTitle.value, content })
  editing.value = false
  addToast('success', t('wiki.saved'))
}

function onEditorSave(content: string) {
  editContent.value = content
  savePage()
}

async function handleDeletePage() {
  if (!currentPage.value || !confirm(t('wiki.confirmDelete'))) return
  await deletePage(currentPage.value.id)
  addToast('success', t('wiki.pageDeleted'))
}

async function handleDeleteSpace() {
  if (!currentSpace.value || !confirm(t('wiki.confirmDeleteSpace'))) return
  await deleteSpace(currentSpace.value.id)
  currentSpace.value = null
  pageTree.value = []
  currentPage.value = null
}

async function openVersions() {
  if (!currentPage.value) return
  await fetchVersions(currentPage.value.id)
  showVersions.value = true
}

async function restoreVersion(v: any) {
  if (!currentPage.value) return
  await updatePage(currentPage.value.id, { title: v.title, content: v.content })
  showVersions.value = false
  addToast('success', `v${v.version_number} ${t('wiki.restored')}`)
}

function handleSearch() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(async () => {
    if (currentSpace.value) await searchPages(currentSpace.value.id, searchQuery.value)
  }, 300)
}
</script>

<template>
  <div v-if="user" class="flex h-full overflow-hidden">
    <!-- Left sidebar: spaces + page tree -->
    <div class="w-72 border-r flex flex-col bg-card shrink-0">
      <!-- Space selector -->
      <div class="p-3 border-b">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-sm font-semibold">{{ $t('wiki.spaces') }}</h2>
          <button @click="showCreateSpace = true" class="w-6 h-6 rounded flex items-center justify-center hover:bg-accent text-muted-foreground hover:text-foreground">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <div class="space-y-1">
          <button
            v-for="s in spaces" :key="s.id"
            @click="selectSpace(s.id)"
            class="w-full text-left px-2 py-1.5 rounded text-sm transition-colors truncate"
            :class="currentSpace?.id === s.id ? 'bg-accent font-medium' : 'hover:bg-accent/50'"
          >
            {{ s.name }}
            <span class="text-xs text-muted-foreground ml-1">({{ s.page_count }})</span>
          </button>
        </div>
      </div>

      <!-- Search -->
      <div v-if="currentSpace" class="p-3 border-b">
        <input
          v-model="searchQuery"
          @input="handleSearch"
          :placeholder="$t('wiki.searchPages')"
          class="w-full px-2 py-1.5 text-sm rounded border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <div v-if="searchResults.length" class="mt-2 space-y-1">
          <button
            v-for="r in searchResults" :key="r.id"
            @click="selectPage(r.id); searchQuery = ''; searchResults = []"
            class="w-full text-left px-2 py-1 rounded text-sm hover:bg-accent/50 truncate"
          >
            {{ r.title }}
          </button>
        </div>
      </div>

      <!-- Page tree -->
      <div v-if="currentSpace" class="flex-1 overflow-auto p-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-muted-foreground uppercase">{{ $t('wiki.pages') }}</span>
          <button
            v-if="currentSpace.user_role === 'writer' || currentSpace.user_role === 'admin'"
            @click="showCreatePage = true"
            class="w-5 h-5 rounded flex items-center justify-center hover:bg-accent text-muted-foreground hover:text-foreground"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <WikiPageTreeNode
          v-for="node in tree" :key="node.id"
          :node="node"
          :selected-id="currentPage?.id"
          :depth="0"
          @select="selectPage"
        />
        <p v-if="!pageTree.length" class="text-xs text-muted-foreground text-center py-4">{{ $t('wiki.noPages') }}</p>
      </div>

      <!-- No space selected -->
      <div v-else class="flex-1 flex items-center justify-center p-4">
        <p class="text-sm text-muted-foreground text-center">{{ $t('wiki.selectSpace') }}</p>
      </div>
    </div>

    <!-- Main content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Page view / editor -->
      <div v-if="currentPage" class="flex-1 flex flex-col overflow-hidden">
        <!-- Toolbar -->
        <div class="flex items-center gap-2 px-4 py-2 border-b shrink-0">
          <h1 v-if="!editing" class="text-lg font-semibold flex-1 truncate">{{ currentPage.title }}</h1>
          <input v-else v-model="editTitle" class="text-lg font-semibold flex-1 bg-transparent border-b border-primary focus:outline-none" />

          <span class="text-xs text-muted-foreground">v{{ currentPage.version }}</span>

          <button v-if="!editing && (currentPage.user_role === 'writer' || currentPage.user_role === 'admin')" @click="startEdit" class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90">
            {{ $t('wiki.edit') }}
          </button>
          <button v-if="editing" @click="savePage" :disabled="saving" class="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
            {{ saving ? $t('common.saving') : $t('common.save') }}
          </button>
          <button v-if="editing" @click="editing = false" class="px-3 py-1.5 text-sm rounded-md border hover:bg-accent">
            {{ $t('common.cancel') }}
          </button>
          <button @click="openVersions" class="px-2 py-1.5 text-sm rounded-md border hover:bg-accent" :title="$t('wiki.history')">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </button>
          <button v-if="currentPage.user_role === 'admin'" @click="handleDeletePage" class="px-2 py-1.5 text-sm rounded-md border hover:bg-destructive hover:text-destructive-foreground">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          </button>
        </div>

        <!-- Collaborative Editor (always mounted when page selected) -->
        <WikiCollabEditor
          v-if="editing"
          ref="collabEditorRef"
          :page-id="currentPage.id"
          :initial-content="currentPage.content"
          :readonly="false"
          @save="onEditorSave"
        />

        <!-- Read-only view -->
        <div v-else class="flex-1 overflow-auto px-6 py-4 prose prose-sm dark:prose-invert max-w-none" v-html="currentPage.content || '<p class=\'text-muted-foreground italic\'>빈 페이지</p>'" />

        <!-- Meta -->
        <div class="px-4 py-2 border-t text-xs text-muted-foreground flex gap-4 shrink-0">
          <span>{{ $t('wiki.author') }}: {{ currentPage.author.display_name || currentPage.author.username }}</span>
          <span>{{ $t('wiki.lastUpdated') }}: {{ new Date(currentPage.updated_at).toLocaleString() }}</span>
        </div>
      </div>

      <!-- No page selected -->
      <div v-else class="flex-1 flex items-center justify-center text-muted-foreground">
        <div class="text-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-16 w-16 mx-auto mb-4 opacity-40">
            <path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>
          </svg>
          <p v-if="currentSpace" class="text-sm">{{ $t('wiki.selectPage') }}</p>
          <p v-else class="text-sm">{{ $t('wiki.selectSpace') }}</p>
        </div>
      </div>
    </div>

    <!-- Version history panel -->
    <div v-if="showVersions" class="w-80 border-l bg-card flex flex-col shrink-0">
      <div class="p-3 border-b flex items-center justify-between">
        <h3 class="font-semibold text-sm">{{ $t('wiki.versionHistory') }}</h3>
        <button @click="showVersions = false" class="w-6 h-6 rounded flex items-center justify-center hover:bg-accent">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      <div class="flex-1 overflow-auto">
        <div
          v-for="v in versions" :key="v.id"
          class="p-3 border-b hover:bg-accent/50 cursor-pointer"
          @click="restoreVersion(v)"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium">v{{ v.version_number }}</span>
            <span class="text-xs text-muted-foreground">{{ new Date(v.created_at).toLocaleString() }}</span>
          </div>
          <p class="text-xs text-muted-foreground mt-0.5">{{ v.author.display_name || v.author.username }}</p>
          <p class="text-xs mt-1 truncate">{{ v.title }}</p>
        </div>
      </div>
    </div>

    <!-- Create space modal -->
    <Teleport to="body">
      <div v-if="showCreateSpace" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showCreateSpace = false">
        <div class="bg-card rounded-lg shadow-xl w-full max-w-md p-6">
          <h3 class="text-lg font-semibold mb-4">{{ $t('wiki.createSpace') }}</h3>
          <div class="space-y-3">
            <div>
              <label class="text-sm font-medium">{{ $t('wiki.spaceName') }}</label>
              <input v-model="newSpaceName" class="w-full mt-1 px-3 py-2 rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-primary" />
            </div>
            <div>
              <label class="text-sm font-medium">{{ $t('wiki.slug') }}</label>
              <input v-model="newSpaceSlug" class="w-full mt-1 px-3 py-2 rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-primary" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button @click="showCreateSpace = false" class="px-4 py-2 text-sm rounded-md border hover:bg-accent">{{ $t('common.cancel') }}</button>
            <button @click="handleCreateSpace" class="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90">{{ $t('common.create') }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Create page modal -->
    <Teleport to="body">
      <div v-if="showCreatePage" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showCreatePage = false">
        <div class="bg-card rounded-lg shadow-xl w-full max-w-md p-6">
          <h3 class="text-lg font-semibold mb-4">{{ $t('wiki.createPage') }}</h3>
          <div>
            <label class="text-sm font-medium">{{ $t('wiki.pageTitle') }}</label>
            <input v-model="newPageTitle" @keyup.enter="handleCreatePage" class="w-full mt-1 px-3 py-2 rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-primary" />
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <button @click="showCreatePage = false" class="px-4 py-2 text-sm rounded-md border hover:bg-accent">{{ $t('common.cancel') }}</button>
            <button @click="handleCreatePage" class="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90">{{ $t('common.create') }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
// Markdown renderer helper (available to template)
function renderMarkdown(content: string): string {
  if (!content) return '<p class="text-muted-foreground italic">빈 페이지</p>'
  // Simple markdown → HTML (uses markdown-it if available, otherwise basic conversion)
  try {
    const MarkdownIt = require('markdown-it')
    const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
    return md.render(content)
  } catch {
    // Fallback: basic conversion
    return content
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>')
  }
}
</script>
