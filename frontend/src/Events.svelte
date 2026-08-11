<script lang="ts">
    import { onMount } from "svelte"
    import { listen } from "@tauri-apps/api/event"
    import { invoke } from "@tauri-apps/api/core"
    import { assistantVoice, isSpeaking } from "@/stores"

    let voiceVal = "jarvis-og"
    assistantVoice.subscribe(value => {
        voiceVal = value || "jarvis-og"
    })

    onMount(async () => {
        // audio playback event - drives the hologram "speaking" animation for the duration of playback
        await listen<{ data: string }>("audio-play", async (event) => {
            const voice = voiceVal || "jarvis-remake"
            const filename = `sound/${voice}/${event.payload.data}.wav`

            isSpeaking.set(true)
            try {
                await invoke("play_sound", { filename, sleep: true })
            } catch (err) {
                console.error("failed to play sound:", err)
            } finally {
                isSpeaking.set(false)
            }
        })

        // assistant state events
        await listen("assistant-greet", () => {
            document.getElementById("arc-reactor")?.classList.add("active")
        })

        await listen("assistant-waiting", () => {
            document.getElementById("arc-reactor")?.classList.remove("active")
        })
    })
</script>
