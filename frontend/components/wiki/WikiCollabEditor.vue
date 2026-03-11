<script setup lang="ts">
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Collaboration from '@tiptap/extension-collaboration'
import * as Y from 'yjs'

const props = defineProps<{
  pageId: string
  initialContent: string
  readonly: boolean
}>()

const emit = defineEmits<{
  save: [content: string]
}>()

const { user } = useAuth()

const editor = ref<Editor | null>(null)
const ydoc = ref<Y.Doc | null>(null)
const ws = ref<WebSocket | null>(null)
const connected = ref(false)
const initialized = ref(false)

function getWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/wiki/collab?page_id=${props.pageId}`
}

function initEditor() {
  cleanup()

  const doc = new Y.Doc()
  ydoc.value = doc

  // Create editor with Yjs collaboration
  editor.value = new Editor({
    editable: !props.readonly,
    extensions: [
      StarterKit.configure({
        history: false, // Yjs handles undo/redo
      }),
      Underline,
      Link.configure({ openOnClick: false }),
      Collaboration.configure({
        document: doc,
      }),
    ],
    content: props.initialContent || '',
  })

  // Connect WebSocket for real-time sync
  connectWs(doc)
}

function connectWs(doc: Y.Doc) {
  const socket = new WebSocket(getWsUrl())
  socket.binaryType = 'arraybuffer'
  ws.value = socket

  socket.onopen = () => {
    connected.value = true
  }

  socket.onclose = () => {
    connected.value = false
    // Reconnect after 3s
    setTimeout(() => {
      if (ydoc.value && !ydoc.value.isDestroyed) {
        connectWs(doc)
      }
    }, 3000)
  }

  socket.onmessage = (event) => {
    try {
      const data = new Uint8Array(event.data)
      Y.applyUpdate(doc, data, 'remote')
    } catch (e) {
      console.debug('Yjs apply error:', e)
    }
  }

  // Broadcast local updates to peers
  const updateHandler = (update: Uint8Array, origin: any) => {
    if (origin !== 'remote' && socket.readyState === WebSocket.OPEN) {
      socket.send(update)
    }
  }
  doc.on('update', updateHandler)
}

function cleanup() {
  editor.value?.destroy()
  editor.value = null
  ws.value?.close()
  ws.value = null
  ydoc.value?.destroy()
  ydoc.value = null
  connected.value = false
}

function getContent(): string {
  return editor.value?.getHTML() || ''
}

function save() {
  emit('save', getContent())
}

defineExpose({ getContent, save })

onMounted(() => {
  initEditor()
})

onUnmounted(() => {
  cleanup()
})

watch(() => props.pageId, () => {
  initEditor()
})

watch(() => props.readonly, (val) => {
  editor.value?.setEditable(!val)
})
</script>

<template>
  <div class="wiki-collab-editor flex flex-col h-full">
    <!-- Toolbar -->
    <div v-if="editor && !readonly" class="flex items-center gap-1 px-3 py-1.5 border-b bg-muted/30 flex-wrap shrink-0">
      <button
        @click="editor!.chain().focus().toggleBold().run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold transition-colors"
        :class="editor.isActive('bold') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >B</button>
      <button
        @click="editor!.chain().focus().toggleItalic().run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold italic transition-colors"
        :class="editor.isActive('italic') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >I</button>
      <button
        @click="editor!.chain().focus().toggleUnderline().run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold underline transition-colors"
        :class="editor.isActive('underline') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >U</button>
      <button
        @click="editor!.chain().focus().toggleStrike().run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold line-through transition-colors"
        :class="editor.isActive('strike') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >S</button>
      <button
        @click="editor!.chain().focus().toggleCode().run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs transition-colors"
        :class="editor.isActive('code') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >&lt;/&gt;</button>

      <div class="w-px h-5 bg-border mx-1" />

      <button
        v-for="level in [1, 2, 3]" :key="level"
        @click="editor!.chain().focus().toggleHeading({ level: level as any }).run()"
        class="w-7 h-7 rounded flex items-center justify-center text-xs font-bold transition-colors"
        :class="editor.isActive('heading', { level }) ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >H{{ level }}</button>

      <div class="w-px h-5 bg-border mx-1" />

      <button
        @click="editor!.chain().focus().toggleBulletList().run()"
        class="w-7 h-7 rounded flex items-center justify-center transition-colors"
        :class="editor.isActive('bulletList') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      </button>
      <button
        @click="editor!.chain().focus().toggleOrderedList().run()"
        class="w-7 h-7 rounded flex items-center justify-center transition-colors"
        :class="editor.isActive('orderedList') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>
      </button>
      <button
        @click="editor!.chain().focus().toggleBlockquote().run()"
        class="w-7 h-7 rounded flex items-center justify-center transition-colors"
        :class="editor.isActive('blockquote') ? 'bg-primary text-primary-foreground' : 'hover:bg-accent text-muted-foreground'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V21z"/></svg>
      </button>
      <button
        @click="editor!.chain().focus().setHorizontalRule().run()"
        class="w-7 h-7 rounded flex items-center justify-center hover:bg-accent text-muted-foreground transition-colors"
      >―</button>

      <div class="flex-1" />

      <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <div class="w-2 h-2 rounded-full" :class="connected ? 'bg-green-500' : 'bg-red-500'" />
        {{ connected ? $t('wiki.connected') : $t('wiki.disconnected') }}
      </div>
    </div>

    <!-- Editor -->
    <div class="flex-1 overflow-auto">
      <EditorContent
        v-if="editor"
        :editor="editor"
        class="prose prose-sm dark:prose-invert max-w-none px-6 py-4 min-h-full"
      />
    </div>
  </div>
</template>

<style>
.wiki-collab-editor .ProseMirror {
  min-height: 100%;
  outline: none;
}
.wiki-collab-editor .ProseMirror p.is-editor-empty:first-child::before {
  content: "내용을 입력하세요...";
  float: left;
  color: #9ca3af;
  pointer-events: none;
  height: 0;
}
</style>
