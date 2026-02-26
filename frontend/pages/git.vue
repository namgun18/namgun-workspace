<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('nav.git')} | ${appName.value}`) })

const {
  currentView,
  fetchRepos,
  resetToRepoList,
} = useGit()

const showCreateIssue = ref(false)

onMounted(async () => {
  resetToRepoList()
  await fetchRepos()
})
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <div class="flex-1 flex flex-col min-w-0 min-h-0">
      <!-- Command bar -->
      <GitCommandBar />

      <!-- Content -->
      <GitRepoList v-if="currentView === 'repo-list'" />
      <GitRepoDetail v-else-if="currentView === 'repo-detail'" />
      <GitFileViewer v-else-if="currentView === 'file-view'" />
      <GitCommitList v-else-if="currentView === 'commit-list'" />
      <GitIssueList v-else-if="currentView === 'issue-list'" @create-issue="showCreateIssue = true" />
      <GitIssueDetail v-else-if="currentView === 'issue-detail'" />
      <GitPullList v-else-if="currentView === 'pull-list'" />
      <GitPullDetail v-else-if="currentView === 'pull-detail'" />
    </div>

    <!-- Create issue modal -->
    <GitCreateIssueModal
      v-if="showCreateIssue"
      @close="showCreateIssue = false"
    />
  </div>
</template>
