---
name: seed-preview
description: seed のアプリを Web（この PC のブラウザ）で開いて、画面の形や文をスマートフォンの幅と PC の幅で確かめる時、画面の写真を撮る時に使う。
---

# アプリを Web で開いて画面を見る

`seed app --web` は Flet のアプリをこの PC のブラウザで開く（画面の確かめ用、一人用）。作者の本物のプロジェクトフォルダーは使わず、scratchpad の写しで開く。

## 1. 写しを作る

```bash
.venv/bin/seed project list                      # 作者のプロジェクトの道（* が今の物）
rsync -a --exclude home.toml <プロジェクト>/ <scratchpad>/preview/seed/
```

- `home.toml`（招待コード）は写さない。
- 写しの `seed.toml` に `bulk` の行があれば消す。在ると、写しから写真の元が元の置き場に書かれる。

## 2. `.claude/launch.json` に一つ足す

`.claude/launch.json` は `.gitignore` にあり、git に入らない。他の回が足した項目は消さずに、`configurations` に一つ足す。

```json
{
  "name": "seed-preview",
  "runtimeExecutable": "bash",
  "runtimeArgs": [
    "-c",
    "SEED_CLAUDE=/nonexistent/claude SEED_CREDENTIALS=<scratchpad>/preview/cred.toml .venv/bin/seed --folder <scratchpad>/preview/seed app --web --port 8563"
  ],
  "port": 8563
}
```

- `SEED_CLAUDE=/nonexistent/claude`: 話すで手元の Claude Code を呼ばない（`src/seed/local.py` の `SEED_CLAUDE`）。
- `SEED_CREDENTIALS=<無いファイル>`: 作者の `~/.config/seed/credentials.toml`（本人の Anthropic の鍵）を読まない。鍵が見えると、Claude Code が無い時にその鍵で API を呼ぶ。
- `port`: 他の項目と重ならない所。使われているかは `ss -ltn 'sport = :8563'`。
- `--folder` は `app` の前でも後でもよい（`seed app --folder ... --web`）。

## 3. 開いて見る

1. `preview_start` に `name: "seed-preview"` を渡して開く。
2. 幅を変えて見る。スマートフォンは `resize_window` の `preset: "mobile"`（375 × 812）、PC は `width: 1280`、`height: 800`。終わったら `preset: "desktop"` に戻す。
3. 文と並びは `read_page` か `get_page_text`、形は `screenshot`。
4. 終わったら `preview_stop` で自分が開いた回を止める。

## 4. Web で見えない物

- 話すの左下の印: Web 版はスマートフォンと同じく「撮る」（カメラの印）になる（`capture.available` が Web を撮れる側に数える）。PC の窓の「写真・動画・zip を選ぶ」は Web には出ない。
- 撮る画面: 押すと開き、形（上の端の「← 戻る」と位置の印、下の帯の写真と動画の切り替え、シャッター、✓。倍率の印はカメラが倍率を返した時だけ）は Web でも見える（設計書 §5.14、`src/seed/app/capture.py`）。カメラの映りは出ず、開けない時は「カメラを開けません（端末の設定）。」の一行が出る。撮る所は実機で作者に見てもらう（`seed-phone` のスキル）。
- 写真・動画・zip を入れる所（設計書 §5.15）: Web では使えない。`main.py` の `pick_photos` は選んだファイルの道で入れるが、ブラウザで選んだ物には道が無く、「写真は PC 版（seed app）で選んでください。」の一行で終わる。PC の窓（`seed app`）で見る。中の動きは `tests/test_bundle.py`。

## してはいけない事

- 作者の本物のプロジェクトフォルダーを `--folder` に指さない。写しの中で消したり書いたりしても、作者の記録に響かないように。
- `SEED_CLAUDE` と `SEED_CREDENTIALS` を外さない（読みや話すで Claude を呼び、作者の契約や鍵を使う）。
- 作者が開いている `flet run --web` を止めない（`pgrep -af "flet run"` で見る）。

## 確かめ方

- `preview_start` の後に `read_console_messages`（`onlyErrors: true`）と、`preview_logs` で Python の誤りが無い。
- スマートフォンの幅で横に流れ出していない（`screenshot` で端が切れていない）。
