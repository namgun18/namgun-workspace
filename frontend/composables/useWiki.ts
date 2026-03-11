/**
 * Wiki composable — singleton state management + API calls.
 */

export interface WikiAuthor {
  id?: string
  username: string
  display_name: string | null
  avatar_url?: string | null
}

export interface WikiSpace {
  id: string
  name: string
  slug: string
  description: string | null
  visibility: string
  icon: string | null
  owner: WikiAuthor
  page_count: number
  user_role?: string
  created_at: string
  updated_at: string
}

export interface WikiPageNode {
  id: string
  parent_id: string | null
  title: string
  slug: string
  sort_order: number
  is_pinned: boolean
  version: number
  author: WikiAuthor
  updated_at: string
}

export interface WikiPageDetail {
  id: string
  space_id: string
  parent_id: string | null
  title: string
  slug: string
  content: string
  sort_order: number
  is_pinned: boolean
  version: number
  author: WikiAuthor
  user_role?: string
  created_at: string
  updated_at: string
}

export interface WikiPageVersion {
  id: string
  version_number: number
  title: string
  content: string
  author: WikiAuthor
  created_at: string
}

export interface WikiMember {
  user_id: string
  role: string
  username: string
  display_name: string | null
  avatar_url: string | null
}

// Singleton state
const spaces = ref<WikiSpace[]>([])
const currentSpace = ref<WikiSpace | null>(null)
const pageTree = ref<WikiPageNode[]>([])
const currentPage = ref<WikiPageDetail | null>(null)
const versions = ref<WikiPageVersion[]>([])
const loading = ref(false)
const saving = ref(false)
const searchResults = ref<WikiPageNode[]>([])

export function useWiki() {
  // ─── Spaces ───

  async function fetchSpaces() {
    loading.value = true
    try {
      spaces.value = await $fetch<WikiSpace[]>('/api/wiki/spaces')
    } finally {
      loading.value = false
    }
  }

  async function fetchSpace(spaceId: string) {
    currentSpace.value = await $fetch<WikiSpace>(`/api/wiki/spaces/${spaceId}`)
  }

  async function createSpace(data: { name: string; slug: string; description?: string; visibility?: string; icon?: string }) {
    const result = await $fetch<{ id: string }>('/api/wiki/spaces', { method: 'POST', body: data })
    await fetchSpaces()
    return result
  }

  async function updateSpace(spaceId: string, data: Record<string, any>) {
    await $fetch(`/api/wiki/spaces/${spaceId}`, { method: 'PATCH', body: data })
    await fetchSpaces()
  }

  async function deleteSpace(spaceId: string) {
    await $fetch(`/api/wiki/spaces/${spaceId}`, { method: 'DELETE' })
    spaces.value = spaces.value.filter(s => s.id !== spaceId)
    if (currentSpace.value?.id === spaceId) currentSpace.value = null
  }

  // ─── Pages ───

  async function fetchPages(spaceId: string) {
    pageTree.value = await $fetch<WikiPageNode[]>(`/api/wiki/spaces/${spaceId}/pages`)
  }

  async function fetchPage(pageId: string) {
    currentPage.value = await $fetch<WikiPageDetail>(`/api/wiki/pages/${pageId}`)
  }

  async function createPage(spaceId: string, data: { title: string; slug: string; content?: string; parent_id?: string }) {
    const page = await $fetch<WikiPageDetail>(`/api/wiki/spaces/${spaceId}/pages`, { method: 'POST', body: data })
    await fetchPages(spaceId)
    return page
  }

  async function updatePage(pageId: string, data: Record<string, any>) {
    saving.value = true
    try {
      currentPage.value = await $fetch<WikiPageDetail>(`/api/wiki/pages/${pageId}`, { method: 'PATCH', body: data })
      if (currentPage.value) await fetchPages(currentPage.value.space_id)
    } finally {
      saving.value = false
    }
  }

  async function deletePage(pageId: string) {
    const spaceId = currentPage.value?.space_id
    await $fetch(`/api/wiki/pages/${pageId}`, { method: 'DELETE' })
    if (spaceId) await fetchPages(spaceId)
    if (currentPage.value?.id === pageId) currentPage.value = null
  }

  // ─── Versions ───

  async function fetchVersions(pageId: string) {
    versions.value = await $fetch<WikiPageVersion[]>(`/api/wiki/pages/${pageId}/versions`)
  }

  // ─── Search ───

  async function searchPages(spaceId: string, query: string) {
    if (!query.trim()) {
      searchResults.value = []
      return
    }
    searchResults.value = await $fetch<WikiPageNode[]>(`/api/wiki/spaces/${spaceId}/search`, {
      params: { q: query },
    })
  }

  // ─── Members ───

  async function fetchMembers(spaceId: string) {
    return await $fetch<WikiMember[]>(`/api/wiki/spaces/${spaceId}/members`)
  }

  async function addMember(spaceId: string, userId: string, role: string = 'reader') {
    await $fetch(`/api/wiki/spaces/${spaceId}/members`, { method: 'POST', body: { user_id: userId, role } })
  }

  async function removeMember(spaceId: string, userId: string) {
    await $fetch(`/api/wiki/spaces/${spaceId}/members/${userId}`, { method: 'DELETE' })
  }

  // ─── Tree helpers ───

  function buildTree(nodes: WikiPageNode[], parentId: string | null = null): (WikiPageNode & { children: any[] })[] {
    return nodes
      .filter(n => n.parent_id === parentId)
      .sort((a, b) => a.sort_order - b.sort_order || a.title.localeCompare(b.title))
      .map(n => ({ ...n, children: buildTree(nodes, n.id) }))
  }

  return {
    spaces, currentSpace, pageTree, currentPage, versions, loading, saving, searchResults,
    fetchSpaces, fetchSpace, createSpace, updateSpace, deleteSpace,
    fetchPages, fetchPage, createPage, updatePage, deletePage,
    fetchVersions, searchPages,
    fetchMembers, addMember, removeMember,
    buildTree,
  }
}
