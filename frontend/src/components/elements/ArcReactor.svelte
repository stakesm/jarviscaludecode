<script lang="ts">
    import { jarvisState, isSpeaking } from "@/stores"

    // ring of voice-reactive bars around the core - deterministic pseudo-random
    // seeds so every bar pulses slightly out of phase with its neighbours
    const barCount = 40
    const barSeeds = Array.from({ length: barCount }, (_, i) => ((i * 137) % barCount) / barCount)

    let speaking = false
    isSpeaking.subscribe((v) => (speaking = v))

    $: baseState = {
        'disconnected': 'disconnected',
        'idle': 'idle',
        'listening': 'active',
        'processing': 'active'
    }[$jarvisState] || 'disconnected'

    // "speaking" takes over visually as soon as a voice reply starts playing
    $: stateClass = speaking && baseState !== 'disconnected' ? 'speaking' : baseState
</script>

<div id="arc-reactor" class="reactor-container {stateClass} arc-white">
    <div class="voice-bars" aria-hidden="true">
        {#each barSeeds as seed, i}
            <span class="voice-bar" style="--i:{i}; --n:{barCount}; --seed:{seed};"></span>
        {/each}
    </div>

    <div class="reactor-container-inner circle abs-center">
        <ul class="marks">
            {#each Array(60) as _, i}
                <li></li>
            {/each}
        </ul>
        <div class="e7">
            <div class="semi_arc_3 e5_1">
                <div class="semi_arc_3 e5_1_ghost"></div>
                <div class="semi_arc_3 e5_2">
                    <div class="semi_arc_3 e5_2_ghost"></div>
                    <div class="semi_arc_3 e5_3">
                        <div class="semi_arc_3 e5_3_ghost"></div>
                        <div class="semi_arc_3 e5_4">
                            <div class="semi_arc_3 e5_4_ghost"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="tunnel circle abs-center"></div>
    <div class="scan-sweep circle abs-center"></div>
    <div class="core-wrapper circle abs-center"></div>
    <div class="core-outer circle abs-center"></div>
    <div class="core-inner circle abs-center"></div>
    <div class="coil-container">
        {#each Array(8) as _, i}
            <div class="coil coil-{i + 1}"></div>
        {/each}
    </div>
</div>

<style lang="scss" global>
    // [ ARC REACTOR VARIABLES ]
    $arc-radius: 133px;
    $bar-radius: 152px;
    $arc-container-size: 195%;
    $arc-spacing: 93%;

    // arc thickness per level
    $arc-thickness-1: 1px;
    $arc-thickness-2: 2px;
    $arc-thickness-3: 3px;
    $arc-thickness-4: 4px;

    // marks (lines) settings
    $mark-width: 2.5px;
    $mark-height: 11px;

    // helper: keeps a bar's angular position while only the amplitude (scaleY) changes
    @mixin bar-transform($scale) {
        transform: rotate(calc(var(--i) * (360deg / var(--n)))) translateY(-#{$bar-radius}) scaleY(#{$scale});
    }

    // [ DEFAULT THEME - CYAN ]
    .reactor-container {
        --arc-color: 2, 254, 255;           // RGB values for easy rgba()
        --arc-glow: #52fefe;
        --arc-glow-rgb: 82, 254, 254;
        --arc-core-border: #1b4e5f;
        --arc-core-bg: #073c4b;

        width: 300px;
        height: 300px;
        margin: auto;
        position: relative;
        border-radius: 50%;
        transition: transform 0.5s ease, opacity 0.5s ease, filter 0.5s ease;
        transform: scale(0.95);
        opacity: 0.9;
        top: 10px;

        ul {
            list-style: none;
            margin: 0;
            padding: 0;
        }
    }

    // [ HOLOGRAM FLICKER ]
    // a rare, quick brightness glitch so the core reads as a projected hologram
    .reactor-container::after {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: rgba(var(--arc-color), 1);
        opacity: 0;
        mix-blend-mode: overlay;
        pointer-events: none;
        animation: holo-flicker 7s infinite steps(1);
    }

    @keyframes holo-flicker {
        0%, 91%, 93%, 96.4%, 100% { opacity: 0; }
        91.5% { opacity: 0.14; }
        92.5% { opacity: 0.03; }
        95.5% { opacity: 0.2; }
        96% { opacity: 0; }
    }

    // [ COLOR THEMES ]
    .reactor-container.arc-cyan {
        --arc-color: 2, 254, 255;
        --arc-glow: #52fefe;
        --arc-glow-rgb: 82, 254, 254;
        --arc-core-border: #1b4e5f;
        --arc-core-bg: #073c4b;
    }

    .reactor-container.arc-red {
        --arc-color: 255, 50, 50;
        --arc-glow: #ff5050;
        --arc-glow-rgb: 255, 80, 80;
        --arc-core-border: #5f1b1b;
        --arc-core-bg: #4b0707;
    }

    .reactor-container.arc-orange {
        --arc-color: 255, 150, 50;
        --arc-glow: #ff9632;
        --arc-glow-rgb: 255, 150, 50;
        --arc-core-border: #5f3c1b;
        --arc-core-bg: #4b2a07;
    }

    .reactor-container.arc-yellow {
        --arc-color: 255, 230, 50;
        --arc-glow: #ffe632;
        --arc-glow-rgb: 255, 230, 50;
        --arc-core-border: #5f5a1b;
        --arc-core-bg: #4b4507;
    }

    .reactor-container.arc-green {
        --arc-color: 50, 255, 100;
        --arc-glow: #32ff64;
        --arc-glow-rgb: 50, 255, 100;
        --arc-core-border: #1b5f2a;
        --arc-core-bg: #074b15;
    }

    .reactor-container.arc-blue {
        --arc-color: 50, 150, 255;
        --arc-glow: #3296ff;
        --arc-glow-rgb: 50, 150, 255;
        --arc-core-border: #1b3c5f;
        --arc-core-bg: #072a4b;
    }

    .reactor-container.arc-purple {
        --arc-color: 180, 100, 255;
        --arc-glow: #b464ff;
        --arc-glow-rgb: 180, 100, 255;
        --arc-core-border: #3c1b5f;
        --arc-core-bg: #28074b;
    }

    .reactor-container.arc-pink {
        --arc-color: 255, 100, 200;
        --arc-glow: #ff64c8;
        --arc-glow-rgb: 255, 100, 200;
        --arc-core-border: #5f1b4a;
        --arc-core-bg: #4b0735;
    }

    .reactor-container.arc-white {
        --arc-color: 255, 255, 255;
        --arc-glow: #ffffff;
        --arc-core-border: #4a4a4a;
        --arc-core-bg: #2a2a2a;
    }

    // [ BACKGROUND GLOW ]
    .reactor-container::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 1000px;
        height: 1000px;
        border-radius: 50%;
        background: radial-gradient(
            circle,
            rgba(var(--arc-color), 0.20) 0%,
            rgba(var(--arc-color), 0.15) 30%,
            rgba(var(--arc-color), 0.10) 40%,
            rgba(var(--arc-color), 0.04) 50%,
            transparent 70%
        );
        z-index: -1;
        pointer-events: none;
        transition: opacity 0.5s ease, transform 0.5s ease;
    }

    // [ CORE ELEMENTS - using CSS vars ]
    .reactor-container-inner {
        height: 238px;
        width: 238px;
        background-color: #161a1b;
        box-shadow: 0px 0px 50px 15px rgba(var(--arc-color), 0.3),
                    inset 0px 0px 50px 15px rgba(var(--arc-color), 0.3);
        transition: box-shadow 0.5s ease;
    }

    .circle { border-radius: 50%; }

    .abs-center {
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        margin: auto;
    }

    .core-inner {
        width: 70px;
        height: 70px;
        border: 5px solid var(--arc-core-border);
        background-color: #ffffff;
        box-shadow: 0px 0px 7px 5px var(--arc-glow),
                    0px 0px 10px 10px var(--arc-glow) inset;
        transition: box-shadow 0.5s ease;
    }

    .core-outer {
        width: 120px;
        height: 120px;
        border: 1px solid var(--arc-glow);
        background-color: #ffffff;
        box-shadow: 0px 0px 2px 1px var(--arc-glow),
                    0px 0px 10px 5px var(--arc-glow) inset;
        transition: box-shadow 0.5s ease;
    }

    .core-wrapper {
        width: 180px;
        height: 180px;
        background-color: var(--arc-core-bg);
        box-shadow: 0px 0px 5px 4px var(--arc-glow),
                    0px 0px 6px 2px var(--arc-glow) inset;
        transition: box-shadow 0.5s ease;
    }

    .tunnel {
        width: 220px;
        height: 220px;
        background-color: #ffffff;
        box-shadow: 0px 0px 5px 1px var(--arc-glow),
                    0px 0px 5px 4px var(--arc-glow) inset;
        transition: box-shadow 0.5s ease;
    }

    // [ SCANNING SWEEP - a thin light band crossing the core, hologram-projector style ]
    .scan-sweep {
        width: 220px;
        height: 220px;
        overflow: hidden;
        pointer-events: none;
        mix-blend-mode: screen;
        opacity: 0.45;
        z-index: 2;

        &::before {
            content: '';
            position: absolute;
            left: -10%;
            top: -30px;
            width: 120%;
            height: 30px;
            background: linear-gradient(to bottom, transparent, rgba(var(--arc-color), 0.9), transparent);
            filter: blur(1px);
            animation: scan-move 3.4s linear infinite;
        }
    }

    @keyframes scan-move {
        0% { top: -30px; }
        100% { top: 250px; }
    }

    // [ VOICE BARS - radial ring that pulses with listening / processing / speaking ]
    .voice-bars {
        position: absolute;
        inset: 0;
        z-index: 3;
        pointer-events: none;
    }

    .voice-bar {
        position: absolute;
        left: 50%;
        top: 50%;
        width: 3px;
        height: 12px;
        margin-left: -1.5px;
        margin-top: -6px;
        border-radius: 2px;
        background: var(--arc-glow);
        opacity: 0;
        box-shadow: 0 0 4px rgba(var(--arc-color), 0.8);
        @include bar-transform(1);
        transition: opacity 0.6s ease;
    }

    .coil-container {
        position: relative;
        width: 100%;
        height: 100%;
        animation: reactor-anim 10s infinite linear;
    }

    .coil {
        position: absolute;
        width: 30px;
        height: 20px;
        top: calc(50% - 110px);
        left: calc(50% - 15px);
        transform-origin: 15px 110px;
        background-color: var(--arc-core-bg);
        box-shadow: 0px 0px 5px var(--arc-glow) inset;
    }

    @for $i from 1 through 8 {
        .coil-#{$i} {
            transform: rotate(#{($i - 1) * 45}deg);
        }
    }

    @keyframes reactor-anim {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .e7 {
        position: absolute;
        z-index: 1;
        width: $arc-container-size;
        height: $arc-container-size;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        border: 6px solid transparent;
        background: transparent;
        border-radius: 50%;
        transition: opacity 0.5s ease;
        text-align: center;
        opacity: 0.5;
    }

    .semi_arc_3 {
        $offset: calc((100% - #{$arc-spacing}) / 2);

        position: absolute;
        width: $arc-spacing;
        height: $arc-spacing;
        left: $offset;
        top: $offset;
        border-style: solid;
        border-color: transparent;
        border-radius: 50%;
        box-sizing: border-box;
        animation: rotate 6s linear infinite;
        overflow: hidden;
    }

    // [ MAIN ARCS ]
    .e5_1 {
        border-width: $arc-thickness-1;
        border-top-color: rgba(var(--arc-color), 0.25);
        border-right-color: transparent;
        border-bottom-color: transparent;
        border-left-color: rgba(var(--arc-color), 0.25);
        animation: rotate 8s linear infinite;
    }

    .e5_2 {
        border-width: $arc-thickness-2;
        border-top-color: transparent;
        border-right-color: rgba(var(--arc-color), 0.4);
        border-bottom-color: rgba(var(--arc-color), 0.4);
        border-left-color: transparent;
        animation: rotate_anti 6s linear infinite;
    }

    .e5_3 {
        border-width: $arc-thickness-3;
        border-top-color: rgba(var(--arc-color), 0.6);
        border-right-color: transparent;
        border-bottom-color: transparent;
        border-left-color: transparent;
        animation: rotate 4s linear infinite;
    }

    .e5_4 {
        border-width: $arc-thickness-4;
        border-top-color: transparent;
        border-right-color: transparent;
        border-bottom-color: rgba(var(--arc-color), 0.8);
        border-left-color: transparent;
        animation: rotate_anti 5s linear infinite;
    }

    // [ GHOST ARCS ]
    .e5_1_ghost {
        border-width: $arc-thickness-1;
        border-top-color: rgba(var(--arc-color), 0.08);
        border-right-color: rgba(var(--arc-color), 0.08);
        border-bottom-color: transparent;
        border-left-color: transparent;
        animation: rotate_anti 12s linear infinite;
    }

    .e5_2_ghost {
        border-width: $arc-thickness-2;
        border-top-color: rgba(var(--arc-color), 0.12);
        border-right-color: transparent;
        border-bottom-color: transparent;
        border-left-color: rgba(var(--arc-color), 0.12);
        animation: rotate 9s linear infinite;
    }

    .e5_3_ghost {
        border-width: $arc-thickness-3;
        border-top-color: transparent;
        border-right-color: rgba(var(--arc-color), 0.18);
        border-bottom-color: rgba(var(--arc-color), 0.18);
        border-left-color: transparent;
        animation: rotate_anti 6s linear infinite;
    }

    .e5_4_ghost {
        border-width: $arc-thickness-4;
        border-top-color: rgba(var(--arc-color), 0.24);
        border-right-color: transparent;
        border-bottom-color: transparent;
        border-left-color: rgba(var(--arc-color), 0.24);
        animation: rotate 7.5s linear infinite;
    }

    @keyframes rotate {
        0% { transform: rotateZ(0deg); }
        100% { transform: rotateZ(360deg); }
    }

    @keyframes rotate_anti {
        0% { transform: rotateZ(0deg); }
        100% { transform: rotateZ(-360deg); }
    }

    // [ MARKS ]
    .marks {
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
    }

    .marks li {
        width: $mark-width;
        height: $mark-height;
        background: rgba(var(--arc-color), 0.8);
        position: absolute;
        left: 50%;
        top: 50%;
        margin-left: calc(-#{$mark-width} / 2);
        margin-top: calc(-#{$mark-height} / 2);
        animation: colour_ease2 3s infinite ease-in-out;
    }

    @keyframes colour_ease2 {
        0% { background: rgba(var(--arc-color), 1); }
        50% { background: rgba(var(--arc-color), 0.3); }
        100% { background: rgba(var(--arc-color), 1); }
    }

    @for $i from 1 through 60 {
        .marks li:nth-child(#{$i}) {
            transform: rotate(#{$i * 6}deg) translateY(-$arc-radius);
        }
    }

    // [ DISCONNECTED ]
    .reactor-container.disconnected {
        transform: scale(0.85);
        opacity: 0.4;
        filter: grayscale(0.7) brightness(0.6);

        &::after { animation: none; opacity: 0; }

        .coil-container { animation-duration: 20s; }
        .e7 { opacity: 0.3; }
        .scan-sweep { opacity: 0.1; &::before { animation-duration: 9s; } }
        .voice-bar { opacity: 0; }

        .e5_1 {
            border-top-color: rgba(var(--arc-color), 0.1);
            border-left-color: rgba(var(--arc-color), 0.1);
            animation: rotate 35s linear infinite;
        }
        .e5_2 {
            border-right-color: rgba(var(--arc-color), 0.15);
            border-bottom-color: rgba(var(--arc-color), 0.15);
            animation: rotate_anti 30s linear infinite;
        }
        .e5_3 {
            border-top-color: rgba(var(--arc-color), 0.2);
            animation: rotate 25s linear infinite;
        }
        .e5_4 {
            border-bottom-color: rgba(var(--arc-color), 0.25);
            animation: rotate_anti 28s linear infinite;
        }

        .e5_1_ghost {
            border-top-color: rgba(var(--arc-color), 0.03);
            border-right-color: rgba(var(--arc-color), 0.03);
            animation: rotate_anti 50s linear infinite;
        }
        .e5_2_ghost {
            border-top-color: rgba(var(--arc-color), 0.05);
            border-left-color: rgba(var(--arc-color), 0.05);
            animation: rotate 45s linear infinite;
        }
        .e5_3_ghost {
            border-right-color: rgba(var(--arc-color), 0.06);
            border-bottom-color: rgba(var(--arc-color), 0.06);
            animation: rotate_anti 40s linear infinite;
        }
        .e5_4_ghost {
            border-top-color: rgba(var(--arc-color), 0.08);
            border-left-color: rgba(var(--arc-color), 0.08);
            animation: rotate 42s linear infinite;
        }
    }

    .reactor-container.disconnected::before {
        opacity: 0.3;
        transform: translate(-50%, -50%) scale(0.7);
    }

    // [ IDLE ]
    .reactor-container.idle {
        transform: scale(0.95);
        opacity: 0.9;

        .coil-container { animation-duration: 10s; }
        .e7 { opacity: 0.6; }

        .voice-bar {
            opacity: 0.22;
            animation: bar-idle 2.6s ease-in-out infinite;
            animation-delay: calc(var(--seed) * -2.6s);
        }

        .e5_1 {
            border-top-color: rgba(var(--arc-color), 0.2);
            border-left-color: rgba(var(--arc-color), 0.2);
            animation: rotate 9s linear infinite;
        }
        .e5_2 {
            border-right-color: rgba(var(--arc-color), 0.35);
            border-bottom-color: rgba(var(--arc-color), 0.35);
            animation: rotate_anti 15s linear infinite;
        }
        .e5_3 {
            border-top-color: rgba(var(--arc-color), 0.5);
            animation: rotate 12s linear infinite;
        }
        .e5_4 {
            border-bottom-color: rgba(var(--arc-color), 0.65);
            animation: rotate_anti 14s linear infinite;
        }

        .e5_1_ghost {
            border-top-color: rgba(var(--arc-color), 0.06);
            border-right-color: rgba(var(--arc-color), 0.06);
            animation: rotate_anti 14s linear infinite;
        }
        .e5_2_ghost {
            border-top-color: rgba(var(--arc-color), 0.1);
            border-left-color: rgba(var(--arc-color), 0.1);
            animation: rotate 22s linear infinite;
        }
        .e5_3_ghost {
            border-right-color: rgba(var(--arc-color), 0.15);
            border-bottom-color: rgba(var(--arc-color), 0.15);
            animation: rotate_anti 18s linear infinite;
        }
        .e5_4_ghost {
            border-top-color: rgba(var(--arc-color), 0.2);
            border-left-color: rgba(var(--arc-color), 0.2);
            animation: rotate 21s linear infinite;
        }
    }

    .reactor-container.idle::before {
        opacity: 0.7;
        transform: translate(-50%, -50%) scale(0.9);
    }

    @keyframes bar-idle {
        0%, 100% { @include bar-transform(0.9); }
        50% { @include bar-transform(1.25); }
    }

    // [ ACTIVE - listening / processing ]
    .reactor-container.active {
        transform: scale(1.05);
        opacity: 1;

        .coil-container { animation-duration: 3s; }
        .e7 { opacity: 1; }
        .scan-sweep { opacity: 0.65; &::before { animation-duration: 1.3s; } }

        .voice-bar {
            opacity: 0.65;
            animation: bar-active 0.9s ease-in-out infinite;
            animation-delay: calc(var(--seed) * -0.9s);
        }

        .e5_1 {
            border-top-color: rgba(var(--arc-color), 0.3);
            border-left-color: rgba(var(--arc-color), 0.3);
            animation: rotate 4s linear infinite;
        }
        .e5_2 {
            border-right-color: rgba(var(--arc-color), 0.5);
            border-bottom-color: rgba(var(--arc-color), 0.5);
            animation: rotate_anti 3s linear infinite;
        }
        .e5_3 {
            border-top-color: rgba(var(--arc-color), 0.7);
            animation: rotate 2s linear infinite;
        }
        .e5_4 {
            border-bottom-color: rgba(var(--arc-color), 0.9);
            animation: rotate_anti 2.5s linear infinite;
        }

        .e5_1_ghost {
            border-top-color: rgba(var(--arc-color), 0.1);
            border-right-color: rgba(var(--arc-color), 0.1);
            animation: rotate_anti 6s linear infinite;
        }
        .e5_2_ghost {
            border-top-color: rgba(var(--arc-color), 0.15);
            border-left-color: rgba(var(--arc-color), 0.15);
            animation: rotate 4.5s linear infinite;
        }
        .e5_3_ghost {
            border-right-color: rgba(var(--arc-color), 0.2);
            border-bottom-color: rgba(var(--arc-color), 0.2);
            animation: rotate_anti 3s linear infinite;
        }
        .e5_4_ghost {
            border-top-color: rgba(var(--arc-color), 0.28);
            border-left-color: rgba(var(--arc-color), 0.28);
            animation: rotate 3.75s linear infinite;
        }

        .reactor-container-inner {
            box-shadow: 0px 0px 70px 25px rgba(var(--arc-color), 0.3),
                        inset 0px 0px 70px 25px rgba(var(--arc-color), 0.3);
        }

        .core-inner {
            box-shadow: 0px 0px 15px 10px var(--arc-glow),
                        0px 0px 20px 15px var(--arc-glow) inset;
        }

        .core-outer {
            box-shadow: 0px 0px 5px 3px var(--arc-glow),
                        0px 0px 15px 10px var(--arc-glow) inset;
        }

        .core-wrapper {
            box-shadow: 0px 0px 10px 8px var(--arc-glow),
                        0px 0px 10px 5px var(--arc-glow) inset;
        }

        .tunnel {
            box-shadow: 0px 0px 10px 3px var(--arc-glow),
                        0px 0px 10px 8px var(--arc-glow) inset;
        }

        .marks li {
            animation: colour_ease2_active 1s infinite ease-in-out;
        }
    }

    .reactor-container.active::before {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1.1);
        animation: bg-pulse 3s ease-in-out infinite;
    }

    @keyframes bg-pulse {
        0%, 100% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.1);
        }
        50% {
            opacity: 0.85;
            transform: translate(-50%, -50%) scale(1.05);
        }
    }

    @keyframes colour_ease2_active {
        0% { background: rgba(var(--arc-color), 1); box-shadow: 0 0 5px rgba(var(--arc-color), 1); }
        50% { background: rgba(var(--arc-color), 0.3); box-shadow: none; }
        100% { background: rgba(var(--arc-color), 1); box-shadow: 0 0 5px rgba(var(--arc-color), 1); }
    }

    @keyframes bar-active {
        0%, 100% { @include bar-transform(0.8); }
        50% { @include bar-transform(1.9); }
    }

    // [ SPEAKING - a voice reply is currently playing back ]
    // same energy as "active" plus a fast, organic voice-bar wave and a pulsing core
    .reactor-container.speaking {
        transform: scale(1.08);
        opacity: 1;

        .coil-container { animation-duration: 2s; }
        .e7 { opacity: 1; }
        .scan-sweep { opacity: 0.85; &::before { animation-duration: 0.7s; } }

        &::after { animation-duration: 2.4s; }

        .voice-bar {
            opacity: 1;

            &:nth-child(4n+1) { animation: bar-speak-a 0.42s ease-in-out infinite; animation-delay: calc(var(--seed) * -0.42s); }
            &:nth-child(4n+2) { animation: bar-speak-b 0.5s ease-in-out infinite; animation-delay: calc(var(--seed) * -0.5s); }
            &:nth-child(4n+3) { animation: bar-speak-c 0.38s ease-in-out infinite; animation-delay: calc(var(--seed) * -0.38s); }
            &:nth-child(4n) { animation: bar-speak-d 0.46s ease-in-out infinite; animation-delay: calc(var(--seed) * -0.46s); }
        }

        .e5_1 {
            border-top-color: rgba(var(--arc-color), 0.35);
            border-left-color: rgba(var(--arc-color), 0.35);
            animation: rotate 3s linear infinite;
        }
        .e5_2 {
            border-right-color: rgba(var(--arc-color), 0.55);
            border-bottom-color: rgba(var(--arc-color), 0.55);
            animation: rotate_anti 2.2s linear infinite;
        }
        .e5_3 {
            border-top-color: rgba(var(--arc-color), 0.8);
            animation: rotate 1.4s linear infinite;
        }
        .e5_4 {
            border-bottom-color: rgba(var(--arc-color), 1);
            animation: rotate_anti 1.8s linear infinite;
        }

        .e5_1_ghost {
            border-top-color: rgba(var(--arc-color), 0.12);
            border-right-color: rgba(var(--arc-color), 0.12);
            animation: rotate_anti 4.5s linear infinite;
        }
        .e5_2_ghost {
            border-top-color: rgba(var(--arc-color), 0.18);
            border-left-color: rgba(var(--arc-color), 0.18);
            animation: rotate 3.5s linear infinite;
        }
        .e5_3_ghost {
            border-right-color: rgba(var(--arc-color), 0.24);
            border-bottom-color: rgba(var(--arc-color), 0.24);
            animation: rotate_anti 2.4s linear infinite;
        }
        .e5_4_ghost {
            border-top-color: rgba(var(--arc-color), 0.32);
            border-left-color: rgba(var(--arc-color), 0.32);
            animation: rotate 3s linear infinite;
        }

        .reactor-container-inner {
            box-shadow: 0px 0px 90px 30px rgba(var(--arc-color), 0.4),
                        inset 0px 0px 90px 30px rgba(var(--arc-color), 0.4);
        }

        .core-inner {
            animation: core-pulse-speak 0.5s ease-in-out infinite;
        }

        .core-outer {
            box-shadow: 0px 0px 8px 5px var(--arc-glow),
                        0px 0px 20px 14px var(--arc-glow) inset;
        }

        .core-wrapper {
            box-shadow: 0px 0px 14px 10px var(--arc-glow),
                        0px 0px 14px 7px var(--arc-glow) inset;
        }

        .tunnel {
            box-shadow: 0px 0px 14px 5px var(--arc-glow),
                        0px 0px 14px 10px var(--arc-glow) inset;
        }

        .marks li {
            animation: colour_ease2_active 0.6s infinite ease-in-out;
        }
    }

    .reactor-container.speaking::before {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1.15);
        animation: bg-pulse 1.1s ease-in-out infinite;
    }

    @keyframes core-pulse-speak {
        0%, 100% {
            box-shadow: 0px 0px 15px 10px var(--arc-glow),
                        0px 0px 20px 15px var(--arc-glow) inset;
        }
        50% {
            box-shadow: 0px 0px 28px 20px var(--arc-glow),
                        0px 0px 34px 24px var(--arc-glow) inset;
        }
    }

    @keyframes bar-speak-a {
        0% { @include bar-transform(0.6); }
        15% { @include bar-transform(2.1); }
        30% { @include bar-transform(0.9); }
        48% { @include bar-transform(1.8); }
        65% { @include bar-transform(0.7); }
        80% { @include bar-transform(2.3); }
        100% { @include bar-transform(0.6); }
    }

    @keyframes bar-speak-b {
        0% { @include bar-transform(1.6); }
        20% { @include bar-transform(0.6); }
        40% { @include bar-transform(2.2); }
        60% { @include bar-transform(0.8); }
        82% { @include bar-transform(1.9); }
        100% { @include bar-transform(1.6); }
    }

    @keyframes bar-speak-c {
        0% { @include bar-transform(0.8); }
        25% { @include bar-transform(1.7); }
        45% { @include bar-transform(2.4); }
        70% { @include bar-transform(0.9); }
        90% { @include bar-transform(1.5); }
        100% { @include bar-transform(0.8); }
    }

    @keyframes bar-speak-d {
        0% { @include bar-transform(2); }
        18% { @include bar-transform(0.7); }
        38% { @include bar-transform(1.5); }
        58% { @include bar-transform(2.3); }
        78% { @include bar-transform(0.6); }
        100% { @include bar-transform(2); }
    }
</style>
