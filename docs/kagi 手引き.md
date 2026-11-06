# kagi — 手引き（2026-11-06。作者が確定するまで案）

読む人: 業務システムを守る係。やる事は三つ。在庫表と口の表を書く、kagi を走らせる、結果を見て「合っている」と言う。kagi は鍵の値を一度も読まないので、この手引きのどこにも値を書く所は無い。

## 1. 始める

```bash
kagi init --dir ~/kagi-data
```

`kagi` の命令は `pip install -e .` で入る。入れていなければ `python -m kagi` でも同じ。

`inventory.toml`（在庫表）、`ports.toml`（口の表）、`audit.log`（記録）ができる。三つとも素の文字で、エディタで開ける。

## 2. 在庫表を書く（鍵の管理 §5 の歩 1）

今ある秘密を全部、一件ずつ `[[secret]]` に書く。書くのは、名、種類、置き場、持つ人、役、作った日、期限、回す周期、なくした時、漏れた時。**値は書かない。** 置き場は「機械:パス」か「紙/金庫」の名。

探す所: サーバーの `/etc` と home、ルーターと VPN 機器の管理画面、ブラウザの保存、スクリプトの中、業者が置いていった物、退職者の物。見つけた物を全部書き、消す物も一度は書いてから消す。

走査で手伝わせる:

```bash
kagi scan /etc/seed ~/farm/seed deploy
```

出るのは `path:line  種類` だけ。出た場所の物が在庫表にあるか見る。無ければ足すか消す。

確かめ方: `kagi check inventory` が抜けも期限切れも出さない。

## 3. 記録を始める（歩 4）

署名の鍵を一つ作って置く。kagi は作らない（人の手）。

```bash
head -c 32 /dev/urandom > ~/.config/kagi/log-key
chmod 600 ~/.config/kagi/log-key
export KAGI_LOG_KEY_FILE=~/.config/kagi/log-key
```

この鍵も在庫表に一件書く（置き場 `pc:~/.config/kagi/log-key`、役「kagi の記録の署名」）。

鍵を使った事、在庫表を変えた事、口を変えた事は、その時に一行足す:

```bash
kagi log add --actor yniji --action inventory.add --detail deb2-seed-env
```

確かめ方: `kagi log verify` が `ok` を出す。試しに `audit.log` を写して一行消し、写しで `verify` が落ちる事を一度見る。

## 4. 口を突き合わせる（歩 3）

機械で口の一覧を取り、ファイルにして渡す（kagi は自分で機械に入らない）:

```bash
ss -ltnp > /tmp/halo-ss.txt
```

```bash
kagi check ports --host halo --ss /tmp/halo-ss.txt
```

出るのは三つ。表に無い口、表にあって開いていない口、外向きで表と違う口。表に無い口は、表に足すか、閉じる。

確かめ方: 差が無くなるまで。

## 4b. Samba の口を見る（鍵の管理 §5e）

Samba の機械の `/etc/samba/smb.conf` を写して渡す: `kagi check smb --conf smb.conf`。`include` の先は辿らないので、あればそのファイルも別に渡す。

出る「直す」: SMB1 が通る、署名が任意、ゲストが入れる（`map to guest` と共有ごと）、全部の口に聞く（`interfaces` と `bind interfaces only = yes`）、個人で付けている（`valid users` と `write list` は `@group` で）、`interfaces` に LAN の外を向く項目。「見るだけ」は `server role`、`passdb backend` の場所、`password` を含む行（中身は出さない）。

確かめ方: 直して `testparm -s` で読めるのを見てから、もう一度走らせて「直す物は無い」まで。`kagi report --smb smb.conf` で報告の口の節にも載る。

## 4c. 機械を見る（Linux の機械の今の形。設計書 §3.4）

`machines.toml` に機械と鍵を書く（`kagi init` の雛形に欄の説明がある）。書くのは、機械の名、役、入れてよい人（`users`）、sudo を持ってよい人（`admins`）、入れてよい鍵（`keys`）。鍵は `[[key]]` に、名と持つ人と公開鍵のファイル（`.pub`）。**秘密鍵とパスワードは書かない。**

```bash
kagi machine collect --host halo
```

```bash
kagi machine check --host halo
```

`collect` は、自分の ssh と自分の鍵で機械に入り、読むだけの文を走らせて、写しを `facts/` に置く。機械は変わらない。走らせる文は `kagi machine script` で読める。パスワードを尋ねられる機械と、初めての機械（機械の鍵をまだ確かめていない）には入らない。先に自分で `ssh halo` し、尋ねられた指紋を機械の画面の `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` と比べてから。

ssh で入れない機械は、文を持って行って走らせ、出力をファイルで渡す: `kagi machine script > k.sh`、機械で `sh k.sh > facts.txt`（root の写しは `sudo sh k.sh > facts.txt`。見える物が増える）、`kagi machine check --host halo --facts facts.txt`。この PC 自身は `kagi machine collect --host <名> --local`。

出るのは「直す」と「見るだけ」。直す物の手は:

```bash
kagi machine fix --host halo
```

sh の文が出る。**kagi は走らせない。** 読んで、機械の端末で一つずつ打つ。ssh の形を変える行は、先に別の窓から鍵で入れる事を確かめてから。終わったら `collect` と `check` をもう一度。

確かめ方: 「直す物は無い」まで。「見るだけ」の中の「表に指紋が無い」は、機械の画面で指紋を見てから `hostkey` に書く。

## 4d. 機械を入れる（Debian 13）

```bash
kagi machine install --host newbox
```

`install/newbox/` に三つできる。`preseed.cfg`（インストーラーへの答え）、`firstboot.sh`（入れた後に一度）、`手順.md`（十二歩）。あとは `手順.md` の通り。

- パスワードと盤は `preseed.cfg` に無い。インストーラーが尋ねた時に、画面で打つ・選ぶ。
- root は止まり、最初の管理者（`admins` の先頭）が sudo を持つ。ssh は表の鍵でだけ入れる。
- `admins` か `keys` が無い機械、弱い鍵（RSA 2048 未満）、Debian 13 でない機械には、ファイルを書かない。
- **本物のインストーラーではまだ通していない。** 初めての時は、消してよい機械か仮想の機械で。

## 4e. 鍵を足す、回す、外す（認証と鍵はひと組）

```bash
kagi key list
```

鍵ごとに、持つ人、指紋、入れてよい機械、在庫表の期限。在庫表（`inventory.toml`）に同じ id が無い鍵は「無い（K-14）」と出る。

- **足す。** 鍵は人が作る: `ssh-keygen -t ed25519 -a 64`（合言葉を付ける。持ち歩く物なら `-t ed25519-sk` で物の鍵に）。`[[key]]` に一件、機械の `keys` に id、在庫表に同じ id で一件（置き場、期限、回す周期）。機械へは `ssh-copy-id -i 新しい.pub 機械`。`collect` と `check` で「表に無い鍵」が出ない事を見る。
- **回す。** 新しい鍵を足す → 新しい鍵で入れる事を確かめる → 機械の `authorized_keys` から古い行を消す → 表の `keys` と `[[key]]` から古い id を外す → `check`。古い鍵のファイルを消し、在庫表の行に消した日を書く。
- **外す（人が辞めた、機械を無くした）。** その人の鍵の id を全部の機械の `keys` から外し、`users` と `admins` からも外す → `kagi machine check`（全部の機械）で、どの機械に残っているかが「表に無い鍵」「表に無いアカウント」として出る → `fix` の手で一台ずつ。
- どれも、終わったら `kagi log add --action key.add`（`key.rotate`、`key.remove`）を一行。

## 5. 一枚の報告

```bash
kagi report
```

在庫の数と期限、口の差、走査の数、記録の検証。これを読んで「合っている」と言えたら、次の歩（置き場、控え、根と二人。鍵の管理 §5）へ。報告は印刷して紙に残してもよい（K-10 の紙の隣）。

## 5b. 机の画面

`kagi app --dir ~/kagi-data` で、係の PC に窓が一つ開く（Flet の PC 版。網には出さない）。`flet` が要る（`pip install -e '.[app]'`）。
在庫・口・機械・走査・記録の五つの札と報告の釦。機械の札は、機械ごとの直す物と、「写しを取る（ssh）」「直す手を見る」の釦。口は `ss -ltnp` の写しを選び、走査は場所を選ぶ。記録は actor・action・detail を書いて「一行足す」（署名の鍵は §3）。
報告の釦は `report-<日>.md` を作業の場所に書き、画面にも出す。鍵の値は画面に出ない。

## 6. やらない事

- 値を kagi に渡さない。走査の出力に値が出る事は無いが、もし出たら kagi の外れなので止めて直す。
- `audit.log` を手で直さない。直す必要があったら、直した事を新しい行として足す。
- kagi に鍵を作らせない、回させない。それは人の手。
- 秘密鍵のファイルを kagi に渡さない。渡しても読まずに止まる。渡すのは `.pub` だけ。
- `kagi machine fix` の文を、読まずに丸ごと走らせない。

## 7. 変更の記録

- 2026-11-06: 初版（Fable）。
- 2026-11-06 午後: §4b Samba の口を見る（`kagi check smb`、設計書 §3.2）。
- 2026-11-06 午後: §5b 机の画面（`kagi app`、設計書 §3.3）。
- 2026-11-06 夜: §4c 機械を見る、§4d 機械を入れる、§4e 鍵を足す・回す・外す（設計書 §3.4）。
