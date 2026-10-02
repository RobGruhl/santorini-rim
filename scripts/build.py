#!/usr/bin/env python3
"""Build docs/index.html: both narration sets and their audio manifests baked into one page.

Run from anywhere: python3 scripts/build.py
"""
import glob, hashlib, html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def load(narr_set):
    stops = []
    for f in sorted(glob.glob(str(ROOT / "narration" / f"{narr_set}*.json"))):
        stops.extend(json.load(open(f)))
    mf = DOCS / "audio" / narr_set / "manifest.json"
    clips = json.load(open(mf))["clips"] if mf.exists() else {}
    for s in sorted(stops, key=lambda s: s["n"]):
        s["audio"] = clips.get(s["slug"], {})
    return sorted(stops, key=lambda s: s["n"])


def strip_tags(text):
    """Audio tags like [pause] are for the voice, not the page."""
    return re.sub(r"\s*\[[^\]]+\]\s*", " ", text).replace("  ", " ").strip()


def stop_html(s):
    paras = lambda t: "".join(f"<p>{html.escape(p.strip())}</p>" for p in strip_tags(t).split("\n") if p.strip())
    players = ""
    for length in ("long", "short"):
        a = s["audio"].get(length)
        if a:
            mins = f"{int(a['sec'] // 60)}:{int(a['sec'] % 60):02d}" if a.get("sec") else ""
            players += (f'<div class="clip"><span>{length.title()} <small>{mins}</small></span>'
                        f'<audio controls preload="none" src="{a["file"]}"></audio></div>')
    where = f'<p class="where">{html.escape(s["where"])}</p>' if s.get("where") else ""
    return (f'<section class="stop" id="{s["slug"]}"><h2><span class="n">{s["n"]}</span>{html.escape(s["title"])}</h2>'
            f'{where}{players}<details><summary>Read the long version</summary>{paras(s["long"])}</details>'
            f'<details><summary>Read the short version</summary>{paras(s["short"])}</details></section>')


def main():
    tpl = (ROOT / "scripts" / "page.html").read_text()
    body = ""
    for who in ("rob", "jamie"):
        stops = load(who)
        body += f'<div class="track" data-set="{who}">' + "".join(stop_html(s) for s in stops) + "</div>"
    out = tpl.replace("<!--TRACKS-->", body)
    (DOCS / "index.html").write_text(out)
    # stamp the service worker so phones pick up a rebuilt page on next open
    version = hashlib.sha1(out.encode()).hexdigest()[:10]
    (DOCS / "sw.js").write_text((ROOT / "scripts" / "sw.js").read_text().replace("__VERSION__", version))
    print("wrote", DOCS / "index.html", f"{len(out)//1024} KB", "| sw", version)


if __name__ == "__main__":
    main()
