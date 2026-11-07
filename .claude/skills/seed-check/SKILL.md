---
name: seed-check
description: seed でコミットする前に、lint と整形とテストを通し、コミットの題と本文を repo の形に揃える時に使う。
---

# コミットの前の確かめ

## 1. 通す

repo の根で。

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/pytest -q
```

- 三つとも通ってからコミットする。全部のテストで 20 秒ほど。
- 整形が外れたら `.venv/bin/ruff format src tests` で直し、`git diff` で直った所を見る。
- テストの数は `pytest -q` の終わりの行（`N passed`）。本文に「N テスト」と書く時はこの数。

## 2. 載せる物を選ぶ

```bash
git status --short
git diff
git add <変えたファイル>
git diff --cached
```

- 同じ repo を別の回が同時に直している事がある。`git add -A` ではなく、自分が変えたファイルだけを名で足す。
- `git diff --cached` で、鍵（`sk-ant-` など）、token、招待コードの値、本物の座標、家の網の番地、機器のシリアル番号が入っていない事を見る。番地は `git diff --cached | grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}'` で拾い、テストの例の私用の網の形（`192.168.1.x`）のほかに無い事を見る。

## 3. 題と本文

形は `git log -20 --format=%s` と `git log -3 --format=%B` で見る。

- 題: 何をしたかを一行。作者の頼みから来た物は、括弧に作者の日付と短い言葉。例: `PC のアプリで動画と zip も入れる（作者 11-07「zipでまとめていれたいので、zipにも対応させて」）`。
- 本文: 直した事を `- ` の箇条で一行ずつ。触ったファイルや文書の名も。
- 終わりに `Co-Authored-By:` の行（その回に渡された物）。
- 区切りでまとめて一つにする。一言の直しごとにコミットを積まない。

## してはいけない事

- push しない。push と公開は作者だけ。
- 落ちたテストを外したり飛ばしたりして通さない。落ちたら直してから。
- 作者が変えた、自分の担当でないファイルを載せない。

## 確かめ方

```bash
git log -1 --stat
git status --short
```

載せたファイルが思った物だけで、残りが思った物だけである事。
