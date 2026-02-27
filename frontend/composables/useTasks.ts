interface Task {
  id: string
  title: string
  description: string | null
  due_date: string | null
  priority: 'low' | 'medium' | 'high'
  status: 'todo' | 'in_progress' | 'done'
  sort_order: number
  created_at: string
  updated_at: string
}

interface TaskListResponse {
  tasks: Task[]
  total: number
}

interface TaskCreateData {
  title: string
  description?: string
  due_date?: string | null
  priority?: 'low' | 'medium' | 'high'
  status?: 'todo' | 'in_progress' | 'done'
}

interface TaskFilters {
  status?: string | null
  priority?: string | null
  sort_by?: string
  sort_dir?: string
  page?: number
  limit?: number
}

export function useTasks() {
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchTasks(filters: TaskFilters = {}) {
    loading.value = true
    try {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.priority) params.set('priority', filters.priority)
      if (filters.sort_by) params.set('sort_by', filters.sort_by)
      if (filters.sort_dir) params.set('sort_dir', filters.sort_dir)
      if (filters.page !== undefined) params.set('page', String(filters.page))
      if (filters.limit !== undefined) params.set('limit', String(filters.limit))
      const qs = params.toString()
      const data = await $fetch<TaskListResponse>(`/api/tasks/${qs ? `?${qs}` : ''}`)
      tasks.value = data.tasks
      total.value = data.total
    } catch {
      tasks.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: TaskCreateData): Promise<Task> {
    const result = await $fetch<Task>('/api/tasks/', {
      method: 'POST',
      body: data,
    })
    return result
  }

  async function updateTask(id: string, data: Partial<TaskCreateData>): Promise<Task> {
    const result = await $fetch<Task>(`/api/tasks/${id}`, {
      method: 'PATCH',
      body: data,
    })
    return result
  }

  async function deleteTask(id: string): Promise<void> {
    await $fetch(`/api/tasks/${id}`, { method: 'DELETE' })
  }

  async function toggleTask(id: string): Promise<Task> {
    const result = await $fetch<Task>(`/api/tasks/${id}/toggle`, {
      method: 'POST',
    })
    return result
  }

  return {
    tasks: readonly(tasks),
    total: readonly(total),
    loading: readonly(loading),
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    toggleTask,
  }
}
