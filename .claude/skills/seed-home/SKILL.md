---
name: seed-home
description: スマートフォンから家の PC へ写真・動画・言葉を送る `seed home`（家のサーバー）を動かす、直す、確かめる時に使う。
---

# seed home（スマートフォン → PC、一方通行）

仕様は `docs/設計書.md` §5.13。PC のプロジェクトフォルダーが本物の記録で、スマートフォンは撮って送り、PC の Claude Code が読んで答えだけを返す。

## どこに何があるか

| 物 | 所 |
|---|---|
| 起動、招待コードを作る、番地を出す | `src/seed/cli.py` の `cmd_home`、`home_invite`、`lan_ip`、`home_env` |
| 受けた写真と動画を畑に置く、PC を探す呼びかけに答える | `src/seed/server/home.py`（`store`、`keep_video`、`answer_discovery`） |
| 口（`/health` の `"home": true`、`/api/read`、`/api/talk`、`/api/video`） | `src/seed/server/main.py` |
| スマートフォンの側の送る手 | `src/seed/client.py`（`is_home`、`video`） |
| スマートフォンの側の PC を探す手 | `src/seed/discover.py`（`find_home`） |
| テスト | `tests/test_home.py` |

- TCP 8800: HTTP の口（`seed home --port` で変わる）。
- UDP 8801: PC を探す。スマートフォンが `seed?` を網に呼びかけ、PC が `seed-home <URL>` を返す。返事が無ければ同じ /24 の番地に一つずつ聞く。`--host` が `0.0.0.0` か `::` の時だけ答える。
- 招待コード: `<プロジェクト>/home.toml`（許可 600、6 桁、一つ。無ければ作り、在ればそのまま使う）。
- 受けた物の置き場: 写真と観察は `<プロジェクト>/fields/<畑>/`（畑の名が無ければ今の畑か根）。動画は `<畑>/videos/<日>/<時刻>.mp4` と同じ名の `.json`（撮った時と所）。

## 作者が動かしているかを見る（読むだけ）

```bash
pgrep -af "seed home"
ss -ltn 'sport = :8800'
ss -lun 'sport = :8801'
curl -s http://127.0.0.1:8800/health      # "home": true なら家のサーバー
```

動いていれば止めない。スマートフォンからの送りは作者の回で確かめる。

## 自分で試す時

作者のフォルダーと口を使わず、scratchpad の写しで、この PC の中だけに立てる。`--host 127.0.0.1` だと PC を探す答えは出ないので、作者の 8801 とぶつからない。

```bash
rsync -a --exclude home.toml --exclude videos/ <プロジェクト>/ <scratchpad>/home-try/
SEED_CREDENTIALS=<scratchpad>/cred.toml .venv/bin/seed --folder <scratchpad>/home-try home --host 127.0.0.1 --port 8810
curl -s http://127.0.0.1:8810/health
```

- 後ろで動かし（`run_in_background`）、終わったら自分が立てたその回だけを止める。
- 読みまで通すと PC の Claude Code が動く。呼ばずに口だけを見る時は `SEED_CLAUDE=/nonexistent/claude` を足す（`/api/read` は 503 になる）。
- 写しの中に新しい `home.toml` が出来る。

スマートフォンからの通し（README と利用マニュアル §11b「スマートフォンから PC へ（一方通行）」と同じ手順）: PC で `seed home` → スマートフォンの「設定を見せて」→「PC を探す」→ 6 桁の招待コード → 撮る。PC の `<畑>/observations/` に観察、`photos/` に写真が増え、答えがスマートフォンに戻れば通っている。

## してはいけない事

- `home.toml` の値を読まない。`seed home` の出力には招待コードと PC の家の網の番地が出るので、その行をファイル、報告、コミットに写さない。テストと文書の番地は私用の網の形の例（`192.168.1.x`）にする。
- 作者の `seed home` を止めない。
- 防火壁（ufw）を変えない。sudo が要るので作者が打つ。スマートフォンから見つからない時は、上の `ss` で 0.0.0.0 に 8800（TCP）と 8801（UDP）が開いている事を確かめ、作者に `sudo ufw status` で家の網からの 8800/tcp と 8801/udp が通っているかを見てもらう。
- 家の網の外に口を開けない（seed は口を開けない。外から使う時は自分のサーバーか VPN の道）。

## 確かめ方

```bash
.venv/bin/pytest -q tests/test_home.py
```

スマートフォンの側の探す手（`find_home`）は偽のソケット、PC の答える手（`answer_discovery`）はこの PC の中の UDP、口は FastAPI の TestClient で試している。
