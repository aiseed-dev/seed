# 出典

**ここに無い資料を根拠に書きません。** URL は repo の文書（`docs/kagi 設計書.md`、`docs/kagi 配線図.md`、
`docs/鍵の管理の仕組み.md`）に在る物だけです。確認日はその文書の日付（2026-11-06）です。資料を足す時は、
読んでから番号を付けて足します。

## 1. 作者の連載「Claude と一緒に育てる Debian サーバー」

人が Claude と一緒に一台のサーバーを作って育てる手順。kagi の良い形の出どころ。章と kagi の行の対応は
`docs/kagi 設計書.md` §3.4b（第 3・4・5・6・9・10・11 章）。kagi の側で読んで揃えたのは第 4・5・10・11 章。
違っていたら連載の側が正しい。

- https://aiseed.dev/debian-server/

## 2. NIST SP 800-41 Rev.1（防火壁の指針）

§2.2.1 機械ごとの防火壁は同じ網の機械からも守る。§2.2.2 網の入口の防火壁はもう一枚の守り。§3.1 外に見せる
サーバーは別の口に。§3.4 防火壁の後ろに防火壁を置く形は一般には扱いにくい。

- https://csrc.nist.gov/pubs/sp/800/41/r1/final

## 3. 警察庁

令和 7 年上半期の情勢（2025-09）。ランサムウェアの被害 116 件のうち中小企業が 77 件。入口は VPN 機器 62%、
リモートデスクトップ 22%。原因に、安易な ID・パスワードと、管理されずに残っていた不要なアカウント。

- https://www.npa.go.jp/publications/statistics/cybersecurity/data/R7kami/R07_kami_cyber_jyosei.pdf
- 対策の資料（令和 8 年 1 月） https://www.npa.go.jp/bureau/cyber/pdf/R7countermeasures_leaflet.pdf
- 数字の転載（宮城県警） https://www.police.pref.miyagi.jp/cyber/pdf/r7-11-2.pdf

## 4. MITRE ATT&CK T1557.002（ARP）

ARP には相手を確かめる仕組みが無い。同じ網の機械は、他の機械の番地を名乗れる。

- https://attack.mitre.org/techniques/T1557/002

## 5. ヤマハ（ルーターの命令の説明。07 の「機能の例」）

LAN 分割、管理の口を絞る命令、口ごとのフィルター、ファームウェアの一覧。作者の家のルーターの資料で、
人の家のルーターには、その機種の資料を読む。

- `lan type` https://www.rtpro.yamaha.co.jp/RT/manual/rt-common/setup/lan_type.html
- LAN 分割機能 https://www.rtpro.yamaha.co.jp/RT/docs/lan-divide/index.html
- `httpd host` https://www.rtpro.yamaha.co.jp/RT/manual/rt-common/http_server/httpd_host.html
- `sshd host` https://www.rtpro.yamaha.co.jp/RT/manual/rt-common/setup/sshd_host.html
- `ip … secure filter` https://www.rtpro.yamaha.co.jp/RT/manual/rt-common/ip/ip_interface_secure_filter.html
- ファームウェアの一覧 https://www.rtpro.yamaha.co.jp/RT/firmware/index.php
- Web の画面の弱点 JVNVU#91161784 https://www.rtpro.yamaha.co.jp/RT/FAQ/Security/JVNVU91161784.html

## 6. NSA「家の網を守る最良の実践」（2023）

守りの弱い機器を強い機器から分ける。管理は中の網からだけ。本文は取れず、要約から読んだ（`docs/kagi 配線図.md` §2）。

- https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/3304674/nsa-releases-best-practices-for-securing-your-home-network/

## repo の中の材料

- `docs/鍵の管理の仕組み.md` §2（K-01〜15）、§3（機械の形）、§5（できることから）
- `docs/kagi 設計書.md` §3.4、§3.4b、§3.5、`docs/kagi 手引き.md`、`docs/kagi 計画書.md` §10、`docs/kagi 配線図.md`
- `docs/deb2 の配備.md` §0、`deploy/deb2/手順.md`、`deploy/deb2/*.toml`
- `docs/設計書.md` §5.9、§5.10、`docs/利用マニュアル.md` §11c、`docs/iPhone 版.md`
- コード: `src/kagi/cli.py`、`src/kagi/machine.py`、`src/kagi/install.py`、`src/seed/cli.py`（`seed token`）、
  `src/seed/server/gate.py`、`src/seed/app/admin.py`
