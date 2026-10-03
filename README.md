# Santorini, along the rim

A minimal audio walking tour for Saturday 3 October 2026, ashore from Virgin Voyages' *Scarlet Lady* (07:00 to 19:00, tender port). Built for the Shore Thing "Hiking Adventure to Oia": the caldera rim path from Firostefani through Imerovigli, past Skaros Rock and over the Profitis Ilias high point, down into Oia. It's the small sibling of [Rhodes Landfall](https://github.com/RobGruhl/rhodes-landfall).

Two tracks share nine stops, each in a short version (about forty seconds) and a long one (two to three minutes):

- **Rob** (`narration/rob.json`): the volcano, Akrotiri and Atlantis, the Venetian castle on Skaros, pirates and the Aegean's free companies, Assyrtiko, Vinsanto and fava.
- **Jamie** (`narration/jamie.json`): living on a volcano, cave houses and cisterns, who stays and who goes (Cyrene to 1956), two churches under Venetian and Ottoman rule, farming dry ground, chapels, vows and vrykolakas, the captains' wives of Oia, the island today. Rendered steadier and softer.

Stop 1 is for the tender or the coach up from Athinios; stop 8 is for Fira and the cable car, if the day ends there; stop 9, the same in both tracks, is local food and where to have lunch in Oia.

## Build

```
python3 scripts/narrate.py --set rob          # plan: clips, characters, credits left
python3 scripts/narrate.py --set rob --yes    # render missing clips into docs/audio/rob/
python3 scripts/narrate.py --set jamie --yes
python3 scripts/build.py                      # docs/index.html (?as=jamie opens Jamie's track)
python3 scripts/album.py                      # album/<set>/ tagged for Apple Music (gitignored)
```

Narration uses ElevenLabs **Eleven v4** (`eleven_v4`, launched 28 September 2026) on the standard text-to-speech endpoint, voice George. Notes from the docs that shaped `narrate.py`:

- Only Stability and Similarity apply; style, speed and speaker boost are gone.
- SSML `<break>` is disabled. Pauses come from paragraph breaks, ellipses or `[pause]` tags.
- Delivery is set by a bracketed natural-language tag, which the script prepends per set so the text on the page stays clean.
- Greek names are swapped for IPA between slashes at render time (`SAY` in `narrate.py`). `research/pron/plain.mp3` and `ipa.mp3` are the ear check.
- Until 12 October 2026, v4 bills about 0.1 credit per character (a launch promotion); after that it's 1 credit per character.

The key is read from `$ELEVENLABS_API_KEY`, the Keychain, `~/.config/toolbelt/elevenlabs.env`, or `~/Projects/hello-elevenlabs/.env`. Every clip is logged to `~/.local/state/agent-voice/audit.log`.
