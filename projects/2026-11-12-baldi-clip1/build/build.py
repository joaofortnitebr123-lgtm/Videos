"""Build the vertical Short for clip 1 (rage door) from input/source.mp4."""
import json, re, subprocess, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/input/source.mp4"
SFX = f"{ROOT}/../../.claude/skills/edit-video/assets/sfx"
OUT = f"{ROOT}/exports/clip1_rage_v1.mp4"

# (source_start, source_end)
SEGS = [(14.30, 27.30), (28.90, 35.20), (38.95, 43.60), (46.60, 56.00)]
FACE_HIDE_SRC = (18.95, 21.95)  # source shows his full-screen facecam here

def to_out(t):
    acc = 0.0
    for s, e in SEGS:
        if s <= t <= e:
            return acc + (t - s)
        acc += e - s
    return None

TOTAL = sum(e - s for s, e in SEGS)

# ---------- captions ----------
words = json.load(open(f"{ROOT}/build/words.json"))
FIX = {"porra,": "a porta,"}
HL = {"CHEGA", "CHEGA.", "PACIÊNCIA,", "BALDI,", "PORTA", "PORTA,", "QUEBRADA!", "AGUENTO", "MAIS!", "NÃO!"}

ws = []
for w in words:
    o = to_out(w["s"])
    if o is None or w["s"] >= 55.85:
        continue
    oe = to_out(min(w["e"], next(e for s, e in SEGS if s <= w["s"] <= e)))
    txt = FIX.get(w["w"], w["w"])
    for i, part in enumerate(txt.split()):
        ws.append({"w": part.upper(), "s": o, "e": oe})

groups, cur = [], []
for i, w in enumerate(ws):
    if cur:
        gap = w["s"] - cur[-1]["e"]
        chars = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
        if gap > 0.35 or len(cur) >= 3 or chars > 16 or re.search(r"[.!?,]$", cur[-1]["w"]):
            groups.append(cur); cur = []
    cur.append(w)
groups.append(cur)

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

YEL = "&H0000D7FF&"
lines = []
for gi, g in enumerate(groups):
    start = g[0]["s"]
    end = min(min(g[-1]["e"], g[-1]["s"] + 0.9) + 0.45, groups[gi + 1][0]["s"] if gi + 1 < len(groups) else TOTAL)
    parts = []
    for w in g:
        t = w["w"].rstrip(".,")
        if w["w"] in HL or t in {x.rstrip(".,!") for x in HL}:
            parts.append(f"{{\\c{YEL}}}{t}{{\\c&HFFFFFF&}}")
        else:
            parts.append(t)
    text = " ".join(parts).replace("...", "…")
    if gi + 1 == len(groups): end = TOTAL
    if text.endswith("CH"): text += "—"
    pop = r"{\fscx82\fscy82\t(0,90,\fscx100\fscy100)}"
    lines.append(f"Dialogue: 1,{ts(start)},{ts(end)},Cap,,0,0,0,,{pop}{text}")

title = (r"Dialogue: 0," + ts(0) + "," + ts(TOTAL) +
         r",Title,,0,0,0,,{\fad(0,0)}ELE PERDEU A\N{\c" + YEL + r"}PACIÊNCIA")

ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Inter Black,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,9,4,8,80,80,280,1
Style: Cap,Inter Black,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,8,3,2,180,180,790,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{title}
""" + "\n".join(lines) + "\n"
open(f"{ROOT}/build/captions.ass", "w").write(ass)

# ---------- video/audio graph ----------
fh0, fh1 = to_out(FACE_HIDE_SRC[0]), to_out(FACE_HIDE_SRC[1])
porta_t = to_out(51.98)
shutter_t = fh0

fc = []
for i, (s, e) in enumerate(SEGS):
    d = e - s
    fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30[v{i}]")
    fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d-0.06:.3f}:d=0.06[a{i}]")
n = len(SEGS)
fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
fc.append("[cv]split=3[c1][c2][c3]")
# blurred background
fc.append("[c1]scale=-2:1920,crop=1080:1920,boxblur=28:2,eq=brightness=-0.22:saturation=1.2[bg]")
# gameplay: crop away the facecam column, upscale
fc.append("[c2]crop=440:320:0:0,scale=1080:786:flags=lanczos,unsharp=5:5:0.8[gp]")
# facecam with white border
fc.append("[c3]crop=116:86:442:8,scale=528:392:flags=lanczos,unsharp=5:5:0.6,pad=540:404:6:6:white[fcam]")
fc.append("[bg][gp]overlay=0:500[b1]")
fc.append(f"[b1][fcam]overlay=270:1320:enable='not(between(t,{fh0:.3f},{fh1:.3f}))'[b2]")
fc.append(f"[b2]subtitles='{ROOT}/build/captions.ass':fontsdir=/usr/share/fonts/opentype/inter[vout]")
# audio: voice/game + sfx
fc.append(f"[1:a]adelay={int(porta_t*1000)}|{int(porta_t*1000)},volume=0.9[s1]")
fc.append(f"[2:a]adelay={int(shutter_t*1000)}|{int(shutter_t*1000)},volume=0.35[s2]")
fc.append("[ca]aformat=channel_layouts=stereo[ca2]")
fc.append("[ca2][s1][s2]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

cmd = ["ffmpeg", "-v", "error", "-y", "-i", SRC,
       "-i", f"{SFX}/sub-impact.wav", "-i", f"{SFX}/curated/camera-shutter-light.wav",
       "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT]
print(f"total {TOTAL:.2f}s, face hidden {fh0:.2f}-{fh1:.2f}, porta sfx {porta_t:.2f}")
for l in lines: print(l.split(",,0,0,0,,")[0].split(",")[1:3], re.sub(r"\{[^}]*\}", "", l.split(",,0,0,0,,")[1]))
subprocess.run(cmd, check=True)
print("ok", OUT)
