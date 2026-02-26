<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { accounts, fetchAccounts } = useMail()

const showForm = ref(false)
const editing = ref<string | null>(null)
const testing = ref<string | null>(null)
const testResult = ref<any>(null)
const saving = ref(false)

const form = ref({
  display_name: '',
  email: '',
  imap_host: '',
  imap_port: 993,
  imap_security: 'ssl',
  smtp_host: '',
  smtp_port: 587,
  smtp_security: 'starttls',
  username: '',
  password: '',
  is_default: false,
})

function resetForm() {
  form.value = {
    display_name: '', email: '',
    imap_host: '', imap_port: 993, imap_security: 'ssl',
    smtp_host: '', smtp_port: 587, smtp_security: 'starttls',
    username: '', password: '', is_default: false,
  }
  editing.value = null
}

function openCreate() {
  resetForm()
  showForm.value = true
}

function openEdit(account: any) {
  editing.value = account.id
  form.value = {
    display_name: account.display_name,
    email: account.email,
    imap_host: account.imap_host,
    imap_port: account.imap_port,
    imap_security: account.imap_security,
    smtp_host: account.smtp_host,
    smtp_port: account.smtp_port,
    smtp_security: account.smtp_security,
    username: account.username,
    password: '',
    is_default: account.is_default,
  }
  showForm.value = true
}

async function saveAccount() {
  saving.value = true
  try {
    if (editing.value) {
      const body: any = { ...form.value }
      if (!body.password) delete body.password
      await $fetch(`/api/mail/accounts/${editing.value}`, { method: 'PATCH', body })
    } else {
      await $fetch('/api/mail/accounts', { method: 'POST', body: form.value })
    }
    showForm.value = false
    resetForm()
    await fetchAccounts()
  } catch (e: any) {
    alert(e.data?.detail || '저장 실패')
  } finally {
    saving.value = false
  }
}

async function deleteAccount(id: string) {
  if (!confirm('이 메일 계정을 삭제하시겠습니까?')) return
  try {
    await $fetch(`/api/mail/accounts/${id}`, { method: 'DELETE' })
    await fetchAccounts()
  } catch (e: any) {
    alert(e.data?.detail || '삭제 실패')
  }
}

async function testConnection(id: string) {
  testing.value = id
  testResult.value = null
  try {
    testResult.value = await $fetch(`/api/mail/accounts/${id}/test`, { method: 'POST' })
  } catch (e: any) {
    testResult.value = { error: e.data?.detail || '테스트 실패' }
  } finally {
    testing.value = null
  }
}

onMounted(() => fetchAccounts())
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">메일 계정 설정</h1>
        <p class="text-muted-foreground text-sm mt-1">Gmail, Outlook 등 외부 메일 계정을 연결합니다.</p>
      </div>
      <button @click="openCreate" class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90">
        계정 추가
      </button>
    </div>

    <!-- Account list -->
    <div class="space-y-3 mb-6">
      <div
        v-for="acct in accounts"
        :key="acct.id"
        class="border rounded-lg p-4 bg-card"
      >
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-medium">{{ acct.display_name }}</h3>
            <p class="text-sm text-muted-foreground">{{ acct.email }}</p>
            <p class="text-xs text-muted-foreground mt-1">
              IMAP: {{ acct.imap_host }}:{{ acct.imap_port }} &middot;
              SMTP: {{ acct.smtp_host }}:{{ acct.smtp_port }}
            </p>
            <span v-if="acct.is_default" class="inline-block mt-1 text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">기본</span>
          </div>
          <div class="flex items-center gap-2">
            <button @click="testConnection(acct.id)" :disabled="testing === acct.id"
                    class="px-3 py-1.5 text-xs border rounded-md hover:bg-accent">
              {{ testing === acct.id ? '테스트 중...' : '접속 테스트' }}
            </button>
            <button @click="openEdit(acct)" class="px-3 py-1.5 text-xs border rounded-md hover:bg-accent">수정</button>
            <button @click="deleteAccount(acct.id)" class="px-3 py-1.5 text-xs border rounded-md hover:bg-destructive/10 text-destructive">삭제</button>
          </div>
        </div>
        <div v-if="testResult && testing === null && testResult !== null" class="mt-3 text-sm">
          <template v-if="testResult.error">
            <p class="text-destructive">{{ testResult.error }}</p>
          </template>
          <template v-else>
            <p :class="testResult.imap?.ok ? 'text-green-600' : 'text-destructive'">
              IMAP: {{ testResult.imap?.message }}
            </p>
            <p :class="testResult.smtp?.ok ? 'text-green-600' : 'text-destructive'">
              SMTP: {{ testResult.smtp?.message }}
            </p>
          </template>
        </div>
      </div>
      <div v-if="accounts.length === 0" class="text-center py-12 text-muted-foreground">
        아직 등록된 메일 계정이 없습니다. 계정을 추가해주세요.
      </div>
    </div>

    <!-- Add/Edit form modal -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showForm = false">
      <div class="bg-background border rounded-lg shadow-lg w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 class="text-lg font-bold mb-4">{{ editing ? '계정 수정' : '메일 계정 추가' }}</h2>

        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium">표시 이름</label>
            <input v-model="form.display_name" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="Gmail 개인" />
          </div>
          <div>
            <label class="text-sm font-medium">이메일 주소</label>
            <input v-model="form.email" type="email" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="user@gmail.com" />
          </div>
          <hr />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm font-medium">IMAP 서버</label>
              <input v-model="form.imap_host" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="imap.gmail.com" />
            </div>
            <div>
              <label class="text-sm font-medium">IMAP 포트</label>
              <input v-model.number="form.imap_port" type="number" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="text-sm font-medium">IMAP 보안</label>
            <select v-model="form.imap_security" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm">
              <option value="ssl">SSL/TLS</option>
              <option value="starttls">STARTTLS</option>
              <option value="none">없음</option>
            </select>
          </div>
          <hr />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-sm font-medium">SMTP 서버</label>
              <input v-model="form.smtp_host" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="smtp.gmail.com" />
            </div>
            <div>
              <label class="text-sm font-medium">SMTP 포트</label>
              <input v-model.number="form.smtp_port" type="number" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
            </div>
          </div>
          <div>
            <label class="text-sm font-medium">SMTP 보안</label>
            <select v-model="form.smtp_security" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm">
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="none">없음</option>
            </select>
          </div>
          <hr />
          <div>
            <label class="text-sm font-medium">로그인 ID</label>
            <input v-model="form.username" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" placeholder="user@gmail.com" />
          </div>
          <div>
            <label class="text-sm font-medium">비밀번호{{ editing ? ' (변경 시에만 입력)' : '' }}</label>
            <input v-model="form.password" type="password" class="w-full mt-1 px-3 py-2 border rounded-md bg-background text-sm" />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_default" type="checkbox" class="rounded" />
            기본 계정으로 설정
          </label>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button @click="showForm = false" class="px-4 py-2 border rounded-md text-sm hover:bg-accent">취소</button>
          <button @click="saveAccount" :disabled="saving" class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90">
            {{ saving ? '저장 중...' : (editing ? '수정' : '추가') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
