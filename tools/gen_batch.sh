#!/usr/bin/env bash
# Generate N plain matches (no stories, no tracking) in parallel, then compare to sourced targets.
# usage: tools/gen_batch.sh out/calib 300
set -e
OUT=${1:-out/calib}; N=${2:-40}
rm -rf "$OUT"; mkdir -p "$OUT"
python - "$OUT" "$N" <<'PY'
import sys
from multiprocessing import Pool
from eventgen import generate_match
from eventgen.io import write_match
out, n = sys.argv[1], int(sys.argv[2])
def one(s):
    write_match(generate_match(s, "none"), f"{out}/s{s}")
if __name__ == "__main__":
    with Pool() as p:
        p.map(one, range(1000, 1000 + n), chunksize=4)
PY
python tools/compare_to_targets.py "$OUT"
