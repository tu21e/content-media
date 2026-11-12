"""Original cinematic/inspirational soundtrack generator (royalty-free, synthesized)."""
import wave
import numpy as np

SR = 44100


def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n, np.float32)
    na = min(n, int(a * sr)); nr = min(n - na, int(r * sr))
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def add(buf, start, sig):
    s = int(start * SR); n = sig.shape[-1]
    if s >= buf.shape[-1] or s + n <= 0: return
    if s < 0: sig = sig[..., -s:]; s = 0; n = sig.shape[-1]
    L = min(n, buf.shape[-1] - s)
    buf[..., s:s + L] += sig[..., :L]


def saw(f, t, harm=10, det=0.0):
    out = np.zeros_like(t)
    for k in range(1, harm + 1):
        if f * k > 9000: break
        out += np.sin(2 * np.pi * f * k * t * (1 + det)) / k
    return out


def pad_note(f, dur, rnd):
    n = int(dur * SR); t = np.arange(n) / SR
    L = saw(f, t, 9, -0.004) + 0.6 * saw(f * 0.5, t, 6, 0.002)
    R = saw(f, t, 9, 0.004) + 0.6 * saw(f * 0.5, t, 6, -0.002)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 0.25 * t + rnd.uniform(0, 6))
    e = env_adsr(n, 0.9, 1.0) * trem
    return np.stack([L * e, R * e]).astype(np.float32) * 0.012


def piano(f, dur=1.6, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k, a in enumerate([1.0, 0.45, 0.22, 0.12, 0.06, 0.03], 1):
        out += a * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (2.2 + 1.6 * k))
    att = np.minimum(1, t / 0.004)
    return (out * att * vel * 0.16).astype(np.float32)


def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return (s * env_adsr(n, 0.02, 0.25) * np.exp(-t * 0.6) * 0.2).astype(np.float32)


def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t * 26)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5) * 0.42).astype(np.float32)


def noise(n, rnd): return rnd.normal(0, 1, n).astype(np.float32)


def clap(rnd):
    n = int(0.3 * SR); t = np.arange(n) / SR
    x = np.diff(noise(n + 1, rnd)) * 0.5
    e = np.exp(-t * 16) + 0.5 * np.exp(-((t - 0.012) * 300) ** 2)
    return (x * e * 0.12).astype(np.float32)


def hat(rnd, open_=False):
    n = int((0.18 if open_ else 0.05) * SR); t = np.arange(n) / SR
    x = np.diff(np.diff(noise(n + 2, rnd)))
    return (x * np.exp(-t * (18 if open_ else 90)) * 0.028).astype(np.float32)


def riser(dur, rnd):
    n = int(dur * SR); t = np.arange(n) / SR; p = t / dur
    x = noise(n, rnd)
    # progressively brighter: blend low-passed and high-passed noise
    lp = np.convolve(x, np.ones(40) / 40, "same")
    hp = np.diff(np.concatenate([[0], x]))
    s = lp * (1 - p) * 2.5 + hp * p * 0.6
    sweep = np.sin(2 * np.pi * np.cumsum(180 + 900 * p ** 2) / SR) * 0.25
    return ((s * 0.2 + sweep * 0.4) * p ** 2.0).astype(np.float32)


def impact(rnd):
    n = int(2.2 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 8)) / SR) * np.exp(-t * 2.2)
    x = noise(n, rnd); sh = np.convolve(x, np.ones(6) / 6, "same") * np.exp(-t * 5)
    return (boom * 0.38 + sh * 0.14).astype(np.float32)


def whoosh(rnd, dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR; p = t / dur
    x = np.convolve(noise(n, rnd), np.ones(8) / 8, "same")
    return (x * np.sin(np.pi * p) ** 2 * 0.09).astype(np.float32)


def reverb(x, secs=2.4, seed=7):
    rnd = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    out = []
    for ch in range(2):
        ir = rnd.normal(0, 1, n).astype(np.float32) * np.exp(-t * 3.0)
        ir = np.convolve(ir, np.ones(5) / 5, "same"); ir[:int(0.02 * SR)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        L = len(x[ch]) + n; N = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[ch], N) * np.fft.rfft(ir, N), N)[:len(x[ch])]
        out.append(y.astype(np.float32))
    return np.stack(out)


PROG = [[9, 12, 16], [5, 9, 12], [0, 4, 7], [7, 11, 14]]  # vi IV I V
PROG2 = [[5, 9, 12], [7, 11, 14], [9, 12, 16], [0, 4, 7]]  # IV V vi I
KEYS = [60, 62, 57, 59, 64, 55]


def compose(path, dur, intro_end, cuts=(), seed=0, outro=3.0):
    rnd = np.random.default_rng(seed)
    key = KEYS[seed % len(KEYS)] - 12 if KEYS[seed % len(KEYS)] > 61 else KEYS[seed % len(KEYS)]
    prog = PROG if seed % 2 else PROG2
    bpm = [92, 96, 100, 88][seed % 4]; beat = 60 / bpm; bar = beat * 4
    n = int(dur * SR) + SR
    dry = np.zeros((2, n), np.float32); wet = np.zeros((2, n), np.float32)
    end_drums = dur - outro
    # ---- intro: pad swell + sparse piano + riser + impact
    c0 = prog[0]
    for iv in c0:
        wet_note = pad_note(mtof(key + iv), intro_end + 0.6, rnd)
        add(wet, 0, wet_note * 1.2)
    for i, iv in enumerate([c0[0], c0[2], c0[1] + 12, c0[2] + 12]):
        add(wet, 0.25 + i * intro_end / 5, np.stack([piano(mtof(key + 12 + iv), 2.0, 0.8)] * 2) * 0.9)
    r = riser(intro_end - 0.05, rnd); add(dry, 0.05, np.stack([r, r]))
    im = impact(rnd); add(dry, intro_end, np.stack([im, im]))
    add(wet, intro_end, np.stack([im, im]) * 0.5)
    # ---- main groove from intro_end
    t0 = intro_end; bi = 0
    while t0 + bi * bar < dur:
        tb = t0 + bi * bar; ch = prog[bi % 4]
        for iv in ch:
            add(wet, tb, pad_note(mtof(key + iv), bar + 0.9, rnd))
        add(dry, tb, np.stack([bass(mtof(key - 24 + ch[0] % 12), bar * 0.95)] * 2))
        # piano arpeggio (8ths)
        pat = [0, 1, 2, 1, 0 + 3, 2, 1, 2]
        for k in range(8):
            tt = tb + k * beat / 2
            if tt > dur - 0.5: break
            nn = ch[pat[k] % 3] + (12 if pat[k] >= 3 or k >= 4 else 0)
            v = 0.85 if k % 2 == 0 else 0.6
            p = piano(mtof(key + 12 + nn), 1.4, v)
            pan = 0.5 + 0.3 * np.sin(k)
            add(wet, tt, np.stack([p * (1.2 - pan), p * (0.4 + pan)]) * 0.9)
        # drums
        for k in range(4):
            tt = tb + k * beat
            if tt >= end_drums: break
            if k in (0, 2): kk = kick(); add(dry, tt, np.stack([kk, kk]))
            if k in (1, 3) and bi >= 1:
                c = clap(rnd); add(dry, tt, np.stack([c, c])); add(wet, tt, np.stack([c, c]) * 1.2)
            for h in (0, 0.5):
                hh = hat(rnd, open_=(h == 0.5 and k == 3)); add(dry, tt + h * beat, np.stack([hh * 0.8, hh * 1.1]))
        bi += 1
    # transition whooshes
    for c in cuts:
        w = whoosh(rnd); add(dry, c - 0.3, np.stack([w * 0.8, w * 1.1]))
    # outro swell
    add(wet, dur - outro, np.stack([piano(mtof(key + 24 + prog[0][0]), 3.0, 0.9)] * 2))
    mix = dry + reverb(wet) * 1.0 + wet * 0.55
    mix = mix[:, :int(dur * SR)]
    fi = int(0.05 * SR); fo = int(1.6 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi); mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    mix /= (np.abs(mix).max() + 1e-6)
    mix = np.tanh(mix * 1.3) / np.tanh(1.3) * 0.89
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
