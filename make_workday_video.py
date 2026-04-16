"""
Generates 'Workday Decoded — Org Structures & Security' as an MP4 video.
Produces TTS narration via gTTS and slides via Pillow, combined with MoviePy.
"""

import os
import textwrap
from pathlib import Path

import numpy as np

import subprocess

from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24
AUDIO_DIR = Path("/tmp/wd_audio")
AUDIO_DIR.mkdir(exist_ok=True)
OUT = Path("/home/user/Videos/workday_decoded.mp4")

# Palette
BG       = (15, 20, 40)      # dark navy
ACCENT   = (240, 165, 0)     # amber
TEXT     = (230, 230, 230)   # near-white body
HEADING  = (255, 255, 255)   # pure white
DIM      = (120, 130, 150)   # muted
STEP_COL = {1: (70, 180, 255), 2: (100, 220, 160), 3: (255, 120, 100)}  # blue, green, red

# ── Font helpers ───────────────────────────────────────────────────────────────
def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

FONT_TITLE  = font(52, bold=True)
FONT_SUB    = font(36, bold=True)
FONT_BODY   = font(28)
FONT_BULLET = font(26)
FONT_LABEL  = font(22)
FONT_STEP   = font(120, bold=True)

# ── Drawing utilities ──────────────────────────────────────────────────────────
def new_frame():
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    # subtle bottom rule
    d.rectangle([(0, H - 4), (W, H)], fill=ACCENT)
    return img, d

def draw_wrapped(d, text, x, y, max_w, fnt, fill, line_spacing=8):
    avg_char = fnt.getlength("M")
    chars_per_line = max(1, int(max_w / avg_char))
    lines = textwrap.wrap(text, width=chars_per_line)
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill)
        bbox = fnt.getbbox(line)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y

def pill(d, x, y, label, color):
    tw = FONT_LABEL.getlength(label)
    pad = 10
    d.rounded_rectangle([(x, y), (x + tw + pad * 2, y + 32)], radius=8, fill=color)
    d.text((x + pad, y + 4), label, font=FONT_LABEL, fill=(20, 20, 30))

# ── Slide builders ─────────────────────────────────────────────────────────────
def slide_intro():
    img, d = new_frame()
    # Amber top bar
    d.rectangle([(0, 0), (W, 6)], fill=ACCENT)
    # Ghost big text
    d.text((60, 80), "WORKDAY", font=font(110, bold=True), fill=(30, 35, 60))
    d.text((60, 195), "DECODED", font=font(110, bold=True), fill=(30, 35, 60))
    # Overlay title
    d.text((64, 90), "WORKDAY", font=font(108, bold=True), fill=HEADING)
    d.text((64, 205), "DECODED", font=font(108, bold=True), fill=HEADING)
    # Subtitle
    d.text((68, 325), "Org Structures & Security", font=font(38), fill=ACCENT)
    # Rule
    d.rectangle([(66, 378), (680, 382)], fill=DIM)
    # Tagline
    draw_wrapped(d,
        "A three-step triage for any Workday org or security query.",
        66, 398, 800, FONT_BODY, TEXT)
    # Step pills
    for i, (lbl, col) in enumerate(
            [("Step 1  Identify", STEP_COL[1]),
             ("Step 2  Classify", STEP_COL[2]),
             ("Step 3  Resolve",  STEP_COL[3])]):
        pill(d, 66 + i * 240, 510, lbl, col)
    return img

def slide_step(step_num, title, bullets, color):
    img, d = new_frame()
    d.rectangle([(0, 0), (W, 6)], fill=color)
    # Big step number (ghost)
    d.text((W - 260, H - 280), str(step_num), font=FONT_STEP, fill=(25, 30, 55))
    # Step badge
    d.text((60, 40), f"STEP {step_num}", font=font(20, bold=True), fill=color)
    # Title
    y = draw_wrapped(d, title, 60, 80, W - 120, FONT_SUB, HEADING, line_spacing=6)
    # Rule
    d.rectangle([(60, y + 12), (60 + int(FONT_SUB.getlength(title[:30])), y + 15)],
                fill=color)
    y += 36
    # Bullets
    for bullet in bullets:
        d.text((60, y), "▸", font=FONT_BULLET, fill=color)
        y = draw_wrapped(d, bullet, 90, y, W - 160, FONT_BULLET, TEXT, line_spacing=6)
        y += 10
    return img

def slide_bucket(step_num, bucket_num, bucket_title, body, color, bucket_color):
    img, d = new_frame()
    d.rectangle([(0, 0), (W, 6)], fill=color)
    d.text((60, 40), f"STEP {step_num}  ·  RESOLUTION", font=font(20, bold=True), fill=color)
    d.text((60, 80), f"Bucket {bucket_num}: {bucket_title}", font=FONT_SUB, fill=bucket_color)
    d.rectangle([(60, 128), (400, 131)], fill=bucket_color)
    draw_wrapped(d, body, 60, 148, W - 120, FONT_BULLET, TEXT, line_spacing=8)
    # Ghost number
    d.text((W - 260, H - 280), str(step_num), font=FONT_STEP, fill=(25, 30, 55))
    return img

def slide_outro():
    img, d = new_frame()
    d.rectangle([(0, 0), (W, 6)], fill=ACCENT)
    d.text((60, 60), "THREE STEPS", font=font(60, bold=True), fill=HEADING)
    d.rectangle([(60, 138), (500, 142)], fill=ACCENT)
    steps = [
        (STEP_COL[1], "1  Identify the structure type"),
        (STEP_COL[2], "2  Classify: structural vs access"),
        (STEP_COL[3], "3  Route to the right fix"),
    ]
    y = 160
    for col, label in steps:
        d.text((60, y), "▸", font=font(32, bold=True), fill=col)
        d.text((100, y + 2), label, font=font(32), fill=TEXT)
        y += 56
    # Footer
    draw_wrapped(d,
        "Thirty seconds of triage saves you an afternoon of solving the wrong problem.",
        60, y + 30, W - 120, FONT_BODY, DIM)
    return img

# ── Narration text ─────────────────────────────────────────────────────────────
NARRATION = [
    # (key, ssml)  — espeak-ng processes these with -m flag
    ("intro", """<speak>
<p>If you've ever spent an afternoon chasing a Workday ticket
in <prosody rate="95%">completely the wrong direction</prosody> —
<break time="200ms"/>
fixing security when it was actually an org problem,
<break time="150ms"/>
or restructuring a hierarchy when it was just a role assignment —
<break time="200ms"/>
this one's for you.</p>

<p>I'm going to walk you through a <prosody rate="92%">simple three-step triage</prosody>
for any query that touches organisation structures or security in Workday.
<break time="200ms"/>
By the end of this, you'll know exactly which questions to ask first —
<break time="150ms"/>
and you'll stop wasting time solving the wrong problem.</p>

<p><prosody rate="105%">Let's get into it.</prosody></p>
</speak>"""),

    ("step1", """<speak>
<p><prosody rate="90%">Step one:</prosody>
<break time="300ms"/>
identify the structure type.</p>

<p>Workday isn't one organisation structure —
<break time="150ms"/>
it's several <prosody rate="95%">running in parallel.</prosody>
<break time="250ms"/>
And the fix for a problem in one
looks nothing like the fix in another.</p>

<p>You've got five main types to think about.
<break time="400ms"/></p>

<p><prosody rate="92%">First</prosody> — the supervisory org.
<break time="200ms"/>
That's your management hierarchy:
who reports to who, how the org chart looks,
who a manager's direct reports are.
<break time="350ms"/></p>

<p><prosody rate="92%">Second</prosody> — cost centres.
<break time="150ms"/>
Financial tracking, budget coding, GL assignments.
<break time="350ms"/></p>

<p><prosody rate="92%">Third</prosody> — company or legal entity.
<break time="150ms"/>
The legal structure of the organisation across jurisdictions.
<break time="350ms"/></p>

<p><prosody rate="92%">Fourth</prosody> — custom orgs.
<break time="200ms"/>
These are flexible — regions, business units, functions, matrix structures.
<break time="150ms"/>
Workday lets you configure them for almost anything.
<break time="350ms"/></p>

<p>And <prosody rate="92%">fifth</prosody> — location hierarchy.
<break time="150ms"/>
Offices, sites, countries, territories.
<break time="400ms"/></p>

<p>Before you do anything else on a query,
<break time="150ms"/>
confirm which of these you're actually dealing with.
<break time="250ms"/>
It sounds obvious,
but a lot of time gets lost because people jump straight to a fix
before they've established this.</p>
</speak>"""),

    ("step2", """<speak>
<p><prosody rate="90%">Step two:</prosody>
<break time="300ms"/>
understand what the query is actually about.</p>

<p>Once you know the structure type,
you need to understand the <prosody rate="93%">nature of the problem</prosody> —
<break time="200ms"/>
because there are two very different categories,
and they point in completely different directions.
<break time="400ms"/></p>

<p>The first category is <prosody rate="90%">structural.</prosody>
<break time="250ms"/>
The query is about how something is set up —
<break time="150ms"/>
a worker is in the wrong part of the hierarchy,
a cost centre is rolling up incorrectly,
a manager has too many direct reports,
or the org chart just doesn't look right.
<break time="200ms"/>
These are configuration questions.
<break time="150ms"/>
The answer lives in the structure itself.
<break time="400ms"/></p>

<p>The second category is <prosody rate="90%">access.</prosody>
<break time="250ms"/>
The query is about who can see or act on something —
<break time="150ms"/>
a user can't view data they should have access to,
a manager isn't receiving approval tasks,
a business process is routing to the wrong person.
<break time="250ms"/>
These <prosody rate="95%">feel</prosody> like org questions sometimes,
but they're not.
<break time="150ms"/>
They're security questions.
<break time="400ms"/></p>

<p>The key insight is this:
<break time="300ms"/>
<prosody rate="88%">the symptoms can look identical.</prosody>
<break time="350ms"/>
My manager can't see their team —
<break time="200ms"/>
could be either.
<break time="300ms"/>
You have to ask —
<break time="200ms"/>
is the manager in the wrong place in the structure?
<break time="200ms"/>
Or are they in the right place,
but their security role isn't scoped correctly?
<break time="250ms"/>
<prosody rate="92%">Those are different fixes.</prosody></p>
</speak>"""),

    ("step3a", """<speak>
<p><prosody rate="90%">Step three:</prosody>
<break time="300ms"/>
triage to the resolution path.</p>

<p>Once you've got structure type and query purpose,
the route forward is clear.
<break time="250ms"/>
There are three resolution buckets.
<break time="500ms"/></p>

<p><prosody rate="90%">Bucket one:</prosody>
<break time="250ms"/>
org structure change.
<break time="300ms"/>
This is where you're correcting <prosody rate="93%">how something is configured.</prosody>
<break time="200ms"/>
In Workday, that usually means Change Organisation Assignments —
<break time="150ms"/>
moving a worker or position to the right supervisory org,
cost centre, or custom org node.
<break time="200ms"/>
Or it means editing a position directly,
or correcting a hierarchy at the admin level.
<break time="300ms"/>
You're changing <prosody rate="88%">where something sits.</prosody></p>
</speak>"""),

    ("step3b", """<speak>
<p><prosody rate="90%">Bucket two:</prosody>
<break time="250ms"/>
security assignment.
<break time="300ms"/>
This is where you're correcting <prosody rate="93%">who has access to what.</prosody>
<break time="200ms"/>
You're looking at security role assignments,
checking whether the role is scoped to the right organisational segment,
and verifying that business process routing steps are pointing at the right role.
<break time="300ms"/>
Workday's <prosody rate="92%">View Security for Securable Item</prosody> task
is your best friend here —
<break time="150ms"/>
it tells you exactly what's controlling access to any given item.
<break time="300ms"/>
You're changing <prosody rate="88%">who can see or act on something.</prosody></p>
</speak>"""),

    ("step3c", """<speak>
<p><prosody rate="90%">Bucket three:</prosody>
<break time="250ms"/>
both.
<break time="350ms"/>
This one comes up most often with custom orgs.
<break time="250ms"/>
Because custom orgs are frequently used for <prosody rate="93%">two things at once</prosody> —
<break time="150ms"/>
as an organisational grouping,
and as the basis for a security constraint.
<break time="300ms"/>
So if access is wrong
and the worker is also in the wrong custom org node,
<break time="200ms"/>
you need to fix the structure first,
then revisit the security scope.
<break time="250ms"/>
Doing it in the wrong order
<break time="150ms"/>
will just confuse things.</p>
</speak>"""),

    ("outro", """<speak>
<p>So —
<break time="300ms"/>
three steps.
<break time="350ms"/>
Identify the structure type.
<break time="300ms"/>
Understand whether it's a structural issue or an access issue.
<break time="300ms"/>
Then route to the right fix.
<break time="400ms"/></p>

<p>It takes about thirty seconds when you're used to it,
<break time="150ms"/>
and it'll save you from the single most common time sink in Workday support:
<break time="200ms"/>
<prosody rate="88%">solving the wrong problem confidently.</prosody>
<break time="400ms"/></p>

<p>That's it for today.
<break time="250ms"/>
If this was useful,
pass it on to someone on your team who's dealing with Workday queries —
<break time="150ms"/>
it might just save them an afternoon.</p>
</speak>"""),
]

# ── Slide assignments per narration segment ────────────────────────────────────
def build_slides():
    return {
        "intro":  slide_intro(),
        "step1":  slide_step(1, "Identify the Structure Type", [
            "Supervisory org  —  management hierarchy & org chart",
            "Cost centres  —  financial tracking, GL assignments",
            "Company / legal entity  —  across jurisdictions",
            "Custom orgs  —  regions, business units, matrix structures",
            "Location hierarchy  —  offices, sites, countries",
        ], STEP_COL[1]),
        "step2":  slide_step(2, "Understand the Nature of the Problem", [
            "Structural  —  how something is configured (wrong hierarchy,\n"
            "  incorrect roll-up, wrong reporting line)",
            "Access  —  who can see or act on something (missing\n"
            "  approval tasks, wrong BP routing, invisible data)",
            "Key insight: identical symptoms, different root causes.",
            'Ask: wrong place in structure,  OR  wrong security scope?',
        ], STEP_COL[2]),
        "step3a": slide_bucket(3, 1, "Org Structure Change",
            "Move a worker or position via Change Organisation Assignments. "
            "Edit a position directly or correct the hierarchy at admin level. "
            "You are changing WHERE something sits.",
            STEP_COL[3], (100, 180, 255)),
        "step3b": slide_bucket(3, 2, "Security Assignment",
            "Review security role assignments and organisational segment scoping. "
            "Verify business process routing steps target the correct role. "
            "Use 'View Security for Securable Item' to trace what controls access. "
            "You are changing WHO can see or act on something.",
            STEP_COL[3], (100, 220, 140)),
        "step3c": slide_bucket(3, 3, "Both — Fix Structure First",
            "Custom orgs often serve dual purpose: organisational grouping AND "
            "security constraint basis. "
            "If both are wrong, fix the org structure first, then re-check "
            "security scope. Wrong order = confusion.",
            STEP_COL[3], (255, 180, 80)),
        "outro":  slide_outro(),
    }

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Generating narration audio…")
    audio_clips = {}
    for key, ssml in NARRATION:
        wav = AUDIO_DIR / f"{key}.wav"
        if not wav.exists():
            raw = AUDIO_DIR / f"{key}_raw.wav"
            # en-gb-x-rp = Received Pronunciation, -m = SSML mode
            subprocess.run(
                ["espeak-ng", "-v", "en-gb-x-rp", "-s", "148", "-p", "54",
                 "-g", "5", "-m", "-w", str(raw), ssml],
                check=True, capture_output=True,
            )
            # Warm up with sox: bass boost, light reverb, normalise
            subprocess.run(
                ["sox", str(raw), str(wav),
                 "bass", "+5",
                 "treble", "-2",
                 "reverb", "20", "50", "100", "100", "0", "1",
                 "norm", "-1"],
                check=True, capture_output=True,
            )
        audio_clips[key] = AudioFileClip(str(wav))
        print(f"  {key}: {audio_clips[key].duration:.1f}s")

    print("Building slides…")
    slides = build_slides()

    print("Assembling clips…")
    clips = []
    for key, _ in NARRATION:
        audio = audio_clips[key]
        frame = slides[key]
        img_clip = (
            ImageClip(np.array(frame))
            .with_duration(audio.duration)
            .with_audio(audio)
        )
        clips.append(img_clip)

    final = concatenate_videoclips(clips, method="compose")
    print(f"Total duration: {final.duration:.1f}s  ({final.duration/60:.1f} min)")

    print(f"Writing {OUT} …")
    final.write_videofile(
        str(OUT),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )
    print(f"\nDone!  →  {OUT}")

if __name__ == "__main__":
    main()
