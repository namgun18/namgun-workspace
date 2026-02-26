<script setup lang="ts">
const {
  selectedChannel,
  messages,
  loadingMessages,
  hasMoreMessages,
  loadingMore,
  typingUsers,
  showMemberPanel,
  sendMessage,
  sendTyping,
  loadMore,
  openThread,
} = useChat()
</script>

<template>
  <div v-if="selectedChannel" class="flex flex-col h-full">
    <ChatHeader />
    <ChatMessageList
      :messages="messages"
      :loading="loadingMessages"
      :has-more="hasMoreMessages"
      :loading-more="loadingMore"
      @load-more="loadMore"
      @open-thread="openThread"
    />
    <ChatTypingIndicator :typing-users="typingUsers" />
    <ChatInput @send="sendMessage" @typing="sendTyping" />
  </div>

  <!-- Empty state -->
  <div v-else class="flex items-center justify-center h-full text-muted-foreground">
    <div class="text-center">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-12 w-12 mx-auto mb-3 opacity-40" aria-hidden="true">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
      <p class="text-sm">{{ $t('chat.conversation.empty') }}</p>
    </div>
  </div>
</template>
