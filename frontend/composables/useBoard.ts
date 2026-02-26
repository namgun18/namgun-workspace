/**
 * Board composable — singleton state management + API calls.
 */

export interface BoardInfo {
  id: string
  name: string
  slug: string
  description: string | null
  categories: string[]
  sort_order: number
  write_permission: string
  notice_permission: string
  comment_permission: string
  allow_comments: boolean
  allow_reactions: boolean
  created_at: string
  updated_at: string
}

export interface AuthorInfo {
  id: string
  username: string
  display_name: string | null
  avatar_url: string | null
}

export interface PostSummary {
  id: string
  board_id: string
  author: AuthorInfo | null
  title: string
  category: string | null
  is_pinned: boolean
  is_must_read: boolean
  view_count: number
  comment_count: number
  has_attachments: boolean
  is_edited: boolean
  created_at: string
  updated_at: string
  board_name?: string
}

export interface ReactionGroup {
  emoji: string
  count: number
  user_ids: string[]
  reacted: boolean
}

export interface PostDetail {
  id: string
  board_id: string
  author: AuthorInfo | null
  title: string
  content: string
  category: string | null
  is_pinned: boolean
  is_must_read: boolean
  must_read_expires_at: string | null
  view_count: number
  comment_count: number
  attachments: Array<{ name: string; url: string; size?: number }>
  reactions: ReactionGroup[]
  is_bookmarked: boolean
  is_edited: boolean
  created_at: string
  updated_at: string
}

export interface CommentInfo {
  id: string
  post_id: string
  author: AuthorInfo | null
  parent_id: string | null
  content: string
  attachments: Array<{ name: string; url: string; size?: number }>
  is_edited: boolean
  is_deleted: boolean
  created_at: string
  updated_at: string
  replies?: CommentInfo[]
}

interface PostListResponse {
  pinned: PostSummary[]
  posts: PostSummary[]
  total: number
  page: number
  page_size: number
}

interface SearchResponse {
  posts: PostSummary[]
  total: number
  page: number
  page_size: number
}

// Module-level singleton state
const boards = ref<BoardInfo[]>([])
const currentBoard = ref<BoardInfo | null>(null)
const posts = ref<PostSummary[]>([])
const pinnedPosts = ref<PostSummary[]>([])
const currentPost = ref<PostDetail | null>(null)
const comments = ref<CommentInfo[]>([])
const pagination = ref({ total: 0, page: 1, page_size: 20 })
const selectedCategory = ref<string | null>(null)
const sortBy = ref<'latest' | 'views' | 'comments'>('latest')
const mustReadPosts = ref<PostSummary[]>([])

const loadingBoards = ref(false)
const loadingPosts = ref(false)
const loadingPost = ref(false)
const loadingComments = ref(false)

let _initialized = false

export function useBoard() {
  const { user } = useAuth()

  // ─── Boards ───

  async function fetchBoards() {
    loadingBoards.value = true
    try {
      const data = await $fetch<BoardInfo[]>('/api/board/boards')
      boards.value = data
    } catch (e: any) {
      console.error('fetchBoards error:', e)
    } finally {
      loadingBoards.value = false
    }
  }

  async function selectBoard(boardId: string) {
    currentBoard.value = boards.value.find(b => b.id === boardId) || null
    selectedCategory.value = null
    sortBy.value = 'latest'
    pagination.value.page = 1
    await fetchPosts(boardId)
  }

  async function createBoard(data: {
    name: string
    slug: string
    description?: string
    categories?: string[]
    write_permission?: string
    notice_permission?: string
    comment_permission?: string
    allow_comments?: boolean
    allow_reactions?: boolean
  }) {
    const result = await $fetch<BoardInfo>('/api/board/boards', {
      method: 'POST',
      body: data,
    })
    await fetchBoards()
    return result
  }

  async function updateBoard(boardId: string, data: Record<string, any>) {
    await $fetch(`/api/board/boards/${boardId}`, {
      method: 'PATCH',
      body: data,
    })
    await fetchBoards()
  }

  async function deleteBoard(boardId: string) {
    await $fetch(`/api/board/boards/${boardId}`, { method: 'DELETE' })
    boards.value = boards.value.filter(b => b.id !== boardId)
    if (currentBoard.value?.id === boardId) {
      currentBoard.value = null
      posts.value = []
      pinnedPosts.value = []
    }
  }

  // ─── Posts ───

  async function fetchPosts(boardId?: string, page?: number) {
    const bid = boardId || currentBoard.value?.id
    if (!bid) return
    loadingPosts.value = true
    try {
      const params: Record<string, any> = {
        page: page || pagination.value.page,
        page_size: pagination.value.page_size,
        sort: sortBy.value,
      }
      if (selectedCategory.value) params.category = selectedCategory.value

      const data = await $fetch<PostListResponse>(`/api/board/boards/${bid}/posts`, { params })
      pinnedPosts.value = data.pinned
      posts.value = data.posts
      pagination.value = {
        total: data.total,
        page: data.page,
        page_size: data.page_size,
      }
    } catch (e: any) {
      console.error('fetchPosts error:', e)
    } finally {
      loadingPosts.value = false
    }
  }

  async function fetchPost(postId: string) {
    loadingPost.value = true
    try {
      const data = await $fetch<PostDetail>(`/api/board/posts/${postId}`)
      // Map reactions with reacted status
      const uid = user.value?.id
      if (data.reactions) {
        data.reactions = data.reactions.map(r => ({
          ...r,
          reacted: uid ? (r.user_ids || []).includes(uid) : false,
        }))
      }
      currentPost.value = data
    } catch (e: any) {
      console.error('fetchPost error:', e)
      currentPost.value = null
    } finally {
      loadingPost.value = false
    }
  }

  async function createPost(boardId: string, data: {
    title: string
    content: string
    category?: string | null
    is_pinned?: boolean
    is_must_read?: boolean
    must_read_expires_at?: string | null
    attachments?: Array<{ name: string; url: string; size?: number }> | null
  }) {
    return await $fetch<PostDetail>(`/api/board/boards/${boardId}/posts`, {
      method: 'POST',
      body: data,
    })
  }

  async function updatePost(postId: string, data: Record<string, any>) {
    const result = await $fetch<PostDetail>(`/api/board/posts/${postId}`, {
      method: 'PATCH',
      body: data,
    })
    currentPost.value = result
    return result
  }

  async function deletePost(postId: string) {
    await $fetch(`/api/board/posts/${postId}`, { method: 'DELETE' })
    posts.value = posts.value.filter(p => p.id !== postId)
    pinnedPosts.value = pinnedPosts.value.filter(p => p.id !== postId)
    if (currentPost.value?.id === postId) {
      currentPost.value = null
    }
  }

  // ─── Comments ───

  async function fetchComments(postId: string) {
    loadingComments.value = true
    try {
      const data = await $fetch<CommentInfo[]>(`/api/board/posts/${postId}/comments`)
      comments.value = data
    } catch (e: any) {
      console.error('fetchComments error:', e)
    } finally {
      loadingComments.value = false
    }
  }

  async function createComment(postId: string, content: string, parentId?: string | null, attachments?: Array<{ name: string; url: string }> | null) {
    const body: Record<string, any> = { content }
    if (parentId) body.parent_id = parentId
    if (attachments) body.attachments = attachments
    const result = await $fetch<CommentInfo>(`/api/board/posts/${postId}/comments`, {
      method: 'POST',
      body,
    })
    await fetchComments(postId)
    return result
  }

  async function updateComment(commentId: string, content: string) {
    await $fetch(`/api/board/comments/${commentId}`, {
      method: 'PATCH',
      body: { content },
    })
    if (currentPost.value) {
      await fetchComments(currentPost.value.id)
    }
  }

  async function deleteComment(commentId: string) {
    await $fetch(`/api/board/comments/${commentId}`, { method: 'DELETE' })
    if (currentPost.value) {
      await fetchComments(currentPost.value.id)
    }
  }

  // ─── Reactions ───

  async function toggleReaction(postId: string, emoji: string) {
    try {
      const result = await $fetch<{ action: string; reactions: any[] }>(
        `/api/board/posts/${postId}/reactions`,
        { method: 'POST', body: { emoji } }
      )
      // Update current post reactions
      if (currentPost.value?.id === postId) {
        const uid = user.value?.id
        currentPost.value = {
          ...currentPost.value,
          reactions: (result.reactions || []).map((r: any) => ({
            emoji: r.emoji,
            count: r.count,
            user_ids: r.user_ids || [],
            reacted: uid ? (r.user_ids || []).includes(uid) : false,
          })),
        }
      }
    } catch (e: any) {
      console.error('toggleReaction error:', e)
    }
  }

  // ─── Bookmarks ───

  async function toggleBookmark(postId: string) {
    try {
      const result = await $fetch<{ action: string; is_bookmarked: boolean }>(
        `/api/board/posts/${postId}/bookmark`,
        { method: 'POST' }
      )
      if (currentPost.value?.id === postId) {
        currentPost.value = {
          ...currentPost.value,
          is_bookmarked: result.is_bookmarked,
        }
      }
      return result
    } catch (e: any) {
      console.error('toggleBookmark error:', e)
    }
  }

  async function fetchBookmarks(page = 1) {
    const data = await $fetch<SearchResponse>('/api/board/bookmarks', {
      params: { page, page_size: 20 },
    })
    return data
  }

  // ─── Must Read ───

  async function fetchMustRead() {
    try {
      const data = await $fetch<PostSummary[]>('/api/board/must-read')
      mustReadPosts.value = data
    } catch (e: any) {
      console.error('fetchMustRead error:', e)
    }
  }

  // ─── Search ───

  async function searchPosts(query: string, boardId?: string, page = 1) {
    const params: Record<string, any> = { q: query, page, page_size: 20 }
    if (boardId) params.board_id = boardId
    return await $fetch<SearchResponse>('/api/board/search', { params })
  }

  // ─── Pagination ───

  async function goToPage(page: number) {
    pagination.value.page = page
    await fetchPosts()
  }

  async function setCategory(cat: string | null) {
    selectedCategory.value = cat
    pagination.value.page = 1
    await fetchPosts()
  }

  async function setSort(sort: 'latest' | 'views' | 'comments') {
    sortBy.value = sort
    pagination.value.page = 1
    await fetchPosts()
  }

  // ─── Init ───

  async function init() {
    if (_initialized) return
    _initialized = true
    await Promise.all([fetchBoards(), fetchMustRead()])
  }

  function cleanup() {
    _initialized = false
  }

  return {
    // State
    boards: readonly(boards),
    currentBoard: readonly(currentBoard),
    posts: readonly(posts),
    pinnedPosts: readonly(pinnedPosts),
    currentPost: readonly(currentPost),
    comments: readonly(comments),
    pagination: readonly(pagination),
    selectedCategory: readonly(selectedCategory),
    sortBy: readonly(sortBy),
    mustReadPosts: readonly(mustReadPosts),
    loadingBoards: readonly(loadingBoards),
    loadingPosts: readonly(loadingPosts),
    loadingPost: readonly(loadingPost),
    loadingComments: readonly(loadingComments),
    // Actions
    init,
    cleanup,
    fetchBoards,
    selectBoard,
    createBoard,
    updateBoard,
    deleteBoard,
    fetchPosts,
    fetchPost,
    createPost,
    updatePost,
    deletePost,
    fetchComments,
    createComment,
    updateComment,
    deleteComment,
    toggleReaction,
    toggleBookmark,
    fetchBookmarks,
    fetchMustRead,
    searchPosts,
    goToPage,
    setCategory,
    setSort,
  }
}
