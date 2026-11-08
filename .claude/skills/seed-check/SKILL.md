---
name: seed-check
description: seed でコミットする前に、lint と整形とテストを通し、コミットの題と本文を repo の形に揃える時に使う。一時ファイルの置き場と片付け（/tmp が満ちるのを防ぐ）もここ。
---

# コミットの前の確かめ

## 0. 一時ファイル（/tmp を満たさない）

この PC の `/tmp` は 32 GB の tmpfs で、Claude のセッションの作業用フォルダー（`/tmp/claude-1001/<プロジェクト>/<セッション>/`）がそのまま残ると満ちる。満ちると、テストが落ち、`flet run` と `seed home` も一時ファイルを書けずに止まる（作者 11-08「Claude が消さないからです」）。

- 始めに `df -h /tmp` を見る。90 % を超えていたら、一日より古いセッションの物を消す: `find /tmp/claude-1001 -mindepth 2 -maxdepth 2 -mtime +1 -exec rm -rf {} +`。今日触った物は、ほかの回が使っている事があるので消さない。
- 大きい物（動画、写真の写し、pytest の一時フォルダー、取ってきた資料）は `/tmp` に置かない。`/var/tmp/seed-<用>/` に置き、終わったら消す。
- pytest は `.venv/bin/pytest -q --basetemp=/var/tmp/seed-test -p no:cacheprovider` で走らせ、終わったら `rm -rf /var/tmp/seed-test`。
- 回の終わり（引き継ぎを書いた後、またはコミットの後）に、自分の作業用フォルダーを消す: `rm -rf /tmp/claude-1001/*/<このセッションの id>`。

## 1. 通す

repo の根で。

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/pytest -q --basetemp=/var/tmp/seed-test -p no:cacheprovider && rm -rf /var/tmp/seed-test
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
