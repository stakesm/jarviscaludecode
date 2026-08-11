<script lang="ts">
    import { onMount, onDestroy } from "svelte"
    import { invoke } from "@tauri-apps/api/core"

    import SearchBar from "@/components/elements/SearchBar.svelte"
    import ArcReactor from "@/components/elements/ArcReactor.svelte"
    import HDivider from "@/components/elements/HDivider.svelte"
    import Stats from "@/components/elements/Stats.svelte"
    import Footer from "@/components/Footer.svelte"
    
    import {
        isJarvisRunning,
        updateJarvisStats,
        enableIpc,
        disableIpc,
        translate,
        translations,
        jarvisState,
        isSpeaking,
        lastRecognizedText,
        lastAiReply,
        ipcConnected
    } from "@/stores"

    $: t = (key: string) => translate($translations, key)

    let processRunning = false
    let launching = false
    let wasRunning = false  // track previous state

    // HUD status readout under the hologram
    $: statusLabel = !$ipcConnected
        ? t('status-disconnected')
        : $isSpeaking
            ? t('status-speaking')
            : {
                idle: t('status-standby'),
                listening: t('status-listening'),
                processing: t('status-processing'),
                disconnected: t('status-disconnected')
            }[$jarvisState] || t('status-standby')

    isJarvisRunning.subscribe((value) => {
        processRunning = value
        if (value) {
            enableIpc()
            wasRunning = true
        } else if (wasRunning) {
            // only disable if it was running before
            disableIpc()
            wasRunning = false
        }
    })

    onMount(() => {
        updateJarvisStats()
    })

    onDestroy(() => {
        disableIpc()
    })

    async function runAssistant() {
        launching = true
        try {
            await invoke("run_jarvis_app")
            setTimeout(async () => {
                await updateJarvisStats()
                launching = false
            }, 2500)
        } catch (err) {
            console.error("Failed to run jarvis-app:", err)
            launching = false
        }
    }
</script>

<div class="app-container assist-page">
    <span class="hud-corner tl" aria-hidden="true"></span>
    <span class="hud-corner tr" aria-hidden="true"></span>
    <span class="hud-corner bl" aria-hidden="true"></span>
    <span class="hud-corner br" aria-hidden="true"></span>

    <div class="search search-section">
        <HDivider />
        <SearchBar />
    </div>

    <div class="reactor-section">
        <div class="reactor-wrapper" class:dimmed={!processRunning}>
            <ArcReactor />
        </div>

        {#if processRunning}
            <div class="hud-readout">
                <span class="hud-status" class:speaking={$isSpeaking} class:live={$jarvisState === 'listening' || $jarvisState === 'processing'}>
                    <i class="hud-dot"></i>{statusLabel}
                </span>
                {#if $lastRecognizedText}
                    <span class="hud-transcript">&raquo; &laquo;{$lastRecognizedText}&raquo;</span>
                {/if}
                {#if $lastAiReply}
                    <span class="hud-ai-reply">&#10022; {$lastAiReply}</span>
                {/if}
            </div>
        {/if}

        {#if !processRunning}
            <div class="offline-badge">
                <span class="offline-icon">⚠</span>
                <span class="offline-text">{t('assistant-not-running')}</span>
                <small>{t('assistant-offline-hint')}</small>
            </div>
            <button 
                class="start-button" 
                on:click={runAssistant}
                disabled={launching}
            >
                {launching ? t('btn-starting') : t('btn-start')}
            </button>
        {/if}
    </div>

    <HDivider noMargin />
    <Stats />
    <Footer />
</div>