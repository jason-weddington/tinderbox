<script lang="ts">
  // The example feature's one screen: pick a folder, watch the scan's
  // progress, read the summary. Replace it with your own screens; the
  // patterns to keep are in docs/tauri-design-notes.md.
  import { onMount } from 'svelte';

  import { appInfo, errorText, onScanProgress, pickFolder, scanFolder, underTauri } from './lib/bridge';
  import { formatBytes, plural } from './lib/format';
  import SummaryList from './lib/SummaryList.svelte';
  import type { ScanProgress, ScanSummary } from './lib/types';

  type View =
    | { kind: 'idle' }
    | { kind: 'scanning'; root: string; progress: ScanProgress | null }
    | { kind: 'done'; summary: ScanSummary }
    | { kind: 'failed'; message: string };

  // Tauri starts a window drag only from an element carrying data-tauri-drag-region
  // (or a "deep" ancestor), so the attributes exist only in the Tauri build.
  const tauri = underTauri();

  let view = $state<View>({ kind: 'idle' });
  let version = $state('');

  // The root component lives as long as the window, so the subscription is
  // never undone. A component that can unmount returns the unlisten instead.
  onMount(() => {
    void onScanProgress((progress) => {
      if (view.kind === 'scanning') view = { ...view, progress };
    });
    // The footer stays empty when the version cannot be read; nothing else depends on it.
    appInfo().then(
      (info) => {
        version = info.version;
      },
      () => undefined,
    );
  });

  async function choose(): Promise<void> {
    const root = await pickFolder();
    if (root === null) return;
    view = { kind: 'scanning', root, progress: null };
    try {
      view = { kind: 'done', summary: await scanFolder(root) };
    } catch (e) {
      view = { kind: 'failed', message: errorText(e) };
    }
  }
</script>

{#if tauri}<div class="titlebar" data-tauri-drag-region="" aria-hidden="true"></div>{/if}
<div class="window">
  <header class="band" data-tauri-drag-region={tauri ? 'deep' : undefined}>
    <h1>Folder summary</h1>
    <button type="button" class="primary" onclick={choose} disabled={view.kind === 'scanning'}>
      {view.kind === 'idle' ? 'Choose folder…' : 'Choose another folder…'}
    </button>
  </header>

  <main>
    <p class="status" aria-live="polite">
      {#if view.kind === 'idle'}
        Choose a folder to see what is in it, by file type.
      {:else if view.kind === 'scanning'}
        {#if view.progress === null}
          Scanning {view.root}…
        {:else}
          Scanning {view.root}: {plural(view.progress.files, 'file', 'files')}, {formatBytes(view.progress.bytes)} so
          far…
        {/if}
      {:else if view.kind === 'done'}
        {plural(view.summary.files, 'file', 'files')}, {formatBytes(view.summary.totalBytes)}, in {view.summary.root}.
      {:else}
        <span class="error" role="alert">{view.message}</span>
      {/if}
    </p>
    {#if view.kind === 'done'}
      {#if view.summary.unreadableFolders > 0}
        <p class="notice">
          {plural(view.summary.unreadableFolders, 'folder', 'folders')} could not be read, so the totals leave them out.
        </p>
      {/if}
      <SummaryList summary={view.summary} />
    {/if}
  </main>

  {#if version !== ''}
    <footer>Version {version}</footer>
  {/if}
</div>

<style>
  /* A transparent strip across the very top, above everything, so a press at the
     window's edge drags it whatever view is showing. Shorter than the band's
     controls start, so it never covers one. */
  .titlebar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 0.5rem;
    z-index: 10;
  }
</style>
