<script setup lang="ts">
const emit = defineEmits<{
  close: []
}>()

const { createBoard } = useBoard()

const name = ref('')
const slug = ref('')
const description = ref('')
const categories = ref('')
const writePermission = ref('all')
const submitting = ref(false)

// Auto-generate slug from name
watch(name, (val) => {
  if (!slug.value || slug.value === slugify(name.value.slice(0, -1))) {
    slug.value = slugify(val)
  }
})

function slugify(str: string): string {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9가-힣\s-]/g, '')
    .replace(/[\s]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 100)
}

async function handleSubmit() {
  if (!name.value.trim() || !slug.value.trim()) {
    alert('이름과 슬러그를 입력해주세요')
    return
  }
  submitting.value = true
  try {
    const cats = categories.value
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)

    await createBoard({
      name: name.value,
      slug: slug.value,
      description: description.value || undefined,
      categories: cats.length > 0 ? cats : undefined,
      write_permission: writePermission.value,
    })
    emit('close')
  } catch (e: any) {
    console.error('Create board error:', e)
    alert(e?.data?.detail || '게시판 생성에 실패했습니다')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40" @click="emit('close')" />
      <div class="relative bg-background rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold mb-4">게시판 만들기</h2>

        <div class="space-y-3">
          <div>
            <label class="text-sm font-medium mb-1 block">이름</label>
            <input v-model="name" type="text" placeholder="예: 공지사항" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">슬러그 (URL)</label>
            <input v-model="slug" type="text" placeholder="예: notice" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">설명 (선택)</label>
            <input v-model="description" type="text" placeholder="게시판 설명" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">말머리 (쉼표 구분)</label>
            <input v-model="categories" type="text" placeholder="예: 일반, 긴급, 안내" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">글쓰기 권한</label>
            <select v-model="writePermission" class="w-full h-9 rounded-md border bg-background px-3 text-sm">
              <option value="all">모든 사용자</option>
              <option value="admin">관리자만</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <UiButton variant="outline" @click="emit('close')">취소</UiButton>
          <UiButton @click="handleSubmit" :disabled="submitting">
            {{ submitting ? '생성 중...' : '생성' }}
          </UiButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
