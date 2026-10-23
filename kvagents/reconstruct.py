"""Reconstruct: turn tracking around a moment into a small 3D scene (JSON).

This step is NOT part of the model pipeline and it never writes match facts.
It only reshapes the synthetic tracking of one goal so a viewer can replay it.

Two scene kinds:
  decoy  an attacker runs away from the play, his marker follows, the pass goes into the space he left
  scan   the player who will receive the ball looks around before it arrives, then plays the pass he chose

The synthetic tracking has no head direction and no deliberate decoy runs, so both are
authored here, within physical limits (speed cap, no teleporting), and every scene says
so ("illustrative reconstruction"). Ball events, times and score are never changed.

CLI:  python -m kvagents.reconstruct MATCH_DIR TRACKING_JSONL --out DIR
(the scene list is SCENES below; ids are the same as in the demo output)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HZ = 5
DT = 1000 // HZ
L, W = 105.0, 68.0
V_MARKER = 8.0   # m/s cap for a defender being pulled along
V_DECOY = 7.5
FLIGHT_TYPES = ("pass", "throw_in", "corner", "free_kick", "goal_kick", "shot", "penalty")  # eventgen.schema PASS_LIKE + SHOT_LIKE

# (match_id, moment_id, kind, shot_seq, t0_ms, t1_ms, extra)
SCENES = [
    ("m00007-lev-hov", "M008", "decoy", 1259, 4812000, 4822600, {}),
    ("m00007-lev-hov", "M011", "scan", 1362, 5217200, 5236000,
     {"scanner": "T01-P18", "recv_seq": 1355, "next_seq": 1357}),
]

CAPTIONS = {
    "decoy": {
        "run": {"en": "#{n} starts a diagonal run, away from the ball",
                "es": "El #{n} lanza una carrera en diagonal, lejos del balón",
                "ar": "اللاعب رقم {n} ينطلق في جري قطري بعيدًا عن الكرة"},
        "follow": {"en": "His marker follows him",
                   "es": "Su marcador lo sigue",
                   "ar": "المدافع الذي يراقبه يتبعه"},
        "pass": {"en": "The pass goes into the space he left",
                 "es": "El pase va al espacio que dejó",
                 "ar": "تذهب التمريرة إلى المساحة التي تركها"},
        "shot": {"en": "#{n} shoots: goal",
                 "es": "El #{n} remata: gol",
                 "ar": "اللاعب رقم {n} يسدد: هدف"},
    },
    "scan": {
        "scan": {"en": "#{n} scans the pitch before the ball reaches him",
                 "es": "El #{n} mira a su alrededor antes de recibir el balón",
                 "ar": "اللاعب رقم {n} يتفحص الملعب قبل وصول الكرة إليه"},
        "pick": {"en": "He has picked #{t}",
                 "es": "Ya eligió al #{t}",
                 "ar": "لقد اختار اللاعب رقم {t}"},
        "pass": {"en": "One touch, pass to #{t}",
                 "es": "Un toque y pase al #{t}",
                 "ar": "لمسة واحدة وتمريرة إلى اللاعب رقم {t}"},
        "shot": {"en": "The shot is saved",
                 "es": "El remate es parado",
                 "ar": "الحارس يتصدى للتسديدة"},
        "goal": {"en": "#{n} scores from the rebound play",
                 "es": "El #{n} marca en la jugada siguiente",
                 "ar": "اللاعب رقم {n} يسجل في اللعبة التالية"},
    },
}


# ---------------------------------------------------------------- helpers
def _smooth(u: float) -> float:
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    return u * u * (3 - 2 * u)


def _lerp(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def _step_toward(cur, want, vmax):
    dx, dy = want[0] - cur[0], want[1] - cur[1]
    d = math.hypot(dx, dy)
    lim = vmax * DT / 1000.0
    if d <= lim or d == 0:
        return want
    return (cur[0] + dx / d * lim, cur[1] + dy / d * lim)


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _read_jsonl(path: Path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _read_window(tracking: Path, t0: int, t1: int):
    header, frames = None, []
    with open(tracking, encoding="utf-8") as f:
        for line in f:
            if line.startswith('{"type":"header"'):
                header = json.loads(line)
                continue
            # cheap pre-filter on time before parsing
            d = json.loads(line)
            if d["type"] != "frame":
                continue
            if t0 <= d["t"] <= t1:
                frames.append(d)
            elif d["t"] > t1:
                break
    return header, frames


# ---------------------------------------------------------------- builder
def build_scene(match_dir: Path, tracking: Path, moment_id: str, kind: str, shot_seq: int,
                t0: int, t1: int, extra: dict) -> dict:
    match = json.load(open(match_dir / "match.json", encoding="utf-8"))
    teams = {t["team_id"]: t for t in json.load(open(match_dir / "teams.json", encoding="utf-8"))["teams"]}
    events = _read_jsonl(match_dir / "events.jsonl")
    by_seq = {e["seq"]: e for e in events}
    shot = by_seq[shot_seq]
    att = shot["team_id"]
    de = next(t for t in teams if t != att)
    direction = next(p["attacking_direction"][att] for p in match["periods"] if p["period"] == shot["period"])
    flip = direction == "right_to_left"

    header, raw = _read_window(tracking, t0, t1)
    if not raw:
        raise SystemExit(f"no tracking frames in {t0}..{t1}")
    pid_of = {p["index"]: p["player_id"] for p in header["players"]}
    team_of = {p["player_id"]: p["team_id"] for p in header["players"]}
    num_of = {}
    pos_of = {}
    for t in teams.values():
        for p in t["players"]:
            num_of[p["player_id"]] = p["jersey_number"]
            pos_of[p["player_id"]] = p["position"]

    times = [f["t"] for f in raw]
    n = len(times)

    def fx(x, y):
        return (L - x, W - y) if flip else (x, y)

    ball = [fx(*f["ball"]) for f in raw]
    track: dict[str, list[tuple[float, float]]] = {}
    last: dict[str, tuple[float, float]] = {}
    for f in raw:
        seen = {}
        for i, x, y in f["p"]:
            seen[pid_of[i]] = fx(x, y)
        for pid in set(seen) | set(last):
            if pid in seen:
                last[pid] = seen[pid]
            track.setdefault(pid, []).append(last[pid])
    # a player who is missing before his first frame: pad at the front
    for pid, lst in track.items():
        if len(lst) < n:
            track[pid] = [lst[0]] * (n - len(lst)) + lst
    orig = {pid: list(v) for pid, v in track.items()}

    def idx_at(t):
        return min(range(n), key=lambda k: abs(times[k] - t))

    # --- flights (pass / shot) inside the window
    flights = []
    for e in events:
        if e["type"] in FLIGHT_TYPES and t0 <= e["match_clock_ms"] <= t1 and "end_x" in e:
            ex, ey = fx(e["end_x"], e["end_y"])
            k0 = idx_at(e["match_clock_ms"])
            k1 = next((k for k in range(k0, n) if math.dist(ball[k], (ex, ey)) < 2.0 and k > k0), min(k0 + 3, n - 1))
            sx, sy = fx(e["x"], e["y"])
            flights.append({"seq": e["seq"], "type": e["type"], "t0": times[k0], "t1": times[k1],
                            "len": round(math.hypot(ex - sx, ey - sy), 1), "from": e["player_id"],
                            "to": e.get("receiver_id") or None, "outcome": e.get("outcome")})
    marks: dict[str, str] = {}
    beats = []
    stats = {}
    scan = None

    scorer = shot["player_id"]
    t_shot = shot["match_clock_ms"]
    num = num_of

    if kind == "decoy":
        assist = by_seq.get(next((s for s, e in by_seq.items() if e["event_id"] == shot.get("assist_event_id")), -1))
        passer = assist["player_id"]
        t_pass = assist["match_clock_ms"]
        fl = next(f for f in flights if f["seq"] == assist["seq"])
        k_arr = idx_at(fl["t1"])
        k_pass = idx_at(t_pass)
        run_start = t_pass - 3200
        k_run = idx_at(run_start)
        rec_pos = orig[scorer][k_arr]
        defenders = [p for p in track if team_of[p] == de and pos_of[p] != "GK"]
        marker = min(defenders, key=lambda p: math.dist(orig[p][k_arr], rec_pos))
        mates = [p for p in track if team_of[p] == att and p not in (passer, scorer) and pos_of[p] != "GK"]
        decoy = min(mates, key=lambda p: math.dist(orig[p][k_run], orig[marker][k_run]))
        d0 = orig[decoy][k_run]
        # the run goes towards the passer's side, so the marker is pulled away from the lane the cutback uses
        side = 1.0 if orig[passer][k_pass][1] >= rec_pos[1] else -1.0
        target = (_clamp(d0[0] + 13.0, 40, L - 11), _clamp(rec_pos[1] + side * 21.0, 5, W - 5))
        k_end = min(n - 1, k_pass + 6)
        dur = max(times[k_end] - times[k_run], 1)
        # decoy path
        new = list(orig[decoy])
        cur = d0
        for k in range(k_run, n):
            u = _smooth((times[k] - times[k_run]) / dur)
            want = _lerp(d0, target, u) if k <= k_end else (
                target[0] + (orig[decoy][k][0] - orig[decoy][k_end][0]),
                target[1] + (orig[decoy][k][1] - orig[decoy][k_end][1]))
            cur = _step_toward(cur, want, V_DECOY)
            new[k] = cur
        track[decoy] = new
        # marker is pulled along while the run lasts, then lets go
        mk = list(orig[marker])
        cur = mk[k_run]
        for k in range(k_run, n):
            w_follow = _smooth((times[k] - run_start - 500) / 1200)
            if times[k] > t_pass:
                w_follow *= 1.0 - _smooth((times[k] - t_pass) / 1800)
            follow = (new[k][0] + 1.6, new[k][1])
            want = _lerp(orig[marker][k], follow, w_follow)
            cur = _step_toward(cur, want, V_MARKER)
            mk[k] = cur
        track[marker] = mk
        k_shot = idx_at(t_shot)
        gap_with = min(math.dist(track[p][k_shot], track[scorer][k_shot]) for p in defenders)
        gap_without = min(math.dist(orig[p][k_shot], orig[scorer][k_shot]) for p in defenders)
        marker_gap_pass = math.dist(track[marker][k_arr], track[scorer][k_arr])
        marker_gap_orig = math.dist(orig[marker][k_arr], orig[scorer][k_arr])
        stats = {"nearest_defender_to_scorer_m": round(gap_with, 1),
                 "same_without_run_m": round(gap_without, 1),
                 "marker_to_scorer_at_pass_m": round(marker_gap_pass, 1),
                 "marker_to_scorer_without_run_m": round(marker_gap_orig, 1)}
        marks = {"decoy": decoy, "marker": marker, "passer": passer, "scorer": scorer}
        beats = [
            {"t": run_start + 200, "key": "run", "n": num[decoy]},
            {"t": run_start + 1700, "key": "follow"},
            {"t": t_pass, "key": "pass"},
            {"t": t_shot - 200, "key": "shot", "n": num[scorer]},
        ]
    elif kind == "scan":
        scanner = extra["scanner"]
        recv = by_seq[extra["recv_seq"]]
        nxt = by_seq[extra["next_seq"]]
        fl = next(f for f in flights if f["seq"] == recv["seq"])
        t_send, t_arr, t_pass = fl["t0"], fl["t1"], nxt["match_clock_ms"]
        target_pid = nxt["receiver_id"]
        k_send, k_arr = idx_at(t_send), idx_at(t_arr)
        opp = lambda k: min((p for p in track if team_of[p] == de), key=lambda p: math.dist(track[p][k], track[scanner][k]))
        # two teammates the scanner could play to, one each side, not the picked target
        mates = [p for p in track if team_of[p] == att and p not in (scanner, target_pid) and pos_of[p] != "GK"]
        ks = k_send
        s = track[scanner][ks]
        ahead = sorted(mates, key=lambda p: math.dist(track[p][ks], s))
        optA = next(p for p in ahead if track[p][ks][1] >= s[1])
        optB = next((p for p in ahead if track[p][ks][1] < s[1] and p != optA), ahead[-1])
        span = max(t_arr - t_send, 600)
        looks = [  # (time, who/what is looked at)
            (t_send, "ball"),
            (t_send + 0.22 * span, opp(ks)),
            (t_send + 0.47 * span, optA),
            (t_send + 0.72 * span, optB),
            (t_arr - 0.02 * span, "ball"),
            (t_pass - 650, target_pid),
        ]
        keys = []
        for t, who in looks:
            k = idx_at(int(t))
            me = track[scanner][k]
            tp = ball[k] if who == "ball" else track[who][k]
            keys.append({"t": int(t), "yaw": round(math.atan2(tp[1] - me[1], tp[0] - me[0]), 3),
                         "look": None if who == "ball" else who})
        scan = {"pid": scanner, "keys": keys, "target": target_pid, "t_send": t_send, "t_arrive": t_arr, "t_pass": t_pass,
                "options": [optA, optB]}
        marks = {"scanner": scanner, "target": target_pid, "scorer": scorer, "passer": recv["player_id"]}
        goal_t = t_shot
        saved_shot = next((e for e in events if e["type"] == "shot" and e["seq"] > nxt["seq"] and e["seq"] < shot_seq), None)
        beats = [
            {"t": t_send, "key": "scan", "n": num[scanner]},
            {"t": t_pass - 500, "key": "pick", "t_n": num[target_pid]},
            {"t": t_pass, "key": "pass", "t_n": num[target_pid]},
        ]
        if saved_shot:
            beats.append({"t": saved_shot["match_clock_ms"], "key": "shot"})
        beats.append({"t": goal_t - 300, "key": "goal", "n": num[scorer]})
    else:
        raise SystemExit(f"unknown scene kind {kind}")

    # --- facing for everybody, from smoothed velocity (ball side when standing)
    yaw: dict[str, list[float]] = {}
    for pid, path in track.items():
        ys = []
        prev = 0.0 if team_of[pid] == att else math.pi
        for k in range(n):
            a, b = path[max(k - 2, 0)], path[min(k + 2, n - 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            sp = math.hypot(dx, dy) / ((min(k + 2, n - 1) - max(k - 2, 0)) * DT / 1000.0 or 1)
            if sp > 0.8:
                tgt = math.atan2(dy, dx)
            else:
                tgt = math.atan2(ball[k][1] - path[k][1], ball[k][0] - path[k][0])
            d = (tgt - prev + math.pi) % (2 * math.pi) - math.pi
            prev = prev + _clamp(d, -0.9, 0.9)
            ys.append(round(prev, 2))
        yaw[pid] = ys

    ordered = [p for p in sorted(track, key=lambda p: (team_of[p] != att, num_of.get(p, 99)))]
    ta, td = teams[att], teams[de]
    return {
        "scene_id": f"{match['match_id']}-{moment_id}-{kind}",
        "match_id": match["match_id"], "moment_id": moment_id, "kind": kind,
        "label": "Illustrative reconstruction from synthetic tracking",
        "hz": HZ, "pitch": [L, W], "t": times,
        "minute": round(t_shot / 60000),
        "teams": {"att": {"id": att, "names": ta["name_i18n"], "color": ta["primary_color"], "short": ta["short_name"]},
                  "def": {"id": de, "names": td["name_i18n"], "color": td["primary_color"], "short": td["short_name"]}},
        "players": [{"id": p, "n": num_of[p], "side": "att" if team_of[p] == att else "def", "pos": pos_of[p]} for p in ordered],
        "ball": [[round(x, 2), round(y, 2)] for x, y in ball],
        "xy": {p: [[round(x, 2), round(y, 2)] for x, y in track[p]] for p in ordered},
        "yaw": {p: yaw[p] for p in ordered},
        "flights": flights, "marks": marks, "scan": scan, "stats": stats, "beats": beats,
        "captions": CAPTIONS[kind],
        "shot_t": t_shot,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("match_dir")
    ap.add_argument("tracking")
    ap.add_argument("--out", default="demo/scenes")
    a = ap.parse_args(argv)
    mdir = Path(a.match_dir)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mid = json.load(open(mdir / "match.json", encoding="utf-8"))["match_id"]
    for (m, mom, kind, seq, t0, t1, extra) in SCENES:
        if m != mid:
            continue
        scene = build_scene(mdir, Path(a.tracking), mom, kind, seq, t0, t1, extra)
        p = out / f"{scene['scene_id']}.json"
        p.write_text(json.dumps(scene, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(p, p.stat().st_size, "bytes", scene["stats"] or "")


if __name__ == "__main__":
    main()
