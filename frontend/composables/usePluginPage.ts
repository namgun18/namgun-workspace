/**
 * Dynamic plugin page component loader.
 * Discovers plugin page.vue files via import.meta.glob and provides
 * an async component for rendering in /p/[id].vue.
 */

import { defineAsyncComponent, type Component } from 'vue'

// Glob all plugin page components at build time
const pluginPages = import.meta.glob<{ default: Component }>(
  '../../plugins/*/frontend/page.vue',
)

// Build plugin ID → loader map from file paths
// Path format: ../../plugins/{pluginId}/frontend/page.vue
const pluginMap: Record<string, () => Promise<{ default: Component }>> = {}
for (const [path, loader] of Object.entries(pluginPages)) {
  const match = path.match(/plugins\/([^/]+)\/frontend\/page\.vue$/)
  if (match) {
    // sample-notes → notes (strip "sample-" prefix if present, or use folder name as-is)
    const folderId = match[1]
    pluginMap[folderId] = loader

    // Also register without "sample-" prefix for convenience
    if (folderId.startsWith('sample-')) {
      pluginMap[folderId.replace('sample-', '')] = loader
    }
  }
}

export function usePluginPage(pluginId: string): Component | null {
  const loader = pluginMap[pluginId]
  if (!loader) return null

  return defineAsyncComponent({
    loader,
    loadingComponent: {
      template: '<div class="flex items-center justify-center py-20 text-muted-foreground"><span class="text-sm">Loading plugin...</span></div>',
    },
    errorComponent: {
      template: '<div class="flex items-center justify-center py-20 text-destructive"><span class="text-sm">Failed to load plugin</span></div>',
    },
  })
}

export function getAvailablePluginIds(): string[] {
  return Object.keys(pluginMap)
}
