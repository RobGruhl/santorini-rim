"""Tag the narration clips as two Apple Music albums (Rob, Jamie) into album/ (gitignored).

Disc 1 is the long versions, disc 2 the short ones, in stop order, with a cover.
Run: python3 scripts/album.py   (needs ffmpeg and Pillow). Drag each folder into Music, sync the phone.
"""
import json, os, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS, OUT = os.path.join(ROOT, 'docs'), os.path.join(ROOT, 'album')
NAMES = {'rob': 'Rob', 'jamie': 'Jamie'}
SERIF_B = '/System/Library/Fonts/Supplemental/Georgia Bold.ttf'
SERIF = '/System/Library/Fonts/Supplemental/Georgia.ttf'


def cover(path, who):
    s = 1400
    im = Image.new('RGB', (s, s), '#2B5D8A'); d = ImageDraw.Draw(im)
    d.text((s / 2, s * .42), 'Santorini', font=ImageFont.truetype(SERIF_B, 220), fill='#FAF8F3', anchor='mm')
    d.text((s / 2, s * .56), 'along the rim', font=ImageFont.truetype(SERIF, 110), fill='#FAF8F3', anchor='mm')
    d.line([(s * .3, s * .67), (s * .7, s * .67)], fill='#BFD6EA', width=8)
    d.text((s / 2, s * .75), f"{who}'s track  ·  3 October 2026", font=ImageFont.truetype(SERIF, 64), fill='#DCE8F2', anchor='mm')
    im.save(path, quality=92)


for st, who in NAMES.items():
    mf = os.path.join(DOCS, 'audio', st, 'manifest.json')
    if not os.path.exists(mf):
        continue
    clips = sorted(json.load(open(mf))['clips'].values(), key=lambda c: c['n'])
    dest = os.path.join(OUT, st); os.makedirs(dest, exist_ok=True)
    art = os.path.join(dest, 'cover.jpg'); cover(art, who)
    for disc, length in ((1, 'long'), (2, 'short')):
        for c in clips:
            if length not in c:
                continue
            suffix = ' (short)' if length == 'short' else ''
            out = os.path.join(dest, f"{disc}-{c['n']:02d} {c['title']}{suffix}.mp3")
            meta = {'title': f"{c['n']:02d} {c['title']}{suffix}", 'album': f'Santorini · {who}',
                    'artist': f'{who} · Santorini', 'album_artist': 'Santorini', 'genre': 'Spoken Word',
                    'date': '2026', 'track': f"{c['n']}/{len(clips)}", 'disc': f'{disc}/2'}
            cmd = ['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(DOCS, c[length]['file']), '-i', art,
                   '-map', '0:a', '-map', '1:v', '-c', 'copy', '-id3v2_version', '3',
                   '-metadata:s:v', 'title=Album cover', '-metadata:s:v', 'comment=Cover (front)']
            for k, v in meta.items():
                cmd += ['-metadata', f'{k}={v}']
            subprocess.run(cmd + [out], check=True)
    print(st, len(os.listdir(dest)) - 1, 'tracks ->', dest)
