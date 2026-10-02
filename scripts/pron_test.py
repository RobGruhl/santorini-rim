"""Render one sentence of Santorini place names twice, plain and with IPA, for an ear check."""
import json, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
import narrate as n
from pathlib import Path
OUT = n.ROOT / "research" / "pron"
plain = ("From Fira the path runs north through Firostefani to Imerovigli and the rock of Skaros, "
         "then on to Oia. Across the water lie Nea Kameni, Thirasia and Akrotiri, and the old name for the whole island is Thera.")
ipa = (plain.replace("Firostefani", "/fiɾostɛˈfani/").replace("Imerovigli", "/imɛɾoˈviʎi/").replace("Skaros", "/ˈskaɾos/")
       .replace("Oia", "/ˈia/").replace("Nea Kameni", "/ˈnɛa kaˈmɛni/").replace("Thirasia", "/θiɾaˈsia/")
       .replace("Akrotiri", "/akɾoˈtiɾi/").replace("Fira", "/ˈfiɾa/").replace("Thera", "/ˈθɪərə/"))
VOICE = "JBFqnCBsd6RMkjVDRZzb"  # George
key = n.api_key()
vid = VOICE
for name, text in (("plain", plain), ("ipa", ipa)):
    text = f"{n.DIRECTION["rob"]}\n{text}"
    body = json.dumps({"model_id": n.MODEL, "text": text, "voice_settings": n.SETTINGS["rob"]}).encode()
    audio, h = n.req(key, f"/v1/text-to-speech/{vid}?output_format=mp3_44100_128", body, {"Content-Type": "application/json"})
    (OUT / f"{name}.mp3").write_bytes(audio)
    n.audit(f"[agent-voice audit] verb=pron-test project=santorini voice={vid} model={n.MODEL} chars={len(text)} credits={h.get('character-cost')}")
    print(name, n.duration_seconds(OUT / f"{name}.mp3"), "s")
