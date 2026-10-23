# 3D replay

The match desk page has a **3D replay** tab. It rebuilds two moments of the demo match in 3D and plays them next to the fan text written for the same moment.

| Moment | What you see | Camera |
| --- | --- | --- |
| 77' goal (M008) | One attacker runs away from the play, his marker follows him, the cutback goes into the space they left | Tactical, Behind play |
| 84' goal build-up (M011) | The player who will receive the ball looks around (opponent, two teammates, the ball), then plays the pass he had already chosen | Tactical, Behind play, **Player view** (his eyes) |

## What is real and what is authored

* Real (generated): who passed, who shot, the minute, the score, the ball positions. These come from `events.jsonl`.
* Synthetic: the positions of all 22 players at 5 Hz, from `eventgen/tracking.py`. They are built from the events.
* Authored on top, by `kvagents/reconstruct.py`: the decoy run and the marker being pulled along (speed caps 7.5 and 8 m/s, no teleporting), and the head direction of the scanning player. The tracking has neither. Every scene carries the label "Illustrative reconstruction" and the page says it does not show how real players move.

## Files

* `kvagents/reconstruct.py` builds `demo/scenes/*.json` from a match folder and its `tracking.jsonl`. Not part of the model pipeline. The scene list is `SCENES` at the top of the file.
* `site/src/scene3d.js` is the player (three.js). `bash tools/build_scene3d.sh` bundles it into `site/vendor/scene3d.js` (committed, so Pages needs no node).
* `tools/build_site.py` inlines the bundle and the scenes into `site/index.html`.

## Rebuild

```
python -m eventgen.cli generate --seed 7 --stories config/stories.example.yaml --out /tmp/a      # writes tracking.jsonl too
python -m kvagents.reconstruct /tmp/a /tmp/a/tracking.jsonl --out demo/scenes
python tools/build_site.py
```

The Narrate workflow does the first two steps for both demo matches.

## Limits

* The 3D captions in Arabic and Spanish are short templates. The Arabic ones need a native reader.
* The tracking players drift to formation slots, so marking is loose. The decoy scene shows an authored run, not a detected one.
* Two moments only. To add one, add a row to `SCENES`.
