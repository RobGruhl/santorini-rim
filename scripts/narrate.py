#!/usr/bin/env python3
"""Render the Santorini narration with ElevenLabs Eleven v4 into docs/audio/<set>/.

Paid per character. This script never spends without --yes. Without it, it prints the plan:
every clip, its character count, the total, the voice and model, and stops.

Eleven v4 notes (docs checked 2 Oct 2026): only Stability and Similarity apply (no style,
speed or speaker boost); SSML <break> is disabled, so pauses are written as [pause] tags or
ellipses; delivery is steered with a bracketed natural-language tag before the text, which
this script prepends (DIRECTION) so the scripts on the page stay clean. Place names that v4
mispronounces are swapped for IPA between slashes at render time (SAY), never in the scripts.

Key resolution: $ELEVENLABS_API_KEY, the Keychain item ELEVENLABS_API_KEY,
~/.config/toolbelt/elevenlabs.env, then ~/Projects/hello-elevenlabs/.env (where it lives today).
Each clip appends one line to ~/.local/state/agent-voice/audit.log.

Usage:
  python3 scripts/narrate.py --set rob            # plan only
  python3 scripts/narrate.py --set jamie --yes    # render what is missing
  python3 scripts/narrate.py --set rob --stops 1-3 --only short --force --yes
"""
from __future__ import annotations
import argparse, glob, json, os, re, stat, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARR = ROOT / "narration"
AUDIO = ROOT / "docs" / "audio"
SETS = ("rob", "jamie")
MODEL = "eleven_v4"
MAX_RUN_CHARS = 60_000           # per-run ceiling; raising it is a diff, not a flag
MAX_CLIP_CHARS = 6_000           # v4 takes 10,000, but shorter requests hold a steadier read
VOICE_PREFS = ["George", "Daniel", "Brian"]
# Per set: Jamie's read is steadier and softer (sensory sensitivities, as in the Rhodes Colossus extra).
SETTINGS = {"rob": {"stability": 0.55, "similarity_boost": 0.75},
            "jamie": {"stability": 0.7, "similarity_boost": 0.75}}
DIRECTION = {"rob": "[Warm, unhurried walking-tour narration, like a friend who knows the island well]",
             "jamie": "[Calm, gentle, soothing narration, soft and unhurried, warm and even]"}
SAY = {                          # Greek stress via IPA; research/pron/{plain,ipa}.mp3 is the ear check
    "Oia": "/ˈia/", "Fira": "/ˈfiɾa/", "Firostefani": "/fiɾostɛˈfani/", "Imerovigli": "/imɛɾoˈviʎi/",
    "Skaros": "/ˈskaɾos/", "Akrotiri": "/akɾoˈtiɾi/", "Thirasia": "/θiɾaˈsia/", "Kameni": "/kaˈmɛni/",
    "hyposkafa": "/iˈposkafa/", "Theoskepasti": "/θɛoskɛpaˈsti/", "kouloura": "/kuˈluɾa/", "Assyrtiko": "/asiɾˈtiko/",
    "panigyria": "/paniʝiˈɾia/", "vrykolakas": "/vɾiˈkolakas/", "Ammoudi": "/aˈmuði/",
    "Tomatokeftedes": "/tomatoˈcɛftɛðɛs/", "chloro": "/xloˈɾo/", "Melitini": "/mɛliˈtini/", "Pitogyros": "/pitoˈʝiɾos/",
    "Lotza": "/ˈlodza/",
}
AUDIT = Path(os.environ.get("AGENT_VOICE_AUDIT_LOG", Path.home() / ".local/state/agent-voice/audit.log"))


def api_key() -> str:
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if k:
        return k
    if sys.platform == "darwin":
        r = subprocess.run(["security", "find-generic-password", "-s", "ELEVENLABS_API_KEY", "-w"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    for p in (Path.home() / ".config/toolbelt/elevenlabs.env", Path.home() / "Projects/hello-elevenlabs/.env"):
        if p.exists():
            if p.parent.name == "toolbelt" and stat.S_IMODE(p.stat().st_mode) & 0o077:
                sys.exit(f"{p} is group/world readable; chmod 600 it first")
            for line in p.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("No ElevenLabs key found")


def req(key: str, path: str, data: bytes | None = None, headers: dict | None = None):
    h = {"xi-api-key": key}
    if headers:
        h.update(headers)
    r = urllib.request.Request("https://api.elevenlabs.io" + path, data=data, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            return resp.read(), resp.headers
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read()[:400]!r}")


def pick_voice(key: str, want: str | None):
    voices = json.loads(req(key, "/v1/voices")[0])["voices"]
    for cand in ([want] if want else []) + VOICE_PREFS:
        for v in voices:
            if v["name"] == cand or v["name"].split(" - ")[0].strip().lower() == cand.lower():
                return v
    sys.exit("None of the preferred voices are on this account; pass --voice NAME")


def load_stops(narr_set: str):
    stops = []
    for f in sorted(glob.glob(str(NARR / f"{narr_set}*.json"))):
        stops.extend(json.load(open(f)))
    return sorted(stops, key=lambda s: s["n"])


def parse_stops(spec: str | None):
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def spoken(text: str, narr_set: str) -> str:
    """What v4 receives: the direction tag, then the script with IPA swapped in for hard names."""
    for word, ipa in SAY.items():
        text = re.sub(rf"\b{re.escape(word)}\b", ipa, text)
    return f"{DIRECTION[narr_set]}\n{text}"


def duration_seconds(path: Path) -> float | None:
    r = subprocess.run(["afinfo", str(path)], capture_output=True, text=True, timeout=30)
    for line in r.stdout.splitlines():
        if "estimated duration" in line:
            return round(float(line.split(":")[1].split()[0]), 1)
    return None


def audit(line: str):
    AUDIT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(AUDIT, "a") as f:
        f.write(line + "\n")
    os.chmod(AUDIT, 0o600)
    print(line, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=SETS, required=True)
    ap.add_argument("--yes", action="store_true", help="actually spend credits")
    ap.add_argument("--only", choices=["short", "long"])
    ap.add_argument("--stops", help="e.g. 1-3,6")
    ap.add_argument("--voice", help="voice name on the account")
    ap.add_argument("--force", action="store_true", help="re-render clips that already exist")
    a = ap.parse_args()

    out = AUDIO / a.set
    stops = load_stops(a.set)
    want = parse_stops(a.stops)
    jobs = []
    for s in stops:
        if want and s["n"] not in want:
            continue
        for length in [a.only] if a.only else ["short", "long"]:
            text = spoken(s[length].strip(), a.set)
            fn = out / f"{s['n']:02d}-{s['slug']}-{length}.mp3"
            if len(text) > MAX_CLIP_CHARS:
                sys.exit(f"{fn.name}: {len(text)} chars exceeds the {MAX_CLIP_CHARS}-char clip ceiling")
            if fn.exists() and not a.force:
                continue
            jobs.append((s, length, text, fn))
    total = sum(len(j[2]) for j in jobs)
    print(f"set {a.set} | model {MODEL} | {len(jobs)} clips | {total:,} characters")
    for _, _, text, fn in jobs:
        print(f"  {fn.name:40s} {len(text):5d}")
    if total > MAX_RUN_CHARS:
        sys.exit(f"Total {total:,} exceeds the per-run ceiling of {MAX_RUN_CHARS:,}")
    if not jobs:
        return write_manifest(a.set, stops)
    key = api_key()
    voice = pick_voice(key, a.voice)
    sub = json.loads(req(key, "/v1/user/subscription")[0])
    print(f"voice {voice['name']} ({voice['voice_id']}) | credits used {sub.get('character_count'):,} of {sub.get('character_limit'):,}")
    if not a.yes:
        print("\nPlan only. Re-run with --yes to render.")
        return
    out.mkdir(parents=True, exist_ok=True)
    for s, length, text, fn in jobs:
        body = json.dumps({"model_id": MODEL, "text": text, "voice_settings": SETTINGS[a.set]}).encode()
        t0 = time.time()
        audio, hdrs = req(key, f"/v1/text-to-speech/{voice['voice_id']}?output_format=mp3_44100_128", body,
                          {"Content-Type": "application/json", "Accept": "audio/mpeg"})
        fn.write_bytes(audio)
        audit(f"[agent-voice audit] {datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')} "
              f"verb=narrate project=santorini clip={a.set}/{fn.name} voice={voice['voice_id']} model={MODEL} "
              f"chars={len(text)} credits={hdrs.get('character-cost')} bytes={len(audio)} secs={time.time()-t0:.1f}")
    write_manifest(a.set, stops, voice)


def write_manifest(narr_set, stops, voice=None):
    out = AUDIO / narr_set
    mf = out / "manifest.json"
    old = json.load(open(mf)) if mf.exists() else {}
    man = {"set": narr_set, "model": MODEL, "voice": (voice or {}).get("name") or old.get("voice"), "clips": {}}
    for s in stops:
        entry = {}
        for length in ("short", "long"):
            fn = out / f"{s['n']:02d}-{s['slug']}-{length}.mp3"
            if fn.exists():
                entry[length] = {"file": f"audio/{narr_set}/{fn.name}", "sec": duration_seconds(fn)}
        if entry:
            man["clips"][s["slug"]] = {"n": s["n"], "title": s["title"], **entry}
    out.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps(man, indent=1, ensure_ascii=False))
    print(f"manifest: {len(man['clips'])} stops with audio -> {mf}")


if __name__ == "__main__":
    main()
