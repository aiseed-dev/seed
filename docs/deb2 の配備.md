# seed のサーバーの配備（Debian、Caddy、Cloudflare の後ろ）

seed のサーバー（入口の頁、公開された記録、招待コードで開く読み取りと話す）を、Debian の機械に置く手順です。作者は自分の機械 deb2 に、この手順で置きます。root の作業は機械の持ち主がします。AI が動くアカウント（`dev`）は sudo を持たず、コードを置くだけです。

この機械に固有の事（ほかに載っているサイトと口、機械の今の形、前の形から移した記録、見つけた事）は公開しません。作者の手元に置いています。

アカウントの分け方（作者 11-06「AI が動くアカウントに sudo を渡さない」「サービスは専用の利用者で動かす」）:

| アカウント | する事 | 読めない物 |
|---|---|---|
| `dev`（AI が動く） | `/opt/seed` にコードを置く（clone、pull、pip） | `/etc/seed` の下全部（鍵、招待コードの一覧、設定）、`/var/lib/seed` の台帳と記録 |
| `seed`（サービス。ログインしない） | `seed.service` を動かす。`/var/lib/seed` の下を書く。`/opt/seed` は読むだけ | 鍵のファイルそのもの（`/etc/credstore/seed.*`、`/etc/seed/log-key`） |
| root（作者） | 利用者を作る、鍵を置く、systemd、Caddy | — |

鍵（Claude、Pl@ntNet、記録の署名）は鍵ごとに root だけが読めるファイル（600 root）に置き、systemd がサービスにだけ渡す。記録の署名の鍵（`/etc/seed/log-key`、0-1 で必ず作る）は `LoadCredential=`、Claude と Pl@ntNet の鍵（`/etc/credstore/seed.anthropic`、`/etc/credstore/seed.plantnet`）は `ImportCredential=`。`ImportCredential=` は無いファイルを飛ばすので、鍵が無くてもサービスは起き、鍵の要る口（読み取り、話す、草の名）は 503 で「準備中です」、入口の頁に一行が出る。鍵は後から置き、置いたら restart（`ImportCredential=` は systemd 254 から。Debian 13 は 257。`systemctl --version` の一行目で見る）。サーバーは `$CREDENTIALS_DIRECTORY` に鍵が在ればそれを、無ければ環境変数を読む（手元で動かす時とテスト）。`/etc/seed/env` には秘密でない設定（URL、置き場、上限、モデル）だけ。Web に出すのは入口、公開された記録、使い方の説明だけ（作者 11-06「Web 版は、マニュアル的なものだけにする」）。


## 0. 手順（上から順に。コピーして打てる形）

順: debpc で `git push` → 0-1 から 0-7 → 0-8 の外からの確かめ。0-2 と 0-8 は dev（Claude）が、ほかは root がします。

### 0-1. [root] サービスの利用者 seed、置き場

```bash
python3 -c "import ensurepip" 2>/dev/null && echo "venv: ある" || sudo apt install -y python3-venv
```

```bash
getent passwd seed || sudo useradd --system --user-group --home-dir /var/lib/seed --no-create-home --shell /usr/sbin/nologin seed
```

```bash
sudo install -d -o dev -g dev -m 755 /opt/seed
sudo install -d -o seed -g seed -m 755 /var/lib/seed /var/lib/seed/public
sudo install -d -o seed -g seed -m 700 /var/lib/seed/audit /var/lib/seed/gate /var/lib/seed/pending
sudo install -d -o root -g seed -m 750 /etc/seed
sudo install -d -o root -g root -m 700 /etc/credstore
sudo test -e /etc/seed/log-key || sudo sh -c 'umask 077; head -c 32 /dev/urandom > /etc/seed/log-key'
sudo ls -ld /opt/seed /var/lib/seed /var/lib/seed/* /etc/seed /etc/credstore /etc/seed/log-key
```

`seed` はログインしない利用者（`nologin`）。`/opt/seed` はコードで、`dev` が置き、`seed` は読むだけ。`/var/lib/seed` の下（公開、載せる前の待ち `pending/`、token の台帳 `gate/`、操作の記録 `audit/`）の持ち主は `seed`。`public` は Caddy（ユーザー caddy）が読むので 755、`pending`、`gate`、`audit` は 700（`pending` はサーバーの人が読む前の物なので、Caddy には見せない。設計書 §5.18）。`/etc/seed` は root:seed 750 で、`dev` は中を見られない。`/etc/credstore` と `log-key` は root だけ（鍵の置き方は 0-3）。

### 0-2. [dev] clone、.venv、テスト

```bash
cd /opt/seed && git clone https://github.com/aiseed-dev/seed.git . && git log --oneline -1
```

```bash
cd /opt/seed && python3 -m venv .venv && .venv/bin/pip install -q -e ".[server,lookup]" && .venv/bin/pip install -q pytest && .venv/bin/python -m pytest -q
```

`git log --oneline -1` が debpc の main の先頭と同じかを見る（push が済んでいるか）。テストは本物の鍵を使わない（Claude を呼ぶ所は差し替えてある）。サーバーには `flet`（アプリ）と `resvg_py`（図）と `qrcode` を入れないので、それらの要るテスト（test_app、capture、direct、loose、plugins、procedure_plugin、project は読み込めず、bundle・cli・home・grow・remote の一部が落ちる）はここでは通らない。サーバーのコードのテスト（test_server、test_talk_server、test_publish など）が通ればよい。11-08 の deb2: 568 通り、13 落ち（全部その理由）。pytest は `--basetemp=/var/tmp/seed-test -p no:cacheprovider` を付け、終わったら消す。

### 0-3. [root] 鍵、設定、招待コードの一覧を置く

Claude と Pl@ntNet の鍵は、今無ければ飛ばしてよい（後から置ける。置き方は 0-5 の後の「鍵を後から置く」）。無い間も、サービスは起き、入口と公開された記録は出る。鍵の要る口は 503 で「準備中です」。

鍵は一つずつ、root だけが読めるファイルに。**ここに本物を貼る（Claude は見ない）**: 次の一行を打つと入力を待つので、鍵を貼り、Enter、Ctrl-D。鍵は画面にも、シェルの履歴にも残らない。鍵がもう在る時は何も聞かずに終わる。

```bash
sudo test -e /etc/credstore/seed.anthropic || sudo sh -c 'umask 077; cat > /etc/credstore/seed.anthropic'
```

Pl@ntNet の鍵があれば同じく:

```bash
sudo test -e /etc/credstore/seed.plantnet || sudo sh -c 'umask 077; cat > /etc/credstore/seed.plantnet'
```

秘密でない設定と、招待コードの一覧:

```bash
sudo install -o root -g seed -m 640 /opt/seed/deploy/env.example /etc/seed/env
sudo install -o root -g seed -m 640 /opt/seed/deploy/invites.example.toml /etc/seed/invites.toml
```

`/etc/seed/env` は見本のままでよい（鍵の行は無い）。`SEED_PUBLIC_URL=https://seed.aiseed.dev` は消さない（公開したときに返る url の基底。無いと `http://127.0.0.1:8010/...` が返る。11-05）。話す口の回数は `SEED_DAILY_TALKS` と `SEED_PER_TOKEN_TALKS`（`0` で閉じる）。

招待コードを作る（一人一つ。画面に出るだけで、どこにも残らない）:

```bash
python3 -c "import secrets; [print(secrets.token_urlsafe(9)) for _ in range(5)]"
```

```bash
sudoedit /etc/seed/invites.toml
```

`[codes]` の下の見本の行（`"example-code-change-me" = "にじ"`）を消し、**ここに本物を書く（Claude は見ない）**: `"コード" = "呼び名"` を一人一行。呼び名は一言の送り主として相手に見える（本名は書かない）。`sudoedit` は持ち主と 640 を保つ。

確かめ（持ち主と許可）:

```bash
sudo ls -l /etc/seed/ /etc/credstore/
```

`env` と `invites.toml` は `-rw-r----- root seed`、`log-key` と `/etc/credstore/` の中は `-rw------- root root`（鍵をまだ置いていなければ `/etc/credstore/` は空）。

確かめ（鍵は dev からも seed からも直には読めない）:

```bash
cat /etc/credstore/seed.anthropic; cat /etc/seed/invites.toml; ls /etc/seed
```

`dev` で打つ。三つとも `Permission denied`。

```bash
sudo -u seed cat /etc/credstore/seed.anthropic; sudo -u seed cat /etc/seed/log-key
```

二つとも `Permission denied`。鍵はサービスが動いている間だけ、systemd がそのサービスにだけ渡す（`$CREDENTIALS_DIRECTORY`）。サービスの中から読めた事は 0-5 の `/health` の `"read":true` で見る。

買い手に token を出す時（出た一行を、その人にだけ渡す。台帳に残るのはハッシュだけ）:

```bash
sudo -u seed /opt/seed/.venv/bin/seed token add "買い手の呼び名" --scope buyer --days 30 --file /var/lib/seed/gate/tokens.json
```

取り消しは `sudo -u seed /opt/seed/.venv/bin/seed token revoke "呼び名" --file /var/lib/seed/gate/tokens.json`（次の要求から効かない）。一覧は `… seed token list --file …`。記録の確かめ:

```bash
sudo KAGI_LOG_KEY_FILE=/etc/seed/log-key /opt/seed/.venv/bin/kagi log verify --dir /var/lib/seed/audit
```

### 0-4. [root] 一覧が読めるか（コードは先頭 4 字だけ出る）

```bash
sudo -u seed /opt/seed/.venv/bin/seed invite --list --invites /etc/seed/invites.toml
```

`N 件` と呼び名が出る。見本の `にじ`（`exam…`）が残っていたら 0-3 に戻る。

動かす人の token を一つ出す（管理に入る鍵。出た一行を、机の PC の管理のアプリ `kagi app` の「人の出入り」の「繋ぐ先」に入れる。出るのはこの一度だけ。どこにも書き写さない）:

```bash
sudo -u seed /opt/seed/.venv/bin/seed token add "自分の呼び名" --scope admin --days 365 --file /var/lib/seed/gate/tokens.json
```

### 0-5. [root] systemd

`ImportCredential=` を使うので、systemd の版を見る:

```bash
systemctl --version | head -1
```

`systemd 254` 以上なら次へ（Debian 13 は 257）。

前に置いた unit（`LoadCredential=anthropic:` の行を `#` にした物）も、この unit で置き換える:

```bash
sudo install -m 644 /opt/seed/deploy/seed.service /etc/systemd/system/
```

```bash
sudo systemd-analyze verify /etc/systemd/system/seed.service
```

何も出なければ次へ（ほかの unit の警告が出ても、`seed.service` の行が無ければよい）。

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable seed && sudo systemctl restart seed
```

```bash
systemctl --no-pager status seed | head -20
```

`Active: active (running)` なら次へ。`status=243/CREDENTIALS` なら `/etc/seed/log-key` が無い（0-1 の `log-key` の行を打つ）。

```bash
curl -s http://127.0.0.1:8010/health; echo
```

`"lookup":true`（fieldnotes-farm が入った）、`"audit":"on"` なら次へ。鍵を置いていなければ `"read":false`、`"talk":false`、`"identify":false` で、それで正しい（その口が 503 で「準備中です」）。鍵の値は出ない。

```bash
ls /var/lib/seed/public/site
```

`index.html index.json p public robots.txt` があれば次へ（uvicorn が起きたときに書き出す）。

```bash
ps -o user= -C uvicorn
```

答えが `seed`。

#### 鍵を後から置く

0-3 の鍵の一行（`seed.anthropic`、Pl@ntNet なら `seed.plantnet`）を打ち、鍵を貼る。その後:

```bash
sudo systemctl restart seed
```

```bash
curl -s http://127.0.0.1:8010/health; echo
```

Claude の鍵なら `"read":true` と `"talk":true`、Pl@ntNet の鍵なら `"identify":true`。入口の頁の「準備中です」の一行は、restart の時に書き直されて消える。

### 0-6. Cloudflare の DNS（作者、Cloudflare の画面で）

`seed` の A レコード（または CNAME）を、deb2 のほかの副ドメインと同じ向け先に、proxied（橙の雲）で。

### 0-7. [root] Caddy

既に足してあれば二度足さない:

```bash
grep -q 'seed.aiseed.dev' /etc/caddy/Caddyfile && echo "もう入っている" || sudo sh -c 'cat /opt/seed/deploy/Caddyfile >> /etc/caddy/Caddyfile'
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && sudo systemctl reload caddy
```

`validate` が落ちたら reload しない（今動いているほかのサイトは止まらない）。 11-08 夜に置いた時、`/` だけが 404 になった（`/index.html` は 200）。`handle { try_files {path} {path}.html =404 }` が、フォルダーの `/` を見つけられないため。`deploy/Caddyfile` は `{path}/index.html` を足した形に直した。もう足してある Caddyfile は、その一行を置き換え、validate が通ったら reload する（一つずつ打つ）:

```bash
sudo sed -i 's#try_files {path} {path}.html =404#try_files {path} {path}/index.html {path}.html =404#' /etc/caddy/Caddyfile
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

```bash
sudo systemctl reload caddy
```

鍵を後にして紹介の頁だけ出す時も、unit はそのまま（鍵が無くても起きる。0-5）。落ちたときに疑う所（Claude は手元に caddy が無く、目でしか見ていない）: `handle_errors` の中の `expression` と `respond` の番号の置き換え（古い Caddy）。その時は `deploy/Caddyfile` の `handle_errors { ... }` をまるごと元の `respond "見つからない（seed）" 404` だけに戻してよい。

客の IP: deb2 の Caddy の全体の設定（`/etc/caddy/Caddyfile` の先頭の `{ servers { trusted_proxies ... } }`）か `(cf)` に Cloudflare の範囲が書いてあるかを見る:

```bash
grep -n 'trusted_proxies\|client_ip_headers\|CF-Connecting-IP' /etc/caddy/Caddyfile
```

書いてあれば本当の客の IP で回数を数える。無ければ Cloudflare の IP で数える。11-07 夜に門へ入れた「間違いを重ねた番地を止める」（設計書 §5.13、`limits.Tries`。10 分に 10 回の間違いで、その番地を 10 分 429。管理の token も止まる）は、この番地で数えるので、Cloudflare の IP のままだと、一人の間違いで同じ Cloudflare の番地を通る全員と管理の画面が 10 分止まる。だから seed を deb2 に置く前に、全体の設定に Cloudflare の範囲の `trusted_proxies` を書く（11-08 の点検で分かった。前は「直すのは 11-08 の後」としていた。Fable が 11-05 夜に `header_up X-Forwarded-For` の行を外した: 直に LAN から叩いたときに空の IP になる方が困るため）。

### 0-8. Claude が外から打つ確かめ（作者が「置いた」と言ったら）

```bash
curl -s https://seed.aiseed.dev/health; echo                                   # 200、lookup true。鍵を置いていれば read、talk、identify も true
curl -sI https://seed.aiseed.dev/ | grep -iE '^HTTP|content-type|content-security'   # 200、text/html、CSP
curl -s https://seed.aiseed.dev/robots.txt                                     # User-agent: * / Allow: /
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/index.json    # 200
curl -s -w ' %{http_code}\n' 'https://seed.aiseed.dev/api/lookup?lat=0&lon=0'  # 403 invite_required
curl -s -w ' %{http_code}\n' -F token=x https://seed.aiseed.dev/api/read       # 503 は鍵無し（準備中です）、400 か 403 なら鍵あり（招待コード無しの門）
curl -s -w ' %{http_code}\n' -H 'content-type: application/json' -d '{"messages":[]}' https://seed.aiseed.dev/api/talk   # 403 invite_required
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/.owners.json  # 404（site/ の外）
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/connections/  # 404
curl -s -o /dev/null -w '%{http_code}\n' https://seed.aiseed.dev/p/no-such-1   # 404
```

その後、作者が本人の PC で `seed invite <コード>` を入れ、「サーバーで読む」「話す（設定の札で読み取りと話すをサーバーに）」「公開」を一周する。公開の答えの url は `https://seed.aiseed.dev/public/<id>.md`（公開ファイルそのもの）、記録の頁は `https://seed.aiseed.dev/p/<id>`。

## 3. 作る人（dev）の作業（更新のたび）

- 更新: `cd /opt/seed && git pull --ff-only && .venv/bin/pip install -q -e ".[server,lookup]"` → root が `sudo systemctl restart seed`。`deploy/` の unit を変えたときは 0-5 の `install` と `daemon-reload` も。Caddyfile を変えたときは `/etc/caddy/Caddyfile` の seed のブロックを手で置き換えて 0-7 の `validate` と `reload`。
- 招待コードの失効: root が `sudoedit /etc/seed/invites.toml` で行を消すだけ（次の要求から効く。再起動は要らない）。dev はこのファイルを読めない。
- 鍵を替える: root が `/etc/credstore/seed.<名>` を置き換え（`sudo sh -c 'umask 077; cat > /etc/credstore/seed.anthropic'`）、`sudo systemctl restart seed`。

## 4. 注意

- `/etc/seed` は root:seed 750、`env` と `invites.toml` は root:seed 640（サービスの利用者 seed だけが読める。dev は読めない）。鍵（`/etc/credstore/seed.anthropic`、`/etc/credstore/seed.plantnet`、`/etc/seed/log-key`）は root:root 600 で、systemd の `ImportCredential=` と `LoadCredential=` がサービスにだけ渡す。鍵の値はログ、例外の文、`/health`、管理の画面に出ない（在るか無いかだけ）。`/var/lib/seed` の下は seed の物。
- Caddy が Cloudflare の `CF-Connecting-IP` から本当の客の IP を取り、`X-Forwarded-For` で uvicorn に渡す（`deploy/Caddyfile` の `header_up`。deb2 の全体の設定に `trusted_proxies` があればそれでも）。uvicorn は 127.0.0.1 からのそれを信じる（回数の上限の IP はこれ）。
- 静的サイト `site/` は uvicorn が公開のたびに書き出す。uvicorn が落ちていても入口と記録は見える。
