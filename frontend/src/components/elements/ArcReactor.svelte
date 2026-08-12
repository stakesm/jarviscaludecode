<script lang="ts">
    import { onMount, onDestroy } from "svelte"
    import { jarvisState, isSpeaking } from "@/stores"

    // A dense holographic sphere made of many tilted, spinning light rings -
    // rendered on <canvas> because this many overlapping glowing strokes
    // would be far too heavy (and far less convincing) as DOM/CSS elements.

    let canvasEl: HTMLCanvasElement
    let wrapperEl: HTMLDivElement
    let rafId = 0
    let dpr = 1

    let speaking = false
    isSpeaking.subscribe((v) => (speaking = v))

    $: baseState = {
        disconnected: "disconnected",
        idle: "idle",
        listening: "active",
        processing: "active",
    }[$jarvisState] || "disconnected"

    // "speaking" takes over visually the moment a voice reply starts playing
    $: state = speaking && baseState !== "disconnected" ? "speaking" : baseState

    // per-state animation tuning - read live by the render loop via `state` above
    const STATE_PARAMS: Record<string, { speed: number; glow: number; jitter: number; dim: number }> = {
        disconnected: { speed: 0.15, glow: 0.35, jitter: 0, dim: 0.35 },
        idle:         { speed: 0.45, glow: 0.75, jitter: 0.06, dim: 0.85 },
        active:       { speed: 1.0,  glow: 1.15, jitter: 0.16, dim: 1 },
        speaking:     { speed: 1.65, glow: 1.45, jitter: 0.34, dim: 1 },
    }

    // ---- 3D point helpers (simple, no library - just rotation matrices) ----
    type Vec3 = { x: number; y: number; z: number }

    function rotateX(p: Vec3, a: number): Vec3 {
        const c = Math.cos(a), s = Math.sin(a)
        return { x: p.x, y: p.y * c - p.z * s, z: p.y * s + p.z * c }
    }
    function rotateY(p: Vec3, a: number): Vec3 {
        const c = Math.cos(a), s = Math.sin(a)
        return { x: p.x * c + p.z * s, y: p.y, z: -p.x * s + p.z * c }
    }
    function rotateZ(p: Vec3, a: number): Vec3 {
        const c = Math.cos(a), s = Math.sin(a)
        return { x: p.x * c - p.y * s, y: p.x * s + p.y * c, z: p.z }
    }

    // ---- ring definitions (generated once, animated forever) ----
    interface Ring {
        radius: number
        tiltX: number
        tiltZ: number
        spin: number      // signed speed multiplier, own direction/pace
        phase: number      // current accumulated rotation
        hue: number         // 32 (deep orange) .. 48 (warm gold)
        alpha: number
        width: number
        points: number
        depthSample: number  // updated each frame for depth-based shading
    }

    const RING_COUNT = 46
    let rings: Ring[] = []

    function makeRings(): Ring[] {
        const out: Ring[] = []
        for (let i = 0; i < RING_COUNT; i++) {
            // deterministic-ish but varied spread via index-based pseudo-random
            const r1 = ((i * 2654435761) % 1000) / 1000
            const r2 = ((i * 40503 + 17) % 1000) / 1000
            const r3 = ((i * 977 + 331) % 1000) / 1000
            const r4 = ((i * 613 + 91) % 1000) / 1000

            out.push({
                radius: 60 + r1 * 92,
                tiltX: r2 * Math.PI,
                tiltZ: r3 * Math.PI,
                spin: (0.25 + r4 * 0.9) * (i % 2 === 0 ? 1 : -1),
                phase: r1 * Math.PI * 2,
                hue: 30 + r2 * 20,
                alpha: 0.1 + r3 * 0.22,
                width: 1 + (r4 > 0.82 ? 1 : 0),
                points: 40,
                depthSample: 0.6,
            })
        }
        return out
    }

    function draw(ctx: CanvasRenderingContext2D, w: number, h: number, dt: number, t: number) {
        const p = STATE_PARAMS[state] ?? STATE_PARAMS.idle
        const cx = w / 2
        const cy = h / 2
        const scale = Math.min(w, h) / 300

        // trailing fade instead of a hard clear - leaves faint light trails,
        // reinforcing the "spinning energy" read from the reference image
        ctx.fillStyle = "rgba(6, 4, 3, 0.32)"
        ctx.globalCompositeOperation = "source-over"
        ctx.fillRect(0, 0, w, h)

        ctx.globalCompositeOperation = "lighter"

        for (const ring of rings) {
            ring.phase += dt * ring.spin * p.speed

            // occasional per-ring jitter at higher energy states - a stand-in
            // for audio reactivity without needing real waveform data
            const wobble = p.jitter > 0
                ? 1 + Math.sin(t * 3.7 + ring.hue) * p.jitter * 0.5
                : 1

            ctx.beginPath()
            for (let i = 0; i <= ring.points; i++) {
                const a = (i / ring.points) * Math.PI * 2
                let pt: Vec3 = { x: Math.cos(a) * ring.radius * wobble, y: Math.sin(a) * ring.radius * wobble, z: 0 }
                pt = rotateX(pt, ring.tiltX)
                pt = rotateZ(pt, ring.tiltZ)
                pt = rotateY(pt, ring.phase)

                // faux depth: nearer points slightly larger/brighter
                const depth = (pt.z + ring.radius) / (ring.radius * 2)
                const px = cx + pt.x * scale
                const py = cy + pt.y * scale * 0.94

                if (i === 0) ctx.moveTo(px, py)
                else ctx.lineTo(px, py)

                if (i === Math.floor(ring.points * 0.3)) {
                    // stash a depth sample for stroke styling below
                    ring.depthSample = depth
                }
            }

            const depth = ring.depthSample
            const alpha = ring.alpha * p.glow * p.dim * (0.55 + depth * 0.65)
            ctx.strokeStyle = `hsla(${ring.hue}, 95%, ${55 + depth * 25}%, ${Math.min(alpha, 0.95)})`
            ctx.lineWidth = ring.width * (0.7 + depth * 0.6)
            ctx.stroke()
        }

        // bright core glow at the centre, like the reference's hot centre
        const coreR = 34 * scale * (0.85 + (Math.sin(t * 2.4) * 0.5 + 0.5) * 0.15) * p.glow
        const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR)
        core.addColorStop(0, `rgba(255, 236, 190, ${0.9 * p.dim})`)
        core.addColorStop(0.4, `rgba(255, 176, 60, ${0.45 * p.dim})`)
        core.addColorStop(1, "rgba(255, 140, 20, 0)")
        ctx.fillStyle = core
        ctx.beginPath()
        ctx.arc(cx, cy, coreR, 0, Math.PI * 2)
        ctx.fill()

        ctx.globalCompositeOperation = "source-over"
    }

    function resize() {
        if (!canvasEl || !wrapperEl) return
        dpr = Math.min(window.devicePixelRatio || 1, 2)
        const size = wrapperEl.clientWidth || 300
        canvasEl.width = size * dpr
        canvasEl.height = size * dpr
        canvasEl.style.width = size + "px"
        canvasEl.style.height = size + "px"
        const ctx = canvasEl.getContext("2d")
        ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    onMount(() => {
        rings = makeRings()
        resize()

        const ctx = canvasEl.getContext("2d")
        if (!ctx) return

        const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
        let last = performance.now()
        let elapsed = 0

        const loop = (now: number) => {
            const dt = Math.min((now - last) / 1000, 0.05)
            last = now
            elapsed += dt

            const size = canvasEl.width / dpr
            draw(ctx, size, size, reduceMotion ? dt * 0.15 : dt, elapsed)

            rafId = requestAnimationFrame(loop)
        }
        rafId = requestAnimationFrame(loop)

        window.addEventListener("resize", resize)
    })

    onDestroy(() => {
        if (rafId) cancelAnimationFrame(rafId)
        if (typeof window !== "undefined") window.removeEventListener("resize", resize)
    })
</script>

<div class="hologram {state}" bind:this={wrapperEl}>
    <canvas bind:this={canvasEl} aria-hidden="true"></canvas>
</div>

<style lang="scss">
    .hologram {
        position: relative;
        width: 300px;
        height: 300px;
        margin: auto;
        border-radius: 50%;
        transition: transform 0.6s ease, opacity 0.6s ease, filter 0.6s ease;
        transform: scale(0.95);
        opacity: 0.9;

        canvas {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            border-radius: 50%;
        }

        // ambient bleed into the surrounding page, echoing the core colour
        &::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 900px;
            height: 900px;
            border-radius: 50%;
            background: radial-gradient(
                circle,
                rgba(255, 160, 60, 0.16) 0%,
                rgba(255, 140, 40, 0.09) 30%,
                rgba(255, 120, 30, 0.04) 45%,
                transparent 68%
            );
            z-index: -1;
            pointer-events: none;
            transition: opacity 0.6s ease, transform 0.6s ease;
        }

        &.disconnected {
            transform: scale(0.85);
            opacity: 0.4;
            filter: grayscale(0.55) brightness(0.65);

            &::before { opacity: 0.35; transform: translate(-50%, -50%) scale(0.7); }
        }

        &.idle {
            transform: scale(0.95);
            opacity: 0.92;

            &::before { opacity: 0.75; transform: translate(-50%, -50%) scale(0.85); }
        }

        &.active {
            transform: scale(1.04);
            opacity: 1;

            &::before {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1.05);
                animation: hologram-pulse 3s ease-in-out infinite;
            }
        }

        &.speaking {
            transform: scale(1.08);
            opacity: 1;

            &::before {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1.15);
                animation: hologram-pulse 1s ease-in-out infinite;
            }
        }
    }

    @keyframes hologram-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.82; }
    }

    @media (prefers-reduced-motion: reduce) {
        .hologram { transition: none; }
    }
</style>
