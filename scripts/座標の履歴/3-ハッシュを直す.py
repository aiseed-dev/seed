#!/usr/bin/env python3
"""filter-repo の後、文書の中の古いコミット番号を新しい番号に直す。

.git/filter-repo/commit-map（旧 新）を読み、README・docs・skill・scripts・tests・deploy
の中の 7 桁以上の 16 進で、旧ハッシュの頭と一致する物を、新ハッシュの同じ桁数に書き換える。
作業木のファイルを書き換えるだけ（コミットはしない）。書き換えた箇所を標準出力に。

使い方: .venv/bin/python scripts/座標の履歴/3-ハッシュを直す.py [--repo PATH] [--dry-run]
"""
import argparse
import os
import re
import subprocess
import sys

DIRS = ["docs", "skill", "scripts", "tests", "deploy"]
TOP_GLOB = re.compile(r"^README.*", re.I)
HEX = re.compile(r"(?<![0-9A-Za-z_])([0-9a-f]{7,40})(?![0-9A-Za-z_])")


def load_map(repo):
    gitdir = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"],
                            check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    path = os.path.join(repo, gitdir, "filter-repo", "commit-map")
    if not os.path.exists(path):
        sys.exit(f"commit-map が無い: {path}（2-書き換える.sh の後に走らせる）")
    pairs = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 2 or parts[0] == "old":
                continue
            old, new = parts
            if old != new and set(new) != {"0"}:
                pairs.append((old, new))
    return pairs


def files(repo):
    for name in sorted(os.listdir(repo)):
        if TOP_GLOB.match(name) and os.path.isfile(os.path.join(repo, name)):
            yield name
    for d in DIRS:
        top = os.path.join(repo, d)
        for root, dirs, fs in os.walk(top):
            dirs[:] = sorted(x for x in dirs if x not in (".git", "__pycache__", ".venv"))
            for f in sorted(fs):
                yield os.path.relpath(os.path.join(root, f), repo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo = a.repo or subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True,
                                    stdout=subprocess.PIPE, text=True).stdout.strip()
    repo = os.path.abspath(repo)
    pairs = load_map(repo)
    olds = [o for o, _ in pairs]
    newof = dict(pairs)

    def lookup(tok):
        hits = [o for o in olds if o.startswith(tok)]
        if len(hits) == 1:
            return newof[hits[0]][:len(tok)]
        if len(hits) > 1:
            print(f"  曖昧（{len(hits)} 件に当たる）、触らない: {tok}")
        return None

    changed = 0
    for rel in files(repo):
        path = os.path.join(repo, rel)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        out_lines = []
        touched = False
        for i, line in enumerate(text.split("\n"), 1):
            def rep(m):
                nonlocal touched, changed
                tok = m.group(1)
                new = lookup(tok)
                if new is None:
                    return tok
                print(f"{rel}:{i}: {tok} → {new}")
                touched = True
                changed += 1
                return new
            out_lines.append(HEX.sub(rep, line))
        if touched and not a.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(out_lines))
    print(f"書き換え {changed} 箇所" + ("（--dry-run、書いていない）" if a.dry_run else ""))


if __name__ == "__main__":
    main()
