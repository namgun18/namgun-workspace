<script setup lang="ts">
const { t } = useI18n()

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
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/[\s]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 100)
}

async function handleSubmit() {
  if (!name.value.trim() || !slug.value.trim()) {
    alert(t('board.create.nameSlugRequired'))
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
    const detail = e?.data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : t('board.create.error')
    alert(msg)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40" @click="emit('close')" />
      <div class="relative bg-background rounded-lg shadow-xl w-full max-w-md p-6" role="dialog">
        <h2 class="text-lg font-semibold mb-4">{{ $t('board.create.title') }}</h2>

        <div class="space-y-3">
          <div>
            <label class="text-sm font-medium mb-1 block">{{ $t('board.create.nameLabel') }}</label>
            <input v-model="name" type="text" :placeholder="$t('board.create.namePlaceholder')" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">{{ $t('board.create.slugLabel') }}</label>
            <input v-model="slug" type="text" :placeholder="$t('board.create.slugPlaceholder')" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">{{ $t('board.create.descriptionLabel') }}</label>
            <input v-model="description" type="text" :placeholder="$t('board.create.descriptionPlaceholder')" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">{{ $t('board.create.categoriesLabel') }}</label>
            <input v-model="categories" type="text" :placeholder="$t('board.create.categoriesPlaceholder')" class="w-full h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <div>
            <label class="text-sm font-medium mb-1 block">{{ $t('board.create.writePermissionLabel') }}</label>
            <select v-model="writePermission" class="w-full h-9 rounded-md border bg-background px-3 text-sm">
              <option value="all">{{ $t('board.create.writePermissionAll') }}</option>
              <option value="admin">{{ $t('board.create.writePermissionAdmin') }}</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <UiButton variant="outline" @click="emit('close')">{{ $t('common.cancel') }}</UiButton>
          <UiButton @click="handleSubmit" :disabled="submitting">
            {{ submitting ? $t('board.create.submitting') : $t('board.create.submit') }}
          </UiButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
