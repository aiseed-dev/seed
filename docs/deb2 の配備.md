# deb2 の配備（2026-11-04。11-05 夜に手順とコードを突き合わせて直した）

deb2 は Cloudflare の後ろ（Caddy の `(cf)` スニペット、origin 証明書）。dev は sudo を持たないので、root の作業は作者がする。

## 0. 11-06 の朝の手順（上から順に。コピーして打てる形）

### 0-★. Web を立ち上げる順（11-06。**提出と動画には要らない**。動画は手元の Flet の PC 版で撮り、GitHub の main と同じ版を見せる。Web 版はテスターのための物で、11-08 の後でもよい）（作者「帰ってきたら、web を立ち上げましょう」「作り直せよ。AI の書いた膨大な履歴は誰も見ない」）

公開する repo は、今の版だけの一つのコミットにする（過去の版を持たない。過去の版に残っていた畑の座標は、これで公開の側に出ない）。作者の手元の履歴（決めた日と理由）はこの repo に残り、動画の git log の場面はここから撮る。

1. **[debpc、作者] push**: 手元の main は 11-06 に今の版だけの一つのコミットにまとめた（古い履歴は枝 `backup-11-06`。要らなければ `git branch -D backup-11-06`）。それを GitHub の main に置く。
   ```bash
   cd /home/dev/dev/seed && git push --force origin main
   ```
   これで GitHub の過去の版は無くなる（GitHub が古いコミットを暫く保持しうるので、公開後に Support へ sensitive data removal を頼む）。
2. **[deb2] 0-1〜0-7** を上から。
3. **[Claude] 0-8** の外からの確かめ。
4. halo の二つの口の門（`deploy/halo/手順.md`）は後でよい。
5. 機械の形（ssh の認証、入っている鍵、口、入口、更新）を kagi で見るのは `deploy/deb2/手順.md`（11-06 夜）。配備の前に突き合わせると、残りの作業が「直す」に出る。

以後は普通に commit と push。コミットは要る時だけ、一行で。

### 0-0. 前の晩までに済ませておく物（debpc で）

- 11-05 夜の時点で、debpc の main は最後に fetch した GitHub の main より **25 コミット先**（`git log origin/main..main`）。ほかに作業中の変更（`server/settings.py`、`cli.py` の `seed invite --list`）がある。**commit して作者が push してから** deb2 で clone する。push が無いと deb2 には古い物が入る（招待コードの読み直しと `--list` が無い）。

**履歴の中の本物の座標（11-05 夜に見つけた）。** 座標の見本は最初のコミット（6e2030b）から本物で、GitHub の origin/main にも入っている（`git log -S` で 10 コミット、blob 9 個）。clone は履歴ごと deb2 に行き、11-08 に repo を公開すれば履歴ごと出る。直すなら push の前に、debpc で履歴を書き換えて force push（作者だけ。全部のコミットの番号が変わる。ほかに clone は無い）:

```bash
cd /home/dev/dev/seed && .venv/bin/pip install -q git-filter-repo && git branch backup-before-filter
```

置き換えの表は repo の外に（本物の値を書くので）。`~/座標の置き換え.txt` に、`本物==>34.0512` の形で一行ずつ（緯度の 4 桁、経度の 4 桁、test_photos のもう一組の緯度二つと経度、2 桁の物は `regex:(?<!\d)34\.07(?!\d)==>34.05` の形）。Claude には本物を書かせない。

```bash
cd /home/dev/dev/seed && .venv/bin/python -m git_filter_repo --replace-text ~/座標の置き換え.txt --force && git remote add origin git@github.com:aiseed-dev/seed.git
```

```bash
cd /home/dev/dev/seed && git log --all -S"<本物の緯度>" --oneline | wc -l   # 0 なら消えた
```

```bash
cd /home/dev/dev/seed && git push --force origin main && rm ~/座標の置き換え.txt
```

（filter-repo は origin を外すので足し直す。backup の枝は確かめた後に消す。しないなら、公開の時に履歴ごと出ることを分かった上で。）

道具は `scripts/座標の履歴/`（11-06）。順は README。注意: 上の `git branch backup-before-filter` は控えにならない（filter-repo は枝も一緒に書き換える。偽の repo で確かめた）。控えは `2-書き換える.sh` が repo の外に bundle で取る。表は dev の home に作る（script 1 を dev で走らせる。aiseed の home の物は dev が読めない）。

### 0-1. [root] Python の venv があるか、置き場を作る

```bash
python3 -c "import ensurepip" 2>/dev/null && echo "venv: ある" || sudo apt install -y python3-venv
```

```bash
sudo install -d -o dev -g dev -m 755 /opt/seed /var/lib/seed /var/lib/seed/public
sudo install -d -o dev -g dev -m 700 /var/lib/seed/users /var/lib/seed/uploads /var/lib/seed/audit /var/lib/seed/gate
sudo install -d -o root -g dev -m 750 /etc/seed
sudo sh -c 'umask 077; head -c 32 /dev/urandom > /etc/seed/log-key'
ls -ld /opt/seed /var/lib/seed /var/lib/seed/* /etc/seed
```

`gate/` は相手ごとの token の台帳の置き場（管理の画面から出すので、サーバーが書ける所）、`log-key` は記録の署名の鍵（`seed.service` が読む。無いとサービスが起きない）。`public` は Caddy（ユーザー caddy）が読むので 755。`users`（Web 版の人ごとの記録）と `uploads`（写真の一時置き場）は Caddy も他の人も読まないので 700。

### 0-2. [dev] clone、.venv、テスト

```bash
cd /opt/seed && git clone https://github.com/aiseed-dev/seed.git . && git log --oneline -1
```

```bash
cd /opt/seed && python3 -m venv .venv && .venv/bin/pip install -q -e ".[server,app,lookup,capture]" && .venv/bin/pip install -q pytest && .venv/bin/python -m pytest -q
```

`git log --oneline -1` が debpc の main の先頭と同じかを見る（0-0 の push が済んでいるか）。

### 0-3. [root] 鍵と招待コードの一覧を置く

```bash
sudo install -o root -g dev -m 640 /opt/seed/deploy/env.example /etc/seed/env
sudo install -o root -g dev -m 640 /opt/seed/deploy/invites.example.toml /etc/seed/invites.toml
```

```bash
sudoedit /etc/seed/env
```

`ANTHROPIC_API_KEY=` の右に **ここに本物を書く（Claude は見ない）**。Pl@ntNet の鍵があれば `PLANTNET_API_KEY=` にも（無ければ空のまま。`/api/identify` だけが 503）。ほかの行はそのまま。`SEED_PUBLIC_URL=https://seed.aiseed.dev` は消さない（Web 版で公開したときに返る url の基底。無いと `http://127.0.0.1:8010/...` が返る。11-05）。

招待コードを作る（一人一つ。画面に出るだけで、どこにも残らない）:

```bash
python3 -c "import secrets; [print(secrets.token_urlsafe(9)) for _ in range(5)]"
```

```bash
sudoedit /etc/seed/invites.toml
```

`[codes]` の下の見本の行（`"example-code-change-me" = "にじ"`）を消し、**ここに本物を書く（Claude は見ない）**: `"コード" = "呼び名"` を一人一行。呼び名は一言の送り主として相手に見える（本名は書かない）。`sudoedit` は持ち主と 640 を保つ。

```bash
ls -l /etc/seed/
```

両方 `-rw-r----- root dev` であること。

買い手に token を出す時（出た一行を、その人にだけ渡す。台帳に残るのはハッシュだけ）:

```bash
sudo /opt/seed/.venv/bin/seed token add "買い手の呼び名" --scope buyer --days 30 --file /var/lib/seed/gate/tokens.json
```

取り消しは `seed token revoke "呼び名" --file /var/lib/seed/gate/tokens.json`（次の要求から効かない）。一覧は `seed token list --file /var/lib/seed/gate/tokens.json`。記録の確かめ:

```bash
sudo KAGI_LOG_KEY_FILE=/etc/seed/log-key /opt/seed/.venv/bin/kagi log verify --dir /var/lib/seed/audit
```

### 0-4. [dev] 一覧が読めるか（コードは先頭 4 字だけ出る）

```bash
/opt/seed/.venv/bin/seed invite --list --invites /etc/seed/invites.toml
```

`N 件` と呼び名が出る。見本の `にじ`（`exam…`）が残っていたら 0-3 に戻る。

動かす人の token を一つ出す（管理の画面に入る鍵。出た一行を、自分のアプリの招待コードの欄に入れる。出るのはこの一度だけ）:

```bash
sudo -u dev /opt/seed/.venv/bin/seed token add "自分の呼び名" --scope admin --days 365 --file /var/lib/seed/gate/tokens.json
```

### 0-5. [root] systemd

```bash
sudo install -m 644 /opt/seed/deploy/seed.service /opt/seed/deploy/seed-app.service /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/seed.service /etc/systemd/system/seed-app.service
sudo systemctl daemon-reload && sudo systemctl enable --now seed seed-app
systemctl --no-pager status seed seed-app | head -30
```

```bash
curl -s http://127.0.0.1:8010/health; echo
curl -s -o /dev/null -w 'seed-app %{http_code}\n' http://127.0.0.1:8560/
ls /var/lib/seed/public/site
```

`/health` は `"read":true`（鍵が入った）、`"lookup":true`（fieldnotes-farm が入った）。`site/` に `index.html index.json p public robots.txt` があること（uvicorn が起きたときに書き出す）。

### 0-6. Cloudflare の DNS（作者、Cloudflare の画面で）

`seed` と `seed-app` の A レコード（または CNAME）を、deb2 のほかの副ドメインと同じ向け先に、proxied（橙の雲）で。

### 0-7. [root] Caddy

既に足してあれば二度足さない:

```bash
grep -q 'seed.aiseed.dev' /etc/caddy/Caddyfile && echo "もう入っている" || sudo sh -c 'cat /opt/seed/deploy/Caddyfile >> /etc/caddy/Caddyfile'
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && sudo systemctl reload caddy
```

`validate` が落ちたら reload しない（今の office ほかは止まらない）。落ちたときに疑う所（Claude は手元に caddy が無く、目でしか見ていない）: `handle_errors` の中の `expression` と `respond` の番号の置き換え（古い Caddy）。その時は `deploy/Caddyfile` の `handle_errors { ... }` をまるごと元の `respond "見つからない（seed）" 404` だけに戻してよい。

客の IP: deb2 の Caddy の全体の設定（`/etc/caddy/Caddyfile` の先頭の `{ servers { trusted_proxies ... } }`）か `(cf)` に Cloudflare の範囲が書いてあるかを見る:

```bash
grep -n 'trusted_proxies\|client_ip_headers\|CF-Connecting-IP' /etc/caddy/Caddyfile
```

書いてあれば本当の客の IP で回数を数える。無ければ Cloudflare の IP で数える（11-06 はそのままでよい。直すのは 11-08 の後。Fable が 11-05 夜に `header_up X-Forwarded-For` の行を外した: 直に LAN から叩いたときに空の IP になる方が困るため）。

### 0-8. Claude が外から打つ確かめ（作者が「置いた」と言ったら）

```bash
curl -s https://seed.aiseed.dev/health; echo                                   # 200、read true、lookup true
curl -sI https://seed.aiseed.dev/ | grep -iE '^HTTP|content-type|content-security'   # 200、text/html、CSP
curl -s https://seed.aiseed.dev/robots.txt                                     # User-agent: * / Allow: /
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/index.json    # 200
curl -s -w ' %{http_code}\n' 'https://seed.aiseed.dev/api/lookup?lat=0&lon=0'  # 403 invite_required
curl -s -w ' %{http_code}\n' -F token=x https://seed.aiseed.dev/api/read       # 503 は鍵無し、400 か 403 なら鍵あり（招待コード無しの門）
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/.owners.json  # 404（site/ の外）
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/connections/  # 404
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/p/no-such-1   # 404
curl -s -o /dev/null -w '%{http_code}\n' https://seed-app.aiseed.dev/          # 200（Flet の頁）
curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' https://seed-app.aiseed.dev/ws   # 101（Cloudflare と Caddy が WebSocket を通す）
```

その後、作者が本人の PC で `seed invite <コード>` を入れ、「サーバーで読む」と「公開」を一周する。公開の答えの url は `https://seed.aiseed.dev/public/<id>.md`（公開ファイルそのもの）、記録の頁は `https://seed.aiseed.dev/p/<id>`。

## 1. 分かったこと（11-04 に dev で見た）

| 項目 | 今 |
|---|---|
| OS / Python / git | Debian、Python 3.13.5、git 2.47 |
| Caddy | 稼働中。office（:8550）、aiai、git、auth、analytics が載っている。`(cf)` を import する形 |
| 空いている口 | 8000（aiai に取ってある）、8010、8551、8560 → seed の API は **8010**、Web 版は **8560** |
| DNS | `seed.aiseed.dev`、`seed-app.aiseed.dev` はまだ無い（Cloudflare で作る） |
| 置き場 | `/opt/seed`、`/var/lib/seed`、`/etc/seed` はまだ無い（root が作る） |
| 盤 / メモリ | 849 GB 空き、26 GB |

二段の副ドメイン（`app.seed.aiseed.dev`）は Cloudflare の無料の証明書に入らないので、Web 版は `seed-app.aiseed.dev`。

## 2. 11-05 夜に直した所と、手元で確かめた物

11-04 の手順（root がリポジトリの `/home/dev/dev/seed/deploy/` から写す）は、deb2 にその clone がある前提だった。0 では `/opt/seed` に clone してから `/opt/seed/deploy/` を写す順に変えた。ほかに直した物:

| 所 | 前 | 今 | 理由 |
|---|---|---|---|
| `users`、`uploads` | 755 | 700 | Web 版の人ごとの記録と写真。Caddy も他のユーザーも読まない |
| venv | 書いていない | `python3-venv` を確かめる | Debian の python3 は venv を別の包みにしている（deb2 にあるかは未確認） |
| テスト | 「テスト」とだけ | `pip install pytest` してから | `[server,app,lookup]` に pytest は入っていない |
| 招待コードの編集 | 「開き」 | `sudoedit` | 持ち主と 640 を保つ |
| Caddy の追記 | `cat >>` | 既にあれば足さない | 二度貼ると同じ名のブロックが二つになり validate が落ちる |
| 公開の後に出る url | `/p/<id>` | `/public/<id>.md` | `/api/publish` の答えは `base_url + public/<id>.md`（`main.py`）。頁は `/p/<id>` |
| `seed.service` | access log あり | `--no-access-log` | `/api/lookup` は `invite` を query で受け、uvicorn の一行のログにコードが出る（手元で見た） |
| `seed-app.service` | 止める時間は既定 | `TimeoutStopSec=10` | WebSocket が開いていると SIGTERM で止まらなかった（手元。二度目の信号で止まった） |
| Caddyfile `/api/*` | そのまま | `header_up X-Forwarded-For {CF-Connecting-IP}` | 何もしなければ uvicorn に届く IP は Cloudflare の物になる（推測。deb2 の全体の設定しだい。0-7） |
| Caddyfile 静的 | CSP 無し | FastAPI と同じ CSP | 静的な頁は Caddy が配るので、`main.py` の CSP が付かない |
| Caddyfile `/public/*.md` | 既定の型 | `text/markdown; charset=utf-8` | Caddy の型の表に .md があるかは OS しだい |
| Caddyfile `handle_errors` | 何でも 404 | 404 だけ「見つからない」 | uvicorn が落ちたときの 502 が 404 に見えていた |

手元（debpc、11-05 夜、口 18010 と 18560、捨てる `public/` と招待コード「ためし」、鍵は空）で通した物: `/health` 200（`read:false`、`lookup:true`）、招待コード無し・違うコードで `/api/lookup`・`/api/publish`・`/api/connect` が 403 `invite_required`、コード付きで `/api/read` 503 `read_unavailable`・`/api/identify` 503、`/api/publish` 200 で `site/index.html`・`site/p/<id>.html`・`site/public/<id>.md`・`site/index.json`・`site/robots.txt` ができた、`Host` と `X-Forwarded-Proto: https` を付けると答えの url が `https://seed.aiseed.dev/public/<id>.md`、`/`・`/p/<id>` は `site/` の物と同じ中身、`/p/無い物` 404、`/api/connect` 200 で入口の「繋がり 1」、取り下げで `site/p/` と `site/public/` が空に、`invites.toml` を空にすると次の要求から 403・戻すと通る、`seed invite --list`、`seed app --web --serve` の `/` 200・`main.dart.js` 200・`/ws` 101、`systemd-analyze verify`（`/opt/seed` を手元の道に置き換えて。置き換え無しは実行ファイルが無いことだけ）。

確かめていない物（deb2 でしか分からない）: Cloudflare の DNS と proxied、`(cf)` の中身、`caddy validate`（手元に caddy が無い）、客の IP が uvicorn に正しく届くか、Caddy（ユーザー caddy）が `/var/lib/seed/public/site` を読めるか、`python3-venv` の有無、本物の鍵での `/api/read`。

コードの側で気づいた物: Web 版（seed-app）は `SEED_SERVER_URL=http://127.0.0.1:8010` で API を呼ぶので、公開したときに出る url が `http://127.0.0.1:8010/public/<id>.md` になっていた → 11-05 夜に `SEED_PUBLIC_URL`（`/etc/seed/env`、既定の見本は `https://seed.aiseed.dev`）を足し、あればそれを基底にするようにした（テストで確認。実機は未）。seed-app も `/etc/seed/env` を読むので `ANTHROPIC_API_KEY` を持つ（使わない。11-08 の後に分ける）。`/api/lookup` は招待コードを query で受ける（`--no-access-log` で手当て。本来は見出しか body。11-08 の後）。

## 3. 作る人（dev）の作業（更新のたび）

- 更新: `cd /opt/seed && git pull --ff-only && .venv/bin/pip install -q -e ".[server,app,lookup,capture]"` → root が `sudo systemctl restart seed seed-app`。`deploy/` の unit を変えたときは 0-5 の `install` と `daemon-reload` も。Caddyfile を変えたときは `/etc/caddy/Caddyfile` の seed のブロックを手で置き換えて 0-7 の `validate` と `reload`。
- 招待コードの失効: `/etc/seed/invites.toml` から行を消すだけ（次の要求から効く。再起動は要らない）。Web 版のログインも同じファイルを読む。

## 4. 注意

- `/etc/seed/env` と `invites.toml` は root:dev 640。dev が読めて、ほかは読めない。`/var/lib/seed/users` と `uploads` は dev の 700。
- Caddy が Cloudflare の `CF-Connecting-IP` から本当の客の IP を取り、`X-Forwarded-For` で uvicorn に渡す（`deploy/Caddyfile` の `header_up`。deb2 の全体の設定に `trusted_proxies` があればそれでも）。uvicorn は 127.0.0.1 からのそれを信じる（回数の上限の IP はこれ）。origin に Cloudflare を通さず来られると `CF-Connecting-IP` は偽れる（IP ごとの上限を逃れるだけ。token ごと・全体の上限は残る）。
- 静的サイト `site/` は uvicorn が公開のたびに書き出す。uvicorn が落ちていても入口と記録は見える。
- 8000 は aiai の moushikomi に取ってあるので使わない。8550 は office。
- 2026-11-06: §0-★ 朝食の後に Web を立ち上げる順（座標の履歴 → force push → 0-1〜0-7 → 0-8 → halo の門は後）。
- 2026-11-06: §0-★ を作り直し（作者「作り直せよ」）。公開は今の版だけの一つのコミット（main-公開用）。過去の版の書き換えは使わない。
