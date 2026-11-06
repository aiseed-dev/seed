#!/usr/bin/env python3
"""履歴全体から徳島の畑の範囲の座標らしい数を集め、git-filter-repo の置き換えの表を書く。

見つけた値は標準出力に一つも出さない。--out のファイル（既定 ~/座標の置き換え.txt、
repo の外、作者だけが開く）にだけ書く。標準出力は件数だけ。

使い方:
    .venv/bin/python scripts/座標の履歴/1-表を作る.py [--repo PATH] [--out PATH]

範囲: 緯度 33.9〜34.3、経度 134.0〜134.6、小数 2 桁以上。
除く: 見本 34.0512・134.2534、渕名（公の地質図の点）34.0193・134.1248、
      それらを短くした形（34.05、134.253 の類。本物と見分けられないので触らない）。
表の形: regex:(?<![\\d.])<値>(?![\\d]|\\.\\d)==><見本>
  （前後に数字が続く物を巻き込まないため。filter-repo の --replace-text と
   --replace-message の両方にそのまま渡せる）
"""
import argparse
import os
import re
import subprocess
import sys

LAT_SAMPLE = "34.0512"
LON_SAMPLE = "134.2534"
KEEP = ["34.0512", "134.2534", "34.0193", "134.1248"]
LAT_RANGE = (33.9, 34.3)
LON_RANGE = (134.0, 134.6)
TOO_MANY = 20

NUM = re.compile(rb"(?<![\d.])(\d{2,3}\.\d{2,})(?![\d]|\.\d)")


def kept(v: str) -> bool:
    for k in KEEP:
        if v == k:
            return True
        # 見本を短くした形（小数 2 桁以上）
        if k.startswith(v) and len(v.split(".")[1]) >= 2:
            return True
    return False


def classify(v: str):
    f = float(v)
    if LAT_RANGE[0] <= f <= LAT_RANGE[1]:
        return "lat"
    if LON_RANGE[0] <= f <= LON_RANGE[1]:
        return "lon"
    return None


def git(repo, *args, **kw):
    return subprocess.run(["git", "-C", repo, *args], check=True,
                          stdout=subprocess.PIPE, **kw).stdout


BLOB_PATH = {}


def blobs(repo):
    out = git(repo, "rev-list", "--all", "--objects")
    for line in out.splitlines():
        parts = line.split(b" ", 1)
        if len(parts) == 2:
            BLOB_PATH.setdefault(parts[0], parts[1].decode(errors="replace"))
    shas = sorted({line.split(b" ", 1)[0] for line in out.splitlines() if line})
    inp = b"\n".join(shas) + b"\n"
    p = subprocess.run(["git", "-C", repo, "cat-file",
                        "--batch-check=%(objectname) %(objecttype)"],
                       input=inp, stdout=subprocess.PIPE, check=True)
    return [l.split()[0] for l in p.stdout.splitlines() if l.endswith(b" blob")]


def read_blobs(repo, shas):
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write(b"\n".join(shas) + b"\n")
    p.stdin.close()
    for _ in shas:
        header = p.stdout.readline().split()
        size = int(header[2])
        data = p.stdout.read(size)
        p.stdout.read(1)
        yield data
    p.wait()


def main():
    global LAT_RANGE, LON_RANGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--out", default=os.path.expanduser("~/座標の置き換え.txt"))
    ap.add_argument("--lat-range", nargs=2, type=float, default=LAT_RANGE,
                    metavar=("MIN", "MAX"), help="試験用（偽の repo）。既定は徳島の畑の範囲")
    ap.add_argument("--where", action="store_true",
                    help="値は出さず、候補が出るファイルの道と、候補の種の数・小数の桁だけ出す")
    ap.add_argument("--include-head", action="store_true",
                    help="今の HEAD の木にもある値も表に入れる（既定は入れない。11-05 に"
                         "置き換えた後の HEAD にある値は見本の周りの点で、本物ではない）")
    ap.add_argument("--lon-range", nargs=2, type=float, default=LON_RANGE,
                    metavar=("MIN", "MAX"))
    a = ap.parse_args()
    LAT_RANGE, LON_RANGE = tuple(a.lat_range), tuple(a.lon_range)
    repo = os.path.abspath(a.repo)
    out = os.path.abspath(os.path.expanduser(a.out))
    if os.path.commonpath([repo, out]) == repo:
        sys.exit("止めた: --out が repo の中を指している（表は repo の外に）")

    found = {"lat": set(), "lon": set()}
    in_msg = set()
    nblob = 0

    where = {}

    def scan(data, sink=None, path=None):
        hit = False
        for m in NUM.finditer(data):
            v = m.group(1).decode()
            if kept(v):
                continue
            c = classify(v)
            if c:
                found[c].add(v)
                if sink is not None:
                    sink.add(v)
                if path is not None:
                    where.setdefault(path, set()).add(v)
                hit = True
        return hit

    shas = blobs(repo)
    for sha, data in zip(shas, read_blobs(repo, shas)):
        if b"\0" in data[:8000]:
            continue  # 二進のファイル（写真）は見ない
        if scan(data, path=BLOB_PATH.get(sha, "?")):
            nblob += 1

    msgs = git(repo, "log", "--all", "--format=%B%x00")
    scan(msgs, in_msg)

    # 今の HEAD の木にある値（11-05 の置き換えの後に残っている物）
    head_vals = set()
    head_blobs = [l.split()[2] for l in git(repo, "ls-tree", "-r", "HEAD").splitlines()
                  if l.split()[1] == b"blob"]
    for data in read_blobs(repo, head_blobs):
        if b"\0" in data[:8000]:
            continue
        for m in NUM.finditer(data):
            head_vals.add(m.group(1).decode())
    in_head = (found["lat"] | found["lon"]) & head_vals
    if not a.include_head:
        found["lat"] -= in_head
        found["lon"] -= in_head
        for path in where:
            where[path] -= in_head
        where = {p: v for p, v in where.items() if v}
    print(f"HEAD の木にもある種 {len(in_head)}"
          + ("（表に入れる）" if a.include_head else "（表から外した）"))

    values = found["lat"] | found["lon"]
    if a.where:
        # 値は出さない。道ごとに、候補の種の数と、小数の桁の内訳だけ
        for path in sorted(where):
            digits = sorted(len(v.split(".")[1]) for v in where[path])
            print(f"{path}: {len(where[path])} 種（小数の桁 {digits}）")
        print(f"計 {len(values)} 種（緯度 {len(found['lat'])}、経度 {len(found['lon'])}）、"
              f"メッセージ {len(in_msg)} 種")
        return
    if len(values) >= TOO_MANY:
        print(f"止めた: 候補が {len(values)} 種（緯度 {len(found['lat'])}、"
              f"経度 {len(found['lon'])}）。{TOO_MANY} 種以上は何かが誤っている。"
              "表は書いていない。")
        sys.exit(2)
    if not values:
        print("候補 0 種。表は書いていない。")
        return

    # 出てくるコミット（変更の中に値がある物、とメッセージにある物）
    pattern = "(^|[^0-9.])(" + "|".join(re.escape(v) for v in sorted(values)) + ")([^0-9]|$)"
    commits = set(git(repo, "log", "--all", "--format=%H", "-G", pattern,
                      "--extended-regexp").split())
    commits |= set(git(repo, "log", "--all", "--format=%H", "--extended-regexp",
                       "--grep", pattern).split())

    lines = []
    for kind, sample in (("lat", LAT_SAMPLE), ("lon", LON_SAMPLE)):
        # 長い物から（短い物が先に当たって長い物を壊さないように。境界も付けてある）
        for v in sorted(found[kind], key=lambda s: (-len(s), s)):
            lines.append(f"regex:(?<![\\d.]){re.escape(v)}(?![\\d]|\\.\\d)==>{sample}")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"緯度 {len(found['lat'])} 種、経度 {len(found['lon'])} 種、"
          f"出てくるコミット {len(commits)}、blob {nblob}、"
          f"コミットのメッセージに出る値 {len(in_msg)} 種")
    print(f"表を書いた: {out}（権限 600。値は作者だけが開いて見る）")


if __name__ == "__main__":
    main()
