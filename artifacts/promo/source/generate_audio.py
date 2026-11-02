#!/usr/bin/env python3
"""Generate a synchronized 38.0s stereo soundtrack (BGM + SFX) for the deslop promo video.

Uses only the Python 3.10+ standard library (math, struct, wave, random).
Tempo: 120 BPM (1 beat = 0.5s, 1 bar = 2.0s).
Sample rate: 48,000 Hz, 16-bit stereo PCM.
"""
import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 48000
DURATION = 38.0
N_SAMPLES = int(SR * DURATION)


def midi_to_freq(midi_note: float) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69.0) / 12.0))


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 <= edge0:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def add_tone(
    buf_l: list[float],
    buf_r: list[float],
    start_s: float,
    dur_s: float,
    freq: float,
    amp: float,
    *,
    pan: float = 0.0,
    attack: float = 0.015,
    decay: float = 4.0,
    richness: float = 0.25,
    detune: float = 0.002,
) -> None:
    i0 = max(0, int(start_s * SR))
    i1 = min(N_SAMPLES, int((start_s + dur_s) * SR))
    gain_l = amp * math.cos((pan + 1.0) * math.pi / 4.0)
    gain_r = amp * math.sin((pan + 1.0) * math.pi / 4.0)
    two_pi_sr = 2.0 * math.pi / SR
    w1 = freq * two_pi_sr
    w2 = freq * (1.0 + detune) * two_pi_sr
    w3 = freq * 2.0 * two_pi_sr
    for i in range(i0, i1):
        t = (i - i0) / SR
        env = min(1.0, t / max(0.001, attack)) * math.exp(-decay * t)
        # Fade out tail cleanly at end of dur_s
        rem = dur_s - t
        if rem < 0.04:
            env *= max(0.0, rem / 0.04)
        ph = i - i0
        s_l = math.sin(w1 * ph) + richness * math.sin(w3 * ph)
        s_r = math.sin(w2 * ph) + richness * math.sin(w3 * ph + 0.3)
        buf_l[i] += gain_l * env * s_l
        buf_r[i] += gain_r * env * s_r


def add_redline_slash(
    buf_l: list[float],
    buf_r: list[float],
    start_s: float,
    amp: float = 0.22,
    pan: float = 0.0,
    pitch_mult: float = 1.0,
) -> None:
    """Crisp editorial pen slash + laser transient."""
    dur_s = 0.24
    i0 = max(0, int(start_s * SR))
    i1 = min(N_SAMPLES, int((start_s + dur_s) * SR))
    rng = random.Random(int(start_s * 1000))
    gain_l = amp * math.cos((pan + 1.0) * math.pi / 4.0)
    gain_r = amp * math.sin((pan + 1.0) * math.pi / 4.0)
    lp = 0.0
    for i in range(i0, i1):
        t = (i - i0) / SR
        env = smoothstep(0.0, 0.006, t) * math.exp(-16.0 * t)
        # Downward frequency sweep
        f = (2200.0 * math.exp(-12.0 * t) + 320.0) * pitch_mult
        tone = math.sin(2.0 * math.pi * f * t)
        noise = rng.uniform(-1.0, 1.0)
        lp = 0.72 * lp + 0.28 * noise
        sig = (0.62 * tone + 0.38 * lp) * env
        buf_l[i] += gain_l * sig
        buf_r[i] += gain_r * sig


def add_sub_impact(
    buf_l: list[float],
    buf_r: list[float],
    start_s: float,
    amp: float = 0.34,
    base_freq: float = 55.0,
) -> None:
    """Warm Apple-keynote style sub impact."""
    dur_s = 1.15
    i0 = max(0, int(start_s * SR))
    i1 = min(N_SAMPLES, int((start_s + dur_s) * SR))
    phase = 0.0
    for i in range(i0, i1):
        t = (i - i0) / SR
        env = smoothstep(0.0, 0.012, t) * math.exp(-3.4 * t)
        f = base_freq + 95.0 * math.exp(-22.0 * t)
        phase += 2.0 * math.pi * f / SR
        sig = (math.sin(phase) + 0.25 * math.sin(2.0 * phase)) * env * amp
        buf_l[i] += sig
        buf_r[i] += sig


def add_whoosh(
    buf_l: list[float],
    buf_r: list[float],
    start_s: float,
    dur_s: float = 0.42,
    amp: float = 0.14,
) -> None:
    """Smooth stereo transition whoosh."""
    i0 = max(0, int(start_s * SR))
    i1 = min(N_SAMPLES, int((start_s + dur_s) * SR))
    rng = random.Random(int(start_s * 500) + 7)
    state_l, state_r = 0.0, 0.0
    for i in range(i0, i1):
        t = (i - i0) / SR
        u = t / dur_s
        env = math.sin(math.pi * u) ** 1.6
        pan = -0.6 + 1.2 * u
        gl = amp * math.cos((pan + 1.0) * math.pi / 4.0)
        gr = amp * math.sin((pan + 1.0) * math.pi / 4.0)
        alpha = 0.08 + 0.25 * math.sin(math.pi * u)
        state_l = (1.0 - alpha) * state_l + alpha * rng.uniform(-1.0, 1.0)
        state_r = (1.0 - alpha) * state_r + alpha * rng.uniform(-1.0, 1.0)
        tone = 0.35 * math.sin(2.0 * math.pi * (180.0 + 260.0 * u) * t)
        buf_l[i] += gl * env * (state_l + tone)
        buf_r[i] += gr * env * (state_r + tone)


def add_ui_tick(
    buf_l: list[float],
    buf_r: list[float],
    start_s: float,
    freq: float = 1600.0,
    amp: float = 0.10,
    pan: float = 0.0,
) -> None:
    dur_s = 0.045
    add_tone(
        buf_l,
        buf_r,
        start_s,
        dur_s,
        freq,
        amp,
        pan=pan,
        attack=0.002,
        decay=65.0,
        richness=0.15,
    )


def generate(out_path: Path) -> None:
    buf_l = [0.0] * N_SAMPLES
    buf_r = [0.0] * N_SAMPLES

    # 1. Chord Progression Pad across 38s (120 BPM, 2.0s per bar = 19 bars)
    # Warm intelligent progression: Am9 -> Fmaj7 -> Cmaj9 -> G6
    chord_bars = [
        # Scene 1 (0.0 - 4.5s): Focused minimal pulse
        (0.0, 2.5, [45, 52, 57, 64, 67]),
        (2.5, 2.0, [41, 48, 57, 60, 64]),
        # Scene 2 (4.5 - 9.5s): Tension & contrast
        (4.5, 2.5, [45, 52, 59, 60, 64]),
        (7.0, 2.5, [41, 48, 55, 60, 64]),
        # Scene 3 (9.5 - 17.5s): Scan -> 13.5s resolution lift
        (9.5, 4.0, [38, 50, 57, 60, 65]),
        (13.5, 4.0, [48, 55, 60, 64, 67, 71]),  # Bright Cmaj9 lift on After reveal!
        # Scene 4 (17.5 - 25.0s): Three Layers & 10 Genres
        (17.5, 2.5, [45, 52, 57, 64, 69]),
        (20.0, 2.5, [41, 48, 57, 60, 67]),
        (22.5, 2.5, [43, 50, 55, 59, 67]),
        # Scene 5 (25.0 - 32.5s): Climax (Run Contract & Exit 0)
        (25.0, 2.5, [45, 52, 57, 64, 71]),
        (27.5, 2.0, [41, 48, 57, 64, 69]),
        (29.5, 3.0, [48, 55, 60, 64, 67, 72]),  # Triumphant C major resolution at Exit 0
        # Scene 6 (32.5 - 38.0s): Finale & CTA warm resolve
        (32.5, 3.0, [41, 48, 57, 60, 64, 69]),
        (35.5, 2.5, [45, 52, 57, 64, 69, 76]),
    ]

    for start_s, dur_s, notes in chord_bars:
        for idx, note in enumerate(notes):
            pan = -0.35 + 0.7 * (idx / max(1, len(notes) - 1))
            amp = 0.055 if note < 50 else 0.036
            add_tone(
                buf_l,
                buf_r,
                start_s,
                dur_s + 0.35,
                midi_to_freq(note),
                amp,
                pan=pan,
                attack=0.18,
                decay=0.55,
                richness=0.22,
                detune=0.003,
            )

    # 2. Rhythmic 120 BPM Marimba/Pluck Arpeggio (0.25s = 8th note, 0.125s = 16th note)
    arp_scale = [57, 60, 64, 67, 69, 72, 69, 64]
    t = 0.5
    step = 0
    while t < 36.0:
        # Pause arp slightly at dramatic hits (2.3-2.7s, 13.3-13.7s, 29.3-29.8s)
        if not (2.25 <= t <= 2.65 or 13.25 <= t <= 13.65 or 29.25 <= t <= 29.75):
            note = arp_scale[step % len(arp_scale)]
            if 13.5 <= t < 17.5 or 29.5 <= t < 32.5:
                note += 3  # Brighter register during resolution moments
            pan = 0.32 if (step % 2 == 0) else -0.32
            accent = 1.25 if (step % 4 == 0) else 0.78
            add_tone(
                buf_l,
                buf_r,
                t,
                0.22,
                midi_to_freq(note),
                0.042 * accent,
                pan=pan,
                attack=0.005,
                decay=14.0,
                richness=0.30,
            )
        t += 0.25
        step += 1

    # 3. Soft 120 BPM Heartbeat Pulse on every beat (0.5s) from 0.5s to 35.5s
    beat_t = 0.5
    beat_idx = 0
    while beat_t <= 35.5:
        if beat_idx % 2 == 0:
            add_sub_impact(buf_l, buf_r, beat_t, amp=0.11, base_freq=55.0)
        else:
            add_ui_tick(buf_l, buf_r, beat_t, freq=920.0, amp=0.035, pan=0.0)
        beat_t += 0.5
        beat_idx += 1

    # 4. Scene-Specific Synchronized SFX
    # Scene 1 (0.0 - 4.5s): Opening sub + 4 Redline slashes + 2.4s Hero Title Impact
    add_sub_impact(buf_l, buf_r, 0.05, amp=0.28, base_freq=52.0)
    slash_times = [
        (0.55, -0.35, 1.00),
        (0.95, 0.25, 1.08),
        (1.35, -0.20, 1.16),
        (1.75, 0.35, 1.25),
    ]
    for st, pan, pm in slash_times:
        add_redline_slash(buf_l, buf_r, st, amp=0.22, pan=pan, pitch_mult=pm)

    # 2.4s Hero title lock-in
    add_sub_impact(buf_l, buf_r, 2.38, amp=0.32, base_freq=48.0)
    for idx, n in enumerate([57, 64, 69, 76]):
        add_tone(
            buf_l,
            buf_r,
            2.40 + idx * 0.03,
            1.4,
            midi_to_freq(n),
            0.075,
            pan=-0.2 + 0.13 * idx,
            attack=0.008,
            decay=2.8,
        )

    # Scene 2 (4.5 - 9.5s): Transition + Left Warning (5.8s) + Right Solution Lock (7.3s)
    add_whoosh(buf_l, buf_r, 4.35, dur_s=0.40, amp=0.16)
    # 5.8s: Synonym trap dull buzz
    add_tone(buf_l, buf_r, 5.80, 0.35, 195.0, 0.09, pan=-0.4, attack=0.01, decay=7.0, richness=0.6)
    add_tone(buf_l, buf_r, 6.02, 0.35, 185.0, 0.09, pan=-0.4, attack=0.01, decay=7.0, richness=0.6)
    # 7.3s: Clean deterministic chime
    for idx, n in enumerate([64, 69, 76]):
        add_tone(buf_l, buf_r, 7.30 + idx * 0.05, 0.9, midi_to_freq(n), 0.08, pan=0.35, attack=0.005, decay=4.5)

    # Scene 3 (9.5 - 17.5s): Live Redline Scan (10.0s - 12.8s) -> 13.5s Collapse & Crystallize
    add_whoosh(buf_l, buf_r, 9.35, dur_s=0.40, amp=0.16)
    for k in range(14):
        tk = 10.0 + k * 0.18
        add_ui_tick(
            buf_l,
            buf_r,
            tk,
            freq=1200.0 + k * 55.0,
            amp=0.07,
            pan=-0.4 + (k % 3) * 0.4,
        )
    # 13.5s: Crisp collapse & emerald crystallization chord
    add_redline_slash(buf_l, buf_r, 13.45, amp=0.18, pan=0.0, pitch_mult=1.35)
    add_sub_impact(buf_l, buf_r, 13.50, amp=0.28, base_freq=65.4)
    for idx, n in enumerate([60, 64, 67, 71, 76]):
        add_tone(
            buf_l,
            buf_r,
            13.50 + idx * 0.04,
            1.8,
            midi_to_freq(n),
            0.075,
            pan=-0.3 + 0.15 * idx,
            attack=0.006,
            decay=2.4,
        )

    # Scene 4 (17.5 - 25.0s): 3 Layers (18.0s, 19.3s, 20.6s) + 10 Genres selector ticks (22.0s - 24.2s)
    add_whoosh(buf_l, buf_r, 17.35, dur_s=0.40, amp=0.16)
    for layer_idx, (lt, note) in enumerate([(18.0, 64), (19.3, 67), (20.6, 72)]):
        add_tone(buf_l, buf_r, lt, 0.75, midi_to_freq(note), 0.085, pan=-0.25 + layer_idx * 0.25, attack=0.005, decay=4.5)
        add_Tone_oct = midi_to_freq(note + 12)
        add_tone(buf_l, buf_r, lt + 0.03, 0.55, add_Tone_oct, 0.045, pan=-0.25 + layer_idx * 0.25, attack=0.004, decay=6.0)

    for g_idx in range(10):
        gt = 22.0 + g_idx * 0.22
        add_ui_tick(buf_l, buf_r, gt, freq=1450.0 + g_idx * 70.0, amp=0.065, pan=-0.45 + g_idx * 0.1)

    # Scene 5 (25.0 - 32.5s): Climax — 6 Phases + 5 Fact Locks + 29.5s Contract OK
    add_whoosh(buf_l, buf_r, 24.85, dur_s=0.45, amp=0.20)
    add_sub_impact(buf_l, buf_r, 25.0, amp=0.34, base_freq=45.0)
    # 5 Fact Shield locks
    shield_notes = [64, 67, 69, 72, 76]
    for s_idx, sn in enumerate(shield_notes):
        st = 26.2 + s_idx * 0.48
        add_tone(buf_l, buf_r, st, 0.65, midi_to_freq(sn), 0.08, pan=-0.4 + s_idx * 0.2, attack=0.004, decay=5.0)
        add_ui_tick(buf_l, buf_r, st, freq=2400.0, amp=0.06, pan=-0.4 + s_idx * 0.2)

    # 29.5s: CONTRACT OK (Exit 0) Climax Shimmer Chord
    add_sub_impact(buf_l, buf_r, 29.50, amp=0.36, base_freq=65.4)
    for idx, n in enumerate([60, 67, 72, 76, 79, 84]):
        add_tone(
            buf_l,
            buf_r,
            29.50 + idx * 0.035,
            2.4,
            midi_to_freq(n),
            0.072,
            pan=-0.4 + 0.16 * idx,
            attack=0.008,
            decay=1.9,
            richness=0.32,
        )

    # Scene 6 (32.5 - 38.0s): Finale & CTA
    add_whoosh(buf_l, buf_r, 32.35, dur_s=0.42, amp=0.15)
    add_sub_impact(buf_l, buf_r, 32.50, amp=0.26, base_freq=55.0)
    # Command typing ticks (33.6s - 34.8s)
    for c_idx in range(10):
        ct = 33.6 + c_idx * 0.11
        add_ui_tick(buf_l, buf_r, ct, freq=1750.0 + (c_idx % 3) * 140.0, amp=0.055, pan=-0.15 + (c_idx % 2) * 0.3)
    # Final warm resolving chime at 35.0s
    for idx, n in enumerate([57, 64, 69, 71, 76]):
        add_tone(
            buf_l,
            buf_r,
            35.0 + idx * 0.05,
            2.8,
            midi_to_freq(n),
            0.065,
            pan=-0.3 + 0.15 * idx,
            attack=0.015,
            decay=1.5,
        )

    # 5. Master Envelope (Fade in 0.0 -> 0.15s, Smooth Fade out 36.4 -> 38.0s) & Soft Limiter
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pcm = bytearray(N_SAMPLES * 4)
    peak = 0.0
    for i in range(N_SAMPLES):
        t = i / SR
        master_env = smoothstep(0.0, 0.12, t) * (1.0 - smoothstep(36.4, 37.95, t))
        # Soft saturation limiter (guarantees zero clipping, max around 0.82 full scale)
        l_val = math.tanh(buf_l[i] * master_env * 1.15) * 0.82
        r_val = math.tanh(buf_r[i] * master_env * 1.15) * 0.82
        peak = max(peak, abs(l_val), abs(r_val))
        li = int(max(-32767, min(32767, round(l_val * 32767.0))))
        ri = int(max(-32767, min(32767, round(r_val * 32767.0))))
        struct.pack_into("<hh", pcm, i * 4, li, ri)

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm)

    print(f"Generated {out_path} ({DURATION:.1f}s, {SR}Hz stereo, peak={peak:.3f})")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/promo/assets/soundtrack.wav")
    generate(target)
