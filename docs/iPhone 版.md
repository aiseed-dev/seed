# iPhone 版（2026-11-06 夜。作者「flet アプリで専用のカメラを持った方がいいかも」「iphone 版をつくればいい」）

人から届いた写真に座標が入っていなかった。アプリの中で撮り、撮った時の位置を写真に書き込む。

## 入っている物

- 撮る画面（`src/seed/app/capture.py`）: 「話す」の左下の「撮る」で開く。カメラを開く、撮る、並べて要らない物を外す、観察にする（送ると「話す」に写真が大きく出て、読み取りが始まる）。位置が取れるまでシャッターは切れない。
- 撮った写真に座標・時刻・向き・誤差を書く（`photos.stamp`）。後はスマートフォンのカメラの写真と同じ道。
- 読み取りと話す（言葉で頼む細かい作業）は、本人の Claude の鍵でスマートフォンから直に、か seed のサーバー経由（`src/seed/direct.py`。設定の札の「読み取りと話す」）。どちらも無ければ、本人の言葉として書き留める。
- スマートフォンの幅に合わせる。
- 入口 `src/main.py`、設定は `pyproject.toml` の `[tool.flet]`。

## Mac でビルドする

要る物: macOS、Xcode 15 以降、CocoaPods 1.16 以降、Apple Developer Program の加入。

```bash
git clone https://github.com/aiseed-dev/seed.git && cd seed
```

```bash
python3 -m venv .venv && .venv/bin/pip install "flet[all]==1.1.0"
```

シミュレーターで開く（署名は要らない。カメラは動かない）:

```bash
.venv/bin/flet build ios-simulator
```

実機に入れる（署名が要る。Team ID は Apple Developer の Membership の頁）:

```bash
.venv/bin/flet build ipa --ios-team-id <Team ID> --ios-export-method debugging
```

## 確かめた事

- スマートフォンに入れる依存だけ（flet、flet-camera、flet-geolocator、pillow、httpx、pyyaml）の環境で、アプリが読み込め、観察の画面（11-06 夜の時点。今の「話す」）まで作れる。
- ブラウザをスマートフォンの幅にして、撮る釦、撮る画面、位置を許さなかった時の文が出る。
- 撮った写真に書いた座標・時刻・向きが、読む側で同じ値に戻る（テスト）。

## 確かめていない事

- Mac でのビルド、iPhone の実機、カメラと位置の実際の動き。
- スマートフォンのアプリには手引き（skill）が入らない（自分の鍵で呼ぶ時は組み込みの短い決まりで動く。サーバー経由ならサーバーの手引き）。
- スマートフォンの安全な置き場の部品（`flet-secure-storage`）がスマートフォンのビルドで使えるか。本人の Claude の鍵は今、PC と同じ `~/.config/seed/credentials.toml`（600。スマートフォンではアプリの入れ物の中）に置く。
