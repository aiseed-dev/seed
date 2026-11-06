# kagi — 設計書（2026-11-06。作者が確定するまで案）

計画は `docs/kagi 計画書.md`。決まりは `docs/鍵の管理の仕組み.md` §2（K-01〜15）。

## 1. 形

- Python 3.11 以上、標準ライブラリだけ（`tomllib`、`hashlib`、`hmac`、`json`、`argparse`、`pathlib`、`re`、`datetime`）。外の package を入れない。
- パッケージ `src/kagi/`。CLI は `kagi`（`pyproject.toml` の `[project.scripts]` に足す）。seed の `src/seed` には触らない。
- 作業の場所は `--dir DIR`（既定は `./kagi-data`）。中に `inventory.toml`、`ports.toml`、`machines.toml`（§3.4）、`audit.log` を置く。全部素の文字。
- 鍵の値は読まない、持たない、出さない。例外は署名の鍵で、それは読むが出さない。

## 2. ファイルの形

### 2.1 `inventory.toml`（在庫表。K-14、K-04、K-05）

```toml
[[secret]]
id = "deb2-seed-env"          # 一意の名
kind = "token"                # password | token | key | cert | passphrase | other
where = "deb2:/etc/seed/env"  # 置き場。機械:パス か 紙/金庫 の名。値ではない
holder = "yniji"              # 持つ人
role = "seed のサーバーが Claude を呼ぶ"   # 一つの役（K-01）
made = 2026-11-04             # 作った日
expires = 2027-05-04          # 期限（無い物は書かない → 抜けとして報告）
rotate_days = 180             # 回す周期
lost = "token を失効し、新しい token を発行して env を書き直す"   # なくした時
leaked = "失効 → 記録で範囲 → 作り直し → 知らせる"              # 漏れた時
```

必須の欄: `id`, `kind`, `where`, `holder`, `role`。`expires` と `rotate_days` と `lost` と `leaked` は無ければ「抜け」として報告する。`value` という欄があったら読まずに拒む（K-13。報告して終了コード 2）。

### 2.2 `ports.toml`（口の表。K-07）

```toml
[[port]]
host = "halo"
port = 8080
proto = "tcp"
service = "seed のサーバー"
bind = "127.0.0.1"            # どこに向くか。0.0.0.0 や :: は外向き
reason = "nginx の後ろ"
```

### 2.3 `audit.log`（記録。K-06）

JSON Lines。一行一件、追記だけ。

```json
{"seq": 1, "ts": "2026-11-06T09:00:00+09:00", "actor": "yniji", "action": "inventory.add", "detail": "deb2-seed-env", "prev": "0000…", "hash": "…", "sig": "…"}
```

- `prev` は前の行の `hash`。最初の行は 64 個の `0`。
- `hash` = SHA-256 of `seq|ts|actor|action|detail|prev` を UTF-8 で。
- `sig` = HMAC-SHA256(鍵, hash) の hex。鍵は §4。
- `verify` は、連番が 1 から飛びなく続く事、`prev` が前の `hash` と一致する事、`hash` が計算と一致する事、`sig` が鍵と一致する事、の四つを全行で見る。一つでも落ちたら、落ちた行の `seq` と理由を出し、終了コード 1。

## 3. 命令

| 命令 | 入力 | 出力 | 終了コード |
|---|---|---|---|
| `kagi init` | `--dir` | 三つのファイルの雛形を作る（在庫表と口の表は例を一件ずつコメント付きで。記録は空） | 0 |
| `kagi check inventory` | `inventory.toml`、`--days N`（既定 30） | 期限切れ、N 日以内に切れる物、欄の抜け、を表で | 抜けか期限切れがあれば 1、無ければ 0 |
| `kagi check ports --ss FILE` | `ports.toml` と `ss -ltnp` の出力のファイル（`--host NAME` で表のどの機械か） | 表に無い口（host, port, bind, process の名）、表にあって開いていない口、外向き（0.0.0.0, ::, *）で表の `bind` と違う口 | 差があれば 1 |
| `kagi scan PATH...` | ファイルかディレクトリ | `path:line  kind` の行だけ。値は出さない。`.git/`、バイナリ（NUL を含む）、1 MB 超は飛ばす。`--exclude GLOB` 可 | 見つかれば 1 |
| `kagi log add --actor A --action X --detail D` | 署名の鍵（§4） | 一行追記。追記した `seq` を出す | 0。鍵が無ければ 2 |
| `kagi log verify` | 署名の鍵 | `ok N lines` か、落ちた行と理由 | 0 / 1 |
| `kagi report` | 上の全部 | Markdown 一枚（在庫の数と期限、口の差、走査の数、記録の検証の結果）。標準出力 | 0 |

`ss -ltnp` の行の読み方: `LISTEN 0 128 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=…,fd=…))` から `bind`=`127.0.0.1`、`port`=8080、`process`=`python3`。IPv6 の `[::]:22` と `*:22` も読む。

走査の型（最初は少なく。計画書 §6 の 3）: PEM の頭（`-----BEGIN … PRIVATE KEY-----`）、`AKIA[0-9A-Z]{16}`、`ghp_[A-Za-z0-9]{36}`、`sk-[A-Za-z0-9_-]{20,}`、`xox[bp]-`、行頭からの `(password|passwd|secret|token|api_key)\s*[=:]\s*\S{8,}`（`.example` と `example` を含むパスは除く）。報告は種類の名（`pem-private-key`、`aws-access-key`、`github-token`、`openai-key`、`slack-token`、`assignment`）だけ。一致した文字列そのものは標準出力にもログにも出さない。

### 3.1 実装で決めた細部（11-06。Opus が書き、Fable が確かめた物。設計書の本文より細かい所）

- 口の外向き: 表の `bind` が `0.0.0.0`・`::`・`*` のどれかなら、`ss` 側がその三つのどれでも表の通りとする。表の `bind` が外向きでない時だけ「外向きで表と違う口」と出す。
- `--host` が無い時は表の全部の機械を一台とみなす。表に機械が二つ以上あれば `--host` が要る。
- `report` は `--ss FILE --host NAME --scan PATH... --exclude GLOB` を付けた時だけ口と走査を見る。付けなければ「突き合わせていない」「走らせていない」と書く。鍵が無ければ記録は「検証していない」。終了コードは 0。
- `--dir` は命令の前でも後でもよい。`scan` は作業の場所を使わない。
- `init` の雛形の例は全部コメント。既にあるファイルは触らない。
- 在庫表の `id` の重複と、`kind` が六つ以外の物は「形の誤り」で終了コード 1。期限が近いだけなら 0。
- 走査: PEM の頭は `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`。`assignment` は大文字小文字を区別せず、行頭の空白を許す。パスに `example` を含む所を外すのは `assignment` だけ。一行に何種類も当たれば種類ごとに一行。1 MB は 1,048,576 バイト。シンボリックリンクは辿らない。数は標準エラー、標準出力は `path:line  kind` だけ。
- 記録: 鍵のファイルが空なら「鍵が無い」と同じ（終了コード 2）。`log add` は最後の行が読めなければ足さず 1。`verify` は落ちた行を全部出す。追記は `flock` を掛けてから。
- テストのファイル名は `tests/kagi/test_kagi_*.py`（既存の `tests/test_cli.py` と名がぶつからないため）。

### 3.2 `kagi check smb --conf smb.conf`（11-06。鍵の管理 §5e の Samba の会社のため）

`smb.conf` を読み、口と認証の形を表で出す。値は出さない（パスワードの類は smb.conf に無いはずだが、`password` を含む行は内容を出さず「ある」とだけ）。見る物と決まり:

| 見る物 | 良い形 | 出す |
|---|---|---|
| `server min protocol` | SMB2 以上 | 無ければ「SMB1 が通る」 |
| `server signing` | `mandatory` | 違えば「署名が任意」 |
| `map to guest` / `guest ok` / `public` | `Never`、`no` | 共有ごとに「ゲストが入れる」 |
| `interfaces` と `bind interfaces only` | LAN の名か網だけ、`yes` | 無ければ「全部の口に聞く」 |
| 共有の `valid users` / `write list` | グループ（`@group`）で | 個人名だけなら「個人で付けている」 |
| `[global]` の `server role` | standalone か active directory domain controller | そのまま出す |
| `smb passwd file`、`passdb backend` | 場所だけ | 場所だけ出す（値は無い） |

終了コードは、直す物があれば 1。`report` の口の節に、`--smb FILE` があれば足す。テスト: 見本の smb.conf（良い物と悪い物）で表と終了コード。

実装で決めた細部（11-06。Opus が書き、Fable が確かめた）: 署名は `mandatory` と `required` を良い形とする。`map to guest` の値は出さない（`Bad Password` が「password を含む行は出さない」とぶつかるため）。interfaces は番地を出さず数だけ。個人名は出さない。`password` を含む行は「見るだけ」（行番号と「ある」）で終了コードに数えない。`passdb backend` の `user@` は伏せる。`server min protocol` が無い時は「SMB1 が通る」と出すが、Samba 4.11 以降の既定は SMB2 なので実際は通らない事が多い（書いて確かめるのが良い形）。AD DC では署名の既定が必須なので、`server signing` を書いていない AD DC で「署名が任意」と出るのは外れ（書いておくのが良い形）。`ipaddress` を使う（標準ライブラリ）。

### 3.3 `kagi app` — 係の机の画面（Flet の PC 版。11-06、作者「手元の Flet の PC 版であれば、サーバーの管理にも使える」）

seed と同じ Flet 1.1 で、係の PC の窓に一画面。網に出さない（Web 版は作らない。K-07）。kagi の本体は標準ライブラリだけのままで、画面は任意の依存（`flet` は seed の `app` の extra に既にある。`src/kagi/app.py` は `flet` を遅く import し、無ければ一行で言う）。

画面は一つ（`--dir` の作業の場所を上に出す）。四つの札と一つの釦。

| 札 | 中身 | 元 |
|---|---|---|
| 在庫 | 件数、期限切れ、30 日以内、抜け。表（id、何、中身）。値は無い | `inventory.check` |
| 口 | `ss` の写しのファイルを選ぶ釦 → 差の表（表に無い口、開いていない口、外向き）。無ければ「突き合わせていない」 | `ports` |
| 走査 | 場所を選ぶ釦 → `path:line  kind` の一覧。値は出ない | `scan` |
| 記録 | `verify` の結果（ok N か、落ちた行）。「一行足す」の小さな入力（actor、action、detail）→ `log add` | `audit` |
| 報告 | 釦。`report` の Markdown を作って `report-<日>.md` に書き、画面に出す | `report` |

- 命令: `kagi app [--dir DIR]`。`kagi app --web` は作らない。
- 文字は日本語（kagi の他の出力と同じ）。見た目は seed の theme と同じ種の色と `font_family="Roboto"`。
- テスト: 画面の関数が、在庫・口・走査・記録の結果を札の文字に変える所を、Flet を起動せずに確かめる（`build_cards(dir)` のような純粋な関数を一つ作り、それを試す）。`flet` が無い時に `kagi app` が終了コード 2 で一行出す事。
- 実装（11-06。Opus が書き、Fable が確かめた）: `build_cards` と `write_report` は純粋な関数。`ElevatedButton` は 1.1 に無く `FilledButton`/`OutlinedButton`。口と走査の札は「選ぶ」の隣に道を書く欄（ブラウザでは `pick_files` が道を返さないため）。口の札に `host` の欄。報告は `report-<日>.md`（同じ日は上書き）。鍵が無い時は記録の札に置き方の一行だけ。確かめの逃げ道: 環境変数 `KAGI_APP_WEB_PORT` がある時だけ 127.0.0.1 のその口でブラウザに出す。11-06 にブラウザで札が並ぶ所まで見た。日本語の字形が □ に見えた回があり、PC の窓での描画は作者が見る。

### 3.4 機械 — Linux の機械を入れる、見る。認証と鍵はひと組（11-06 夜）

作者 11-06: 「halo の設定は、あとにしよう。というか、Linux マシンのインストールや管理ができるようにして」「Linux マシンのインストールや運用は難しかったけど、AI 時代には逆に簡単になる」「特に認証はちゃんとやりましょう。そして、キーの管理もやりましょう」「この二つはセットでも問題ないはず」。

**考え方。** 難しかったのは、覚える事が多く、機械ごとに違い、確かめ方が人に付いていた所。AI の時代に簡単になるのは、人が「この機械は何の役で、誰が入れて、どの鍵で入るか」を表に書けば、入れる時の答えの文と、見た結果と表の差と、直す手の文を道具が書くから。人に残るのは、表を書く、画面でパスワードを打つ、盤を選ぶ、機械の鍵の指紋を目で比べる、直す手を読んで打つ、の五つ。kagi は機械を変えない。

**ファイル `machines.toml`（機械の表と鍵の表。人が書く）。** 認証（誰が入れるか）と鍵（どの鍵で入るか）を一つのファイルに並べる。

```toml
[[machine]]
host = "halo"                 # 機械の名
ssh = "halo"                  # ~/.ssh/config の名（無ければ host）
role = "家のデータベース"       # 一つの役
os = "debian-13"
users = ["dev"]               # 入れてよい人
admins = ["dev"]              # sudo を持ってよい人。入れる時は先頭が最初の管理者
keys = ["yniji-debpc"]        # 入れてよい鍵（[[key]] の id）
hostkey = "SHA256:…"          # 機械の鍵（ed25519）の指紋
lan = "192.168.1.0/24"        # 入れる時: ssh を通す網
profile = "server"            # 入れる時: server | desktop
encrypt = true                # 入れる時: 盤を暗号化する機械

[[key]]
id = "yniji-debpc"            # 在庫表にも同じ id で一件（期限と回す周期はそちら）
holder = "yniji"
pub = "~/.ssh/id_ed25519.pub" # 公開鍵のファイル。.pub だけを読む
fingerprint = "SHA256:…"      # pub があれば要らない
```

`value`、`private`、`password`、`passphrase` の欄があれば読まずに拒む（K-13）。`host` と `ssh` は英数字と `. _ -` だけで、先頭の `-` を許さない（ssh の引数に化けない）。指紋は公開鍵の中身の SHA-256 で、`ssh-keygen -lf` と同じ形。kagi が自分で計算する（標準ライブラリ）。`.pub` でないファイルと、`PRIVATE KEY` を含む物は読まずに拒む。

**命令。**

| 命令 | する事 | 終了コード |
|---|---|---|
| `kagi machine list` | 機械の表と、写しの有無 | 0 |
| `kagi machine script` | 機械で走らせる読むだけの sh の文を出す（人が読める。約 90 行） | 0 |
| `kagi machine collect --host H [--local]` | 写しを取り `facts/<H>-<日時>.txt`（600）に置く。ssh を使った時は記録に `machine.collect` を一行（署名の鍵があれば） | 0 / 2 |
| `kagi machine check [--host H] [--facts FILE]` | 写しを、機械の表・口の表・在庫表と突き合わせる。`--host` が無ければ全部の機械 | 直す物があれば 1 |
| `kagi machine fix --host H` | 直す手を sh の文で出す。**走らせない**。連載 2-02 の八つに当たる手（ssh の形、鍵、人と管理者、防火壁、口、入口、機械の鍵）には `【読んで確かめてから】` の印。印の無い手（更新、サービス、時計）は、打って写しを取り直して確かめる | 直す物があれば 1 |
| `kagi machine install --host H [--out DIR]` | 入れる時の三つのファイルを `install/<H>/` に書く | 0 / 2 |
| `kagi key list` | 鍵ごとに、持つ人、指紋、入れてよい機械、在庫表の期限 | 在庫表に無い鍵があれば 1 |
| `kagi key fingerprint FILE.pub` | 公開鍵の指紋 | 0 / 2 |

**写し（`collect`）。** 境界（§6）の「外に繋がない」の、ただ一つの例外。条件は四つ。(1) 人が命令を打った時だけ。(2) 入るのは人の ssh と人の鍵で、kagi は鍵を読まない。`BatchMode=yes`、`PasswordAuthentication=no`、`StrictHostKeyChecking=yes` で、尋ねられる形（パスワード、初めての機械）は全部落ちる。初めての機械は、人が自分で入って機械の鍵の指紋を確かめた後でないと取れない。(3) 機械に渡すのは決まった文（`SCRIPT`）だけで、標準入力で渡し、機械に置かない。文は読むだけ（テストが、変える命令の語が無い事を見る）。(4) 鍵を使った事として記録に一行。root でなくても走り、root の写し（人が `sudo sh` で走らせてファイルで渡す）なら見える物が増える。

**突き合わせ（`check`）の見る物。**

| 何 | 良い形 | 直す物として出す |
|---|---|---|
| 認証（ssh） | `PasswordAuthentication no`、`KbdInteractiveAuthentication no`、`PermitRootLogin no`、`AllowUsers` が表の人 | パスワードで入れる（書いていなければ既定の yes として）、尋ねて答える形で入れる、root がパスワードで入れる、鍵で入れない、AllowUsers に表に無い人 |
| 機械の鍵 | 写しの ed25519 の指紋 = 表の `hostkey` | 表と違う（入れ直したのでなければ、別の機械か、間に誰か居る）。表に無ければ指紋を出して「書く」（見るだけ） |
| 入っている鍵 | authorized_keys の指紋が全部、表の `keys` | 表に無い鍵、弱い鍵（DSA、RSA 2048 未満）。RSA 3072 未満は見るだけ |
| 鍵の表 | `keys` の id が `[[key]]` にあり、在庫表にも同じ id | `[[key]]` に無い、在庫表に無い（K-14）、表の指紋と pub の指紋が違う |
| アカウント | 入れるアカウント（uid 1000 以上、shell が nologin でない）が全部、表の `users` か `admins` | 表に無いアカウント（警察庁の「管理されずに残っていた不要なアカウント」）、パスワードが空（root の写し） |
| 管理者 | sudo の組が表の `admins` | 表に無い管理者、パスワード無しの sudo（root の写し） |
| 更新 | 更新 0、一覧が 7 日以内、unattended-upgrades が入り動く、再起動が要らない | それぞれ |
| 防火壁 | ufw が有効、か firewalld | 動いていない。nftables だけなら見るだけ（規則は見ない） |
| 口 | 写しの `ss -ltnp` = 口の表（`ports.compare` をそのまま使う） | 表に無い口、開いていない口、外向き。口の表にその機械が無ければ見るだけ |
| 時計 | NTP で合っている（K-11） | 合っていない |
| サービス、盤 | 落ちた unit が無い、表の `services` が動いている、85% 未満 | それぞれ。暗号化されていない盤は見るだけ。表に `encrypt = true` と書いた機械（個人情報を置く機械など）で暗号化されていなければ直す物 |
| 入口 | Caddy の入口が全部、入口の表にあり、`gate` と `lan` の入口に確かめる行がある | 上の「入口の表」 |
| データ | `data` の置き場が在る | 置き場が無い。大きさと盤の残りは見るだけ |

root でない写しでは、実際に効いている sshd の値（`sshd -T`）、他の人の authorized_keys、パスワードの状態、sudoers が見えない。その事を「見るだけ」の行で必ず言う。sshd の設定をファイルから読む時は、最初に出た値が効くとして読み（Debian は drop-in が先）、`Match` の中は見ない。

**入れる（`install`）。Debian 13 だけ。** 三つを書く。

- `preseed.cfg`: インストーラーへの答え。**パスワードと盤は書かない。** インストーラーが尋ね、人が画面で打つ・選ぶ（K-13。ファイルに秘密が無いので、LAN の HTTP で渡してよい）。root は止める（`passwd/root-login false`）。最初の管理者の `authorized_keys` に表の公開鍵を入れ、`/etc/ssh/sshd_config.d/10-kagi.conf` で鍵でだけ入る形にする（`late_command`。中身は base64 にして引用の入れ子を避ける）。公開鍵の後ろの注釈（メールや機械の名）は入れず、表の id を付ける。
- `firstboot.sh`: 入れた後に人が `sudo sh` で一度。sshd の確かめ、ufw（入る向きを閉じ、ssh は `lan` があればその網だけ、無ければ回数を絞る。**ssh を通してから有効にする**）、自動の更新、時計。何度走らせても同じ形。今ある機械に形を当てる時にも使えるが、鍵が入っていなければ sshd は変えない（入れなくなるのを防ぐ）。
- `手順.md`: 十二歩。人がやる事、kagi がやる事、人が確かめる事。機械の鍵の指紋を機械の画面で見て表に書き（歩 6）、初めての ssh で尋ねられた指紋と目で比べ（歩 7）、最後にパスワードでは入れない事を試す（歩 9）。

足りない物があれば書かずに拒む（半端な形で入れない）: `admins` が無い、`keys` が無い（鍵でだけ入る形にできない）、pub が無い、弱い鍵、`lan` が網でない、Debian 13 でない。

**表に足した欄（同じ夜）。** `services = ["seed", "caddy"]`（systemd で動いているべきサービス）、`user_services = ["glimmer"]`（写しを取る人の `systemctl --user` で動いているべき物）、`local = true`（この PC 自身。写しを ssh でなくここで取る）。写しには動いているサービスの一覧、起動した時、load、メモリ、盤の使用率が入る。表のサービスが動いていなければ「直す」に出て、手は `systemctl status …`（理由を見る）と `restart`。作者「linux の管理ができなければ、自然農法のアプリを動かすときに Claude に聞かないといけない」への形。

**入口の表 `[[door]]`（同じ夜。作者「deb2 は、公開用。でも特定の人しかアクセス出来ないようにしようと思ったら認証システムは必須」）。** 口の表（どの口が開いているか）の一段上で、外から来る入口ごとに、誰が、何で守られて入るかを書く。

```toml
[[door]]
host = "deb2"
site = "app.example.org"      # Caddy の設定の入口の名
who = "招待した人"             # 誰が入れるか（人の言葉）
auth = "app"                  # public | app | gate | lan
```

`public` は誰でも（認証無しが正しい）、`app` は裏のアプリが確かめる（招待コード、ログイン）、`gate` は前の Caddy が確かめる（basic_auth、forward_auth、Authorization の照合、mTLS）、`lan` は網で絞る（remote_ip）。写しは `/etc/caddy/Caddyfile` から**形だけ**を取る（入口の名、通す先、認証の行の名。値は取らない。テストが、見本の設定の中の偽の値が写しに出ない事を見る）。出す物: 表に無い入口（直す）、`gate` なのに確かめる行が無い（直す。誰でも通る）、`lan` なのに remote_ip が無い（直す）、表にあって設定に無い（直す。まだ置いていない入口）。`app` の入口は「アプリの中は見ていない」と必ず言う。kagi が見るのは設定の形までで、アプリが本当に確かめているかは外から試して見る。Caddy 以外（nginx など）はまだ無い。

**データの置き場 `data`（作者「halo は、データベース用。文字データでないデータの場合は容量が大きくなるし、管理が難しい」）。** 機械に `data = ["/srv/photos"]` と書くと、写しにその道の大きさと、その盤の使用率と残りが入る。置き場が無ければ「直す」（盤が繋がっていない）。道は文に埋めず、引数で渡す（文は変えない）。道の字は英数字と `. _ / @ + -` だけ。大きさを測るので、待つ時間を 10 分まで延ばす。

**deb2 用（作者「deb2 用も作って」）。** `deploy/deb2/` に、配備が済んだ後の口の表、seed の秘密の在庫の見本、機械と入口の表の見本、手順。配備の前に突き合わせると、8010 と 8560 の口、seed の二つの入口、seed と seed-app のサービスの六つが「直す」に出る。それが残りの配備の作業。

**机の画面（`kagi app`。作者「linux の管理のためのツールをつくって、flet で使えるようにしろ」）。** 三つの画面を上の釦で切り替える。

| 画面 | 中身 |
|---|---|
| 機械（最初に開く） | 機械ごとの釦（`halo 直す 9`、`よし`、`写し無し`）で選ぶ。選んだ機械の頭の一行、「写しを取る」「直す手を全部写す」「入れる時のファイルを作る」。直す物は一件ずつ、何・見た物・手（等幅の文）と、その手を写す釦。見るだけの行。「機械を足す」の欄（名、ssh、役、入れてよい人、sudo を持ってよい人、鍵の id、サービス、この PC 自身） |
| 鍵 | 鍵ごとの id、持つ人、指紋、入れてよい機械、在庫表の期限。「鍵を足す」（id、持つ人、`.pub` の道。秘密鍵は読まずに拒む） |
| 在庫・口・記録 | 前からの札（在庫、口、走査、記録、報告） |

画面から足した機械と鍵は `machines.toml` の末尾に一件ずつ書く（足した形を読めるか確かめてから。読めなければ書かない）。直す・消すはエディタで。画面は機械を変えない。写す釦は手の文を貼り付け用に写すだけで、走らせるのは人。窓が狭い時は窓の幅に合わせる。画面の中身を作る所は Flet を使わない関数（`machine_view`、`keys_view`、`add_machine`、`add_key`）でテストする。`kagi report` に「機械」の節。11-06 夜にブラウザで開いて、札と表と直す手の文が出る所まで見た。その時、前からあった「口」の札が灰色の塊になっていた（折り返す行の中に、幅を伸ばす欄があった）ので、欄の幅を決めて直した（走査と記録の欄も同じ）。

**確かめた物（11-06 夜、Fable）。** テスト 28 件（公開鍵の形の見本は対になる秘密鍵が無い偽物）。作者の halo（ssh、番地、dev、root でない）、deb2（ssh）、机の PC（`local`）の三台で写しを取り、突き合わせと直す手が出た。机の画面はブラウザで開き、機械を選ぶ、画面から halo の写しを取る、直す手が出る、鍵の一覧、まで見た（PC の窓での描画は作者が見る）。`preseed.cfg` は `debconf-set-selections -c` で文法を、`firstboot.sh` は `sh -n` で文法を、作ったファイルは `kagi scan` で秘密らしい文字列が無い事を見た。

**確かめていない物。** `preseed.cfg` と `firstboot.sh` を、本物のインストーラーと入れたての機械で通していない（仮想の機械で一度通すのが次。`手順.md` の頭にもそう書く）。Ubuntu（autoinstall）と RHEL 系（dnf、kickstart）は無い。root の写しの節（`sshd -T`、`passwd -S`、sudoers）は見本でだけ試した。

### 3.4b 連載「Claude と一緒に育てる Debian サーバー」との対応（11-06 夜。作者「ここと関係してきます」 https://aiseed.dev/debian-server/ ）

連載は、人が Claude と一緒に一台のサーバーを作って育てる手順。kagi は、その「良い形」に機械が今も合っているかを、何台でも同じ見方で確かめる道具。良い形の出どころは連載に置き、kagi の側で別の基準を作らない。Fable が第 4・5・10・11 章を読んで揃えた（本人の連載なので、違っていたら連載の側が正しい）。

| 連載の章 | 連載の形 | kagi が見る物・書く物 |
|---|---|---|
| 3 最小インストール | netinst、tasksel は SSH サーバーと標準ユーティリティだけ | `machine install` の `preseed.cfg`（`standard, ssh-server`。パスワードと盤は人が画面で） |
| 4 SSH という玄関 | ed25519 の鍵、合言葉を付ける、`PasswordAuthentication no`、`PermitRootLogin no`、`sshd -t` と `reload`、別の窓で確かめてから閉じる、退路（画面） | 認証（ssh）の行、入っている鍵と鍵の表、機械の鍵の指紋。直す手は同じ順（先に別の窓で確かめる、`sshd -t`、`reload`） |
| 5 守りの基本 | ufw は入りも出も既定は拒否、ssh を通してから有効に、出口は 53・123/udp・80,443/tcp、unattended-upgrades、fail2ban（`jail.local` に 10m・10m・5 回、`[sshd]`）、不要なサービスを止める、`ss -tlnp` | 防火壁（入る向き・出る向きの既定、fail2ban）、更新（自動の更新、再起動）、口の表との突き合わせ。`firstboot.sh` は同じ規則を同じ順で書く |
| 6 サービスという単位 | systemd の unit と timer | `services`、`user_services`、`timers`、落ちている unit |
| 9 外の世界に公開する | リバースプロキシ、公開しないも選択肢 | 入口の表（`[[door]]`）と Caddy の設定の形 |
| 10 データを守る | restic、`backup.service` と `backup.timer`、合言葉は `/etc/restic/backup.env`（600）、復元の演習 | `timers = ["backup"]` が止まれば直す物。`data` の置き場が無ければ直す物。合言葉は在庫表に一件（値は書かない） |
| 11 サーバーを育てる | 週 15 分の定例（`df`、`free`、エラー、失敗したサービス、ログイン試行、fail2ban、データベース）、先週の出力と比べる、月の保守 | `kagi weekly`（全部の機械の写しを取り直し、一枚の報告を `weekly-<日>.md` に書く）。写しに盤、メモリ、この 7 日のエラーの行数、落ちている unit。前の写しから増えた・消えた直す物を出す |

**連載と違えてある所（一つ）。** ssh の設定を書くファイルの名。連載は `/etc/ssh/sshd_config.d/99-hardening.conf`、kagi は `10-kagi.conf`。sshd は同じ項目が二度出ると**最初の値**を使い、Debian は `sshd_config.d/*.conf` を名の順で先に読む。最小インストールには他のファイルが無いので `99-` でも効くが、VPS の雛形に `50-cloud-init.conf`（`PasswordAuthentication yes`）のような物が在ると、`99-` の値は効かない。kagi の突き合わせは「最初に出た値」で読むので、その時は「パスワードで入れる」が消えずに残る。

**連載に在って kagi にまだ無い物。** needrestart、PostgreSQL の中（第 7 章）、restic の中身と復元の演習の記録、月の保守の日付の記録、`journalctl` のエラーの中身（数だけ見ている）。

**作者の三台で週の定例を走らせた結果（11-06 夜）。** halo 10、deb2 12、机の PC 3。三台とも、出る向きを既定で通していた（連載の形と違う所）。

### 3.5 `kagi check tokens` — 相手に出した token の台帳（11-06 夜。K-05、K-14）

アプリの門（seed のサーバーなど）に入る token を、誰に、どのアプリの、どの範囲で、いつまで出したか。台帳は `~/.config/aiseed/tokens.json`（`--file` で別の場所。サーバーでは `/var/lib/seed/gate/tokens.json`）で、書くのはアプリ（`seed token add`。seed の設計書 §5.9）。在るのはハッシュだけで、kagi はハッシュも出さない。token そのものの欄（`token`、`code`、`value`）があれば読まずに拒む（終了コード 2）。

出すのは、期限切れのまま取り消していない物（直す。終了コード 1）、期限の近い物（`--days`、既定 30）、生きている物、取り消した物。期限の無い物は期限切れと同じ扱い。机の画面では「鍵」の画面の下に同じ表。kagi は seed のコードを使わない（JSON を読むだけ）。機械に入る鍵（`[[key]]`）と、アプリに入る token（この台帳）が、同じ画面に並ぶ。

サーバーの記録（誰が何をしたか）は kagi の記録と同じ形なので、`kagi log verify --dir <記録の場所>` でそのまま確かめられる。

## 4. 署名の鍵

順に探す。(1) `$CREDENTIALS_DIRECTORY/kagi-log-key`（systemd の credential）。(2) `$KAGI_LOG_KEY_FILE` が指すファイル。どちらも無ければ `log add` と `log verify` は終了コード 2 で、鍵の置き方（手引き §3）を一行出す。鍵の中身は読んで HMAC に使うだけで、出力・ログ・例外のメッセージに出さない。ファイルの許可が `600` でなければ警告する。

## 5. テスト（`tests/kagi/`）

- 在庫表: 必須の欄の抜け、期限切れ、N 日以内、`value` 欄の拒否。
- 口: `ss` の出力の見本（IPv4、IPv6、`*`、プロセス名付き）と表の突き合わせの三種の差。
- 走査: 見本のファイル（偽の形の文字列。実際の鍵ではない）で種類だけが出て、文字列そのものが出力に無い事を `capsys` で確かめる。バイナリと `.git` を飛ばす事。
- 記録: 追記 → 検証 ok。一行消す → 落ちる。一文字変える → 落ちる。鍵を替える → 落ちる。鍵が無い → 終了コード 2。
- 報告: 一枚が出て、値を含まない事。
- 機械と鍵（§3.4）: 公開鍵の指紋、秘密鍵と値の欄の拒否、名の形、認証・鍵・アカウント・更新・口の差、写しを取る命令の形（鍵でだけ、確かめ済みの機械だけ）、読むだけの文に変える命令の語が無い事、入れるファイルにパスワードと盤が無い事。

## 6. 境界

- 外に繋がない。`ss` を自分で走らせない（人がファイルで渡す。計画書 §6 の 2）。例外は `kagi machine collect` 一つ（§3.4 の四つの条件: 人が打った時だけ、人の ssh と鍵で、読むだけの決まった文、記録に一行）。
- 機械を変えない。直す手は文で出し、走らせるのは人（sudo は人の手）。入れる時のファイルも、渡すのと走らせるのは人。 AI が動くアカウントに sudo を渡さない（作者 11-06 夜。連載 2-02 は決めていない所で、ここは連載より厳しい）。
- 鍵を作らない、回さない、発行しない。それは人の手（鍵の管理 §5 の歩 2・6）。読むのは公開鍵と指紋だけ。
- seed のコードに依存しない。seed の repo から切り出せる。

## 7. 変更の記録

- 2026-11-06: 初版（Fable）。
- 2026-11-06: §3.1 実装で決めた細部（Opus の報告から）。
- 2026-11-06 午後: §3.2 `check smb`（作者「これらもできるだけ実装しろ」）。
- 2026-11-06 午後: §3.3 `kagi app`（Flet の PC 版の画面）。
- 2026-11-06 夜: §3.4 機械（入れる、見る、直す手）と、認証と鍵の表。§6 の境界に例外を一つ（`machine collect`）。
- 2026-11-06 夜: §3.5 `kagi check tokens`（相手に出した token の台帳）。
- 2026-11-06 夜: §3.4b 連載との対応。防火壁の出る向き、fail2ban、控えの timer、この 7 日のエラー、前の写しとの比べ、`kagi weekly`。`firstboot.sh` を連載の規則に。
- 2026-11-06 夜: AI が動くアカウントに sudo を渡さない。`fix` の手に、連載の八つに当たる物の印。
