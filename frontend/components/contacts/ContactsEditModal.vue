<script setup lang="ts">
import type { TypedValue } from '~/composables/useContacts'

const {
  addressBooks, showEditModal, editingContact,
  createContact, updateContact, closeModal,
} = useContacts()

const { t } = useI18n()
const form = reactive({
  address_book_id: '',
  name: '',
  first_name: '',
  last_name: '',
  organization: '',
  emails: [] as TypedValue[],
  phones: [] as TypedValue[],
  addresses: [] as TypedValue[],
  notes: '',
})
const error = ref('')
const submitting = ref(false)

const isEditing = computed(() => !!editingContact.value)
const modalTitle = computed(() => isEditing.value ? t('contacts.edit.editTitle') : t('contacts.edit.createTitle'))

watch(showEditModal, (show) => {
  if (!show) return
  error.value = ''
  if (editingContact.value) {
    const c = editingContact.value
    form.address_book_id = c.address_book_id
    form.name = c.name
    form.first_name = c.first_name || ''
    form.last_name = c.last_name || ''
    form.organization = c.organization || ''
    form.emails = c.emails.length > 0 ? [...c.emails] : [{ type: 'work', value: '' }]
    form.phones = c.phones.length > 0 ? [...c.phones] : [{ type: 'work', value: '' }]
    form.addresses = [...c.addresses]
    form.notes = c.notes || ''
  } else {
    form.address_book_id = addressBooks.value[0]?.id || ''
    form.name = ''
    form.first_name = ''
    form.last_name = ''
    form.organization = ''
    form.emails = [{ type: 'work', value: '' }]
    form.phones = [{ type: 'work', value: '' }]
    form.addresses = []
    form.notes = ''
  }
})

function addEmail() { form.emails.push({ type: 'other', value: '' }) }
function removeEmail(i: number) { form.emails.splice(i, 1) }
function addPhone() { form.phones.push({ type: 'other', value: '' }) }
function removePhone(i: number) { form.phones.splice(i, 1) }
function addAddress() { form.addresses.push({ type: 'home', value: '' }) }
function removeAddress(i: number) { form.addresses.splice(i, 1) }

async function handleSubmit() {
  if (!form.name.trim()) {
    error.value = t('contacts.edit.nameRequired')
    return
  }
  if (!form.address_book_id) {
    error.value = t('contacts.edit.addressBookRequired')
    return
  }

  submitting.value = true
  error.value = ''
  try {
    const data = {
      address_book_id: form.address_book_id,
      name: form.name.trim(),
      first_name: form.first_name.trim() || undefined,
      last_name: form.last_name.trim() || undefined,
      organization: form.organization.trim() || undefined,
      emails: form.emails.filter(e => e.value.trim()),
      phones: form.phones.filter(p => p.value.trim()),
      addresses: form.addresses.filter(a => a.value.trim()),
      notes: form.notes.trim() || undefined,
    }

    if (isEditing.value) {
      await updateContact(editingContact.value!.id, data)
    } else {
      await createContact(data)
    }
    closeModal()
  } catch (e: any) {
    error.value = e?.data?.detail || t('contacts.edit.saveError')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="closeModal" />

      <div class="relative w-full max-w-lg bg-background border rounded-xl shadow-lg max-h-[85vh] overflow-y-auto" role="dialog">
        <div class="flex items-center justify-between px-5 py-4 border-b sticky top-0 bg-background z-10">
          <h2 class="text-lg font-semibold">{{ modalTitle }}</h2>
          <button @click="closeModal" class="p-1 rounded hover:bg-accent">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="px-5 py-4 space-y-4">
          <!-- Address book -->
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.addressBookLabel') }}</label>
            <select v-model="form.address_book_id" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50">
              <option v-for="book in addressBooks" :key="book.id" :value="book.id">{{ book.name }}</option>
            </select>
          </div>

          <!-- Name -->
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.nameLabel') }}</label>
            <input v-model="form.name" type="text" :placeholder="$t('contacts.edit.namePlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.lastNameLabel') }}</label>
              <input v-model="form.last_name" type="text" :placeholder="$t('contacts.edit.lastNamePlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.firstNameLabel') }}</label>
              <input v-model="form.first_name" type="text" :placeholder="$t('contacts.edit.firstNamePlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
            </div>
          </div>

          <!-- Organization -->
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.organizationLabel') }}</label>
            <input v-model="form.organization" type="text" :placeholder="$t('contacts.edit.organizationPlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>

          <!-- Emails -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-sm font-medium">{{ $t('contacts.edit.emailLabel') }}</label>
              <button type="button" @click="addEmail" class="text-xs text-primary hover:underline">{{ $t('common.addItem') }}</button>
            </div>
            <div v-for="(email, i) in form.emails" :key="i" class="flex gap-2 mb-1.5">
              <select v-model="email.type" class="w-20 px-2 py-2 text-sm border rounded-lg bg-background shrink-0">
                <option value="work">{{ $t('contacts.type.work') }}</option>
                <option value="home">{{ $t('contacts.type.home') }}</option>
                <option value="other">{{ $t('contacts.type.other') }}</option>
              </select>
              <input v-model="email.value" type="email" placeholder="email@example.com" class="flex-1 px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
              <button type="button" @click="removeEmail(i)" class="p-1 text-muted-foreground hover:text-destructive shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>

          <!-- Phones -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-sm font-medium">{{ $t('contacts.edit.phoneLabel') }}</label>
              <button type="button" @click="addPhone" class="text-xs text-primary hover:underline">{{ $t('common.addItem') }}</button>
            </div>
            <div v-for="(phone, i) in form.phones" :key="i" class="flex gap-2 mb-1.5">
              <select v-model="phone.type" class="w-20 px-2 py-2 text-sm border rounded-lg bg-background shrink-0">
                <option value="work">{{ $t('contacts.type.work') }}</option>
                <option value="home">{{ $t('contacts.type.home') }}</option>
                <option value="other">{{ $t('contacts.type.other') }}</option>
              </select>
              <input v-model="phone.value" type="tel" placeholder="010-0000-0000" class="flex-1 px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
              <button type="button" @click="removePhone(i)" class="p-1 text-muted-foreground hover:text-destructive shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>

          <!-- Addresses -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-sm font-medium">{{ $t('contacts.edit.addressLabel') }}</label>
              <button type="button" @click="addAddress" class="text-xs text-primary hover:underline">{{ $t('common.addItem') }}</button>
            </div>
            <div v-for="(addr, i) in form.addresses" :key="i" class="flex gap-2 mb-1.5">
              <select v-model="addr.type" class="w-20 px-2 py-2 text-sm border rounded-lg bg-background shrink-0">
                <option value="home">{{ $t('contacts.type.home') }}</option>
                <option value="work">{{ $t('contacts.type.work') }}</option>
                <option value="other">{{ $t('contacts.type.other') }}</option>
              </select>
              <input v-model="addr.value" type="text" :placeholder="$t('contacts.edit.addressPlaceholder')" class="flex-1 px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
              <button type="button" @click="removeAddress(i)" class="p-1 text-muted-foreground hover:text-destructive shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>

          <!-- Notes -->
          <div>
            <label class="block text-sm font-medium mb-1">{{ $t('contacts.edit.notesLabel') }}</label>
            <textarea v-model="form.notes" rows="2" :placeholder="$t('contacts.edit.notesPlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none" />
          </div>

          <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

          <div class="flex justify-end gap-2 pt-1">
            <button type="button" @click="closeModal" class="px-4 py-2 text-sm rounded-lg hover:bg-accent transition-colors">{{ $t('common.cancel') }}</button>
            <button type="submit" :disabled="submitting" class="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors">
              {{ submitting ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
