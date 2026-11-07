---
name: seed-phone
description: seed のアプリを USB で繋いだ Android の実機に入れて試す時、実機のアプリの中の記録や画面の録画を PC で見る時、APK を作る時に使う。
---

# Android の実機で試す

コマンドは repo の根（`pyproject.toml` のある所）で打つ。`flet` は `pyproject.toml` の `[tool.flet.app]`（`path = "src"`、`module = "main.py"`）を読む。

adb は `~/Android/sdk/platform-tools/adb`、無ければ PATH の `adb`。下では `ADB` と書く。

```bash
ADB=~/Android/sdk/platform-tools/adb; [ -x "$ADB" ] || ADB=adb
```

## 始める前に見る

- 作者が動かしている回: `pgrep -af "flet (debug|run)"`。在れば止めない。新しく `flet debug` を始めると同じアプリが入れ直され、作者の回が切れる。Python を直した後は、作者の端末で `R` を押すと読み直される。
- 繋がっている端末の番号: `$ADB devices`（`device` と出た行の一つ目の欄）か `.venv/bin/flet devices android`。番号はファイルにも報告にも写さない。

## 入れて動かす

```bash
.venv/bin/flet debug android --device-id <adb devices の番号> --arch arm64-v8a
```

作るのに数分かかり、終わらずに走り続けるので後ろで動かす（Bash の `run_in_background`）。出力に「Flutter run key commands」と出たら、スマートフォンに画面が出ている。Python を直したら `R`、終わる時は `q`。起きた時に `Pictures/seed: ok` の一行が出る（`src/main.py`。写真をスマートフォンの共有の所に書けるかの確かめ）。

## APK にする

```bash
.venv/bin/flet build apk --arch arm64-v8a
```

出来る物は `build/apk/seed-farm.apk`。入れ直しは `$ADB -s <番号> install -r build/apk/seed-farm.apk`（`-r` はアプリの中の記録を残したまま差し替える）。

## アプリの中を見る（読むだけ）

アプリは自分の入れ物を家にする（`src/main.py` が `HOME` を `FLET_APP_STORAGE_DATA` にする）。記録は `files/data/seed` の下。

```bash
$ADB shell run-as dev.aiseed.seed ls -R files/data/seed | head -80
$ADB shell run-as dev.aiseed.seed cat files/data/seed/<観察の道>.md
$ADB exec-out run-as dev.aiseed.seed cat files/data/seed/<写真の道>.jpg > <scratchpad>/x.jpg
```

- 撮った写真の写し: `/storage/emulated/0/Pictures/seed/<日付>/`（`photos.device_pictures_dir`）。
- 録った動画: 記録の `videos/<日>/<時刻>.mp4` と同じ名の `.json`。PC に送れた物は `.json` に `sent` が付く。

## 画面の録画

スマートフォンの画面の録画は `/storage/emulated/0/Movies/` に入り、名は録画を止めた時刻。

```bash
$ADB shell ls -lt /storage/emulated/0/Movies/ | head
$ADB pull /storage/emulated/0/Movies/<名>.mp4 <scratchpad>/
FF=$(.venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -ss 3 -i <scratchpad>/<名>.mp4 -frames:v 1 <scratchpad>/<名>.jpg   # 一コマを絵にして Read で見る
```

## してはいけない事

- スマートフォンの鍵を開けない。PIN を打たない。画面が消えていたら作者に開けてもらう。
- `credentials.toml` を読まない。スマートフォンの中（`files/data/.config/seed/`）も PC の `~/.config/seed/` も。本人の鍵が入っている。
- 写真や動画を消す前に、pull して一コマを見て、何の物かを確かめる。2026-11-07 に確かめずに消した動画が畑の動画で、戻せなかった。
- 作者が動かしている `flet debug` / `flet run` を止めない。
- `adb uninstall` と `pm clear` を使わない。アプリの中の記録（`files/data/seed`）ごと消える。

## 確かめ方

- `flet debug` の出力に「Flutter run key commands」と `Pictures/seed: ok`。Python の誤りもこの出力に出る。
- 撮った後に `run-as` の `ls -R` で、新しい観察と写真が増えている。
