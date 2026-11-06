# halo をデータベースのサーバーに（設計。2026-11-05 夜）

作者（11-05 夜、畑に出る前）: 「halo 機をデータベースサーバーにしようと思います。その設計にとりかかって。多くの人からアクセスが来るようになると思うので認証も本格的にやらないといけない。digitaldoor では、Apple の Wallet の認証を取得する勉強に入ってもいいのでは思っている。」
同じ晩のもう一つの決まり: **deb2 は公開用のサーバーなので、公開できる物しか置かない。** この二つで形が決まる。設計は Claude（Fable）、決めるのは事実と作者。実装は 11-08 の提出の後。

## 0. 先に、外れている所・確かめていない物

- **halo の盤は暗号化されていない**（NVMe は ext4 そのまま。11-05 夜に `lsblk` で見た）。→ 作者（11-05 夜）「halo のディスクは暗号化無しでいいでしょう。必要なものだけ暗号化すればいい」。作者「極端になるな。Wallet 用のサーバーは暗号化が必要かもしれない」。置く物ごとの表は §8 の 1。
- **halo に IPv6 のグローバルアドレスが付いている**（`2405:…`、enp194s0）。外から 22・8080・11434・11435 に届くかは未確認（`ufw` は sudo が要る。作者が `sudo ufw status verbose` で見る。届くなら、認証無しの Glimmer と sd-server が今この瞬間も外に向いている）。
- halo の 8080 が何か未確認（Glimmer の画面と推測）。
- halo に外付けの盤は今は繋がっていない（`/mnt` は空）。作者 11-05「外付けのディスクもあります。それをつなぎます」はまだ。控えの先が無い。
- 家の回線の上りの速さは未測定。「多くの人」が来る先は deb2 で、halo は後ろ、が前提（§2）。
- `auth.aiseed.dev` は PocketBase が動いている（`/api/health` が答える。digitaldoor の ninshou）。**パスキーを持つかは未確認**（§4）。Apple・Google のサインインは digitaldoor の文書では使う形。
- PostgreSQL の Debian 13 の版は Claude の記憶で 17。
- Apple Wallet の条件は digitaldoor の `docs/使い方.md`（2026-09-16）と `docs/鍵の管理の問題の整理.md` §8 に作者の整理があり、Claude が 11-05 夜に公開資料で確かめ直した（§5）。

## 1. 事実（11-05 夜に測った。halo は ssh で読むだけ、deb2 は配備の手順書 §1 から）

| | halo（192.168.100.6） | deb2（Cloudflare の後ろ） |
|---|---|---|
| OS | Debian 13、カーネル 7.1.8 | Debian、Python 3.13 |
| CPU・メモリ | Ryzen AI Max+ 395、32 スレッド、123 GB（Glimmer が約 100 GB） | 26 GB |
| 盤 | NVMe 1.7 TB、使用 222 GB、残り 1.4 TB、ext4、暗号化無し、swap 96 GB | 849 GB 空き |
| 開いている口 | 22、8080、11434（Glimmer）、11435（sd-server）。5432・8551 は閉 | 443（Caddy: office、aiai、git、auth、analytics、11-06 から seed） |
| 入っていない物 | postgresql、wireguard、tailscale、caddy、podman、docker（dpkg に無い） | — |
| 網 | LAN 192.168.100.6、IPv6 グローバル有り、無線は down | 公開の IP、Cloudflare proxied |
| 役目 | Glimmer、seed の絵（sd-server）。user の systemd で動く | 公開のサーバー。PocketBase（auth）も載っている |

## 2. 形: deb2 は入口、halo は本体

公開できる物しか deb2 に置かないので、**人の記録・口座の中身・研究室・写真の集まりは halo**、**deb2 には公開物と、入口の役だけ**。多くの人が来るのは deb2 で、halo は家の中から deb2 に向けて繋いだ線（WireGuard。halo から外へ張るので、家の router に口を開けない）の向こう。

```
人・AI ──HTTPS──▶ Cloudflare ──▶ deb2（Caddy）
                                   ├ 静的サイト site/、公開ファイル public/、一言      … 公開物。今のまま
                                   ├ PocketBase（auth.aiseed.dev）: 口座、パスキー、サインイン … 入口。中身は口座の名と鍵の公開鍵だけ
                                   ├ seed API（/api/read …）: 招待コードか口座で門        … 読みは Anthropic へ。記録は残さない（今のまま）
                                   └ 逆向きの proxy ──WireGuard──▶ halo
                                                                   ├ PostgreSQL（wg0 だけに listen）
                                                                   │   口座と記録の対応、Web 版の人の記録の索引、写真の索引、研究室の目録、客の token のハッシュ
                                                                   ├ ファイル: Web 版の人の記録（users/）、写真、研究室（lab）    … 記録は素の文字のまま（基本計画 §6）
                                                                   ├ Web 版（seed app --web）: deb2 から通す。users/ は deb2 から消える
                                                                   └ Glimmer、sd-server（家の中。token を掛ける）
                                                                   └ 控え: 外付けの盤（夜ごと）→ debpc の hdd2（週ごと）→ 切り離した盤
```

**何を DB に入れ、何をファイルのままにするか。** 記録の本体は人の物で、素の文字のファイルのまま（基本計画 §6。失っても PC の `~/seed/` から戻せる）。DB に入れるのは、**複数の人や機械が同時に書く物**と**索引**だけ。

| 物 | 今 | これから | 形 |
|---|---|---|---|
| 口座（誰が誰か）、パスキー、サインイン | 招待コードの TOML（deb2）＋ PocketBase（digitaldoor） | PocketBase（deb2）。招待コードは口座を作る門として残す | PocketBase の SQLite。公開鍵と呼び名だけ |
| 客の token（人が AI や機械に渡す。研究室 §5b） | 設計だけ | halo の PostgreSQL にハッシュ、scope、発行先の覚え | 発行と失効は本人の口座の頁から |
| 公開ファイル、一言、持ち主の token のハッシュ | deb2 のファイル（`public/`、`connections/`、`.owners.json`） | deb2 のまま（公開物）。halo に写しと索引 | ファイルが本体。DB は索引 |
| Web 版の人の記録（users/） | deb2 の `/var/lib/seed/users`（11-06 に動かすかは作者） | **halo** に移し、Web 版も halo で動かす。deb2 は通すだけ | ファイル（本人の形のまま）。索引だけ DB |
| 本人の記録（PC 版 `~/seed/`） | 本人の PC | 変えない | — |
| 研究室（lab: 図書室、原本、bulk） | debpc の hdd2 | halo（研究室 §7） | ファイル。目録は DB |
| 写真の集まりと索引（種の候補、本人の判定、座標、許諾） | 無い | halo | ファイル＋ PostgreSQL |
| 回数の上限（1 日の USD、読みの回数） | deb2 の `limits.py`（メモリ） | 口座ごとに数える。数は DB | PostgreSQL |
| `ANTHROPIC_API_KEY` | deb2 の `/etc/seed/env` | 読みが deb2 に残る間は deb2。halo に移すなら `/etc/seed/env` ごと | 平文の env（直す案は 11-08 の後） |

**PostgreSQL にする理由。** 研究室 §7 では「索引は SQLite 一つ、PostgreSQL は複数の人や機械が同時に書く段になってから」と書いた。作者の「多くの人からアクセス」で、その段に入る。口座ごとの回数、客の token の失効、Web 版の複数の人の同時の書き込みは SQLite の一ファイルでは詰まる。PocketBase は SQLite のままでよい（口座の数は招待の数で、書き込みは少ない）。

## 3. 認証（本格的に）— 三つの層

digitaldoor の鍵の階層（扉コントローラ仕様書 §5.2b: 管理者の鍵、発行者の鍵、端末の鍵、記録の鍵、更新の署名の鍵）に合わせる。seed の対応表（設計書 §13 の 12）は、これで埋まる。

| 層 | 誰が誰に | 形 | 5.2b の位置 |
|---|---|---|---|
| **人**（ブラウザ、スマホ） | 人が入口（deb2）に | **パスキー（WebAuthn）を主**に。許可も費用も要らず、iPhone・Android・PC で使え、フィッシングに強い。Apple・Google のサインインは任意の二つ目（digitaldoor の ninshou にある形）。招待コードは口座を作る門として残す（コードだけの人は今の通り動く）。ログインの印は PocketBase の token を httpOnly の cookie で。seed の `/api/*` は招待コードに加えて口座の token を受ける | 端末の鍵（パスキーの秘密鍵はスマートフォンの中。digitaldoor R-AC-21「資格情報を端末の鍵に結ぶ」と同じ） |
| **AI・機械**（seed の PC 版、買い手の AI、スマートフォンのアプリ） | 人が自分の口座から発行し、客に渡す | 客の token（研究室 §5b の通り。`Authorization: Bearer`、受ける側はハッシュだけ、scope は `read`／`mark`／`write`／`buyer`、seed の絵は `draw`）。発行・一覧・失効は口座の頁と `seed token` | 発行者の鍵（本人） |
| **機械同士**（deb2↔halo、halo の中） | 作者が機械に | WireGuard の鍵の対（halo→deb2）。PostgreSQL は wg0 だけに listen、`scram-sha-256`、TLS、役ごとの role（deb2 の proxy は読み書きできる表を絞る。superuser は halo のコンソールだけ）。Glimmer・sd-server に token。ssh は鍵だけ、パスワード認証は切る | 管理者の鍵（作者の ssh 鍵と sudo）、記録の鍵（盤の暗号化。今は無い） |

- **更新の署名の鍵**: git の commit と deb2 の clone に署名は無い。11-08 の後に、作者の鍵で tag に署名し、deb2 の更新はその tag だけ、を足す。
- **外に出るのは人が了解した物だけ**（基本計画 §6 の 5）は変えない。口座ができても、公開は本人が選んで送る。
- Wallet（Apple・Google）は seed には要らない。digitaldoor の扉の鍵の話（§5）。

## 4. PocketBase とパスキー

`auth.aiseed.dev` は PocketBase（11-05 夜に `/api/health` で見た）。digitaldoor の `docs/権限の申請の雛形.md` 101 行は「社員の端末のパスキー（WebAuthn）の登録を PocketBase の OAuth2 の上に重ねる形か、別の小さい物か」と書いていて未決。seed も同じ所に乗る（口座は一つ。seed と digitaldoor で別の口座を作らない）。
PocketBase 自身がパスキーを持つかは、11-05 夜の Claude の調べで下に書く（§4a）。持たなければ、パスキーの登録と検証だけを担う小さい FastAPI（`py_webauthn`）を deb2 に置き、検証が通ったら PocketBase の token を出す形（digitaldoor の「別の小さい物」）。

### 4a. 調べ（11-05 夜。公開資料）

- **PocketBase 本体にパスキーは無い。** 公式の docs（v0.41.1）の認証の方法は、パスワード、OTP（メールの一回コード）、OAuth2（Google、GitHub、Microsoft など）、MFA（この中の二つを組み合わせる）の四つ。WebAuthn の語は無い。
- **本家は GitHub を 2026-10-26 に archive し、開発を作者自身のサイト（ganigeorgiev.com/pocketbase）に移した。** 止まったのではなく移転（issue 7872「新しい家」。LLM の spam で PR を止めていた）。Go の import path は GitHub 側が v0.40.6 で止まり、それより新しい版（0.41.x）は新しい所だけ。pocketbase.io の docs はそのまま。→ **deb2 の PocketBase（auth.aiseed.dev）の版と、更新と安全の知らせをどこから受けているかを作者が確かめる**（GitHub の watch では届かなくなった）。
- パスキーを PocketBase に付ける道は第三者だけ: Go の拡張 kaiseo/pocketbase-passkey（2026-03。本家の作者は「vibe-coded な物を勧めたくない」と議論を閉じた）、fork doodlemania2/pocketbase（WebAuthn を認証の方法として持つが、ログイン開始で利用者の有無が分かる問題と、reset の流れの不具合が未解決）。
- **Claude の読み。** 拡張も fork も勧めない（本家が面倒を見ず、安全の問題が開いている）。形は二つ。(a) **パスキーは seed の側の小さい FastAPI（`py_webauthn`）**で登録と検証をし、通ったら PocketBase の token を出す（digitaldoor の雛形 101 行の「別の小さい物」。PocketBase は口座の台帳と OAuth2 のまま）。(b) 先に **PocketBase の MFA（OAuth2 ＋ OTP）**で始め、パスキーは (a) を次に。決めるのは作者。どちらでも口座は PocketBase 一つ。

出典（確認日 2026-11-05）: https://pocketbase.io/docs/authentication/ 、 https://github.com/pocketbase/pocketbase （archive の帯、README の移転の注意）、 https://github.com/pocketbase/pocketbase/issues/7872 、 https://github.com/pocketbase/pocketbase/discussions/7574 、 https://github.com/doodlemania2/pocketbase （issue 39、40）。

## 5. Apple Wallet（digitaldoor の側。seed には要らない。**置くのは halo でなく別の PC: §8 の 6、作者 11-05 夜**）

作者の整理（digitaldoor `docs/使い方.md` 316〜327 行、2026-09-16。`docs/鍵の管理の問題の整理.md` §8）が既にある。要点:

| 道 | 誰が | 条件 | 作者の 09-16 の結論 |
|---|---|---|---|
| パスキー（WebAuthn） | 誰でも | 許可も費用も要らない | 使える |
| Sign in with Apple | Apple Developer Program の会員（99 USD/年） | App ID + Services ID。得られるのはメールと名前 | 使える |
| Wallet の鍵（Home Key / Aliro） | 錠の製造者と Apple の契約 | Aliro の読取機、日本に Aliro の錠が無い（2026-09） | **今は無理** |
| Apple Wallet Access Program（社員証・ホテルの鍵） | Credential Manager（基盤の提供者）、Credential Provider（錠の製造者）、Participating Provider（建物の持ち主） | Credential Manager は稼働率 99.99%、複数リージョン、P1 を 15 分、経営幹部のスポンサー、読取機の Apple の認証。窓口 access-partnerships@group.apple.com | 民泊・貸家は、日本の Credential Manager の客（Participating Provider）として入る形。自分で Credential Manager は別会社・別規模 |
| NFC & SE Platform（iOS 18.1 から日本も） | 家の鍵なら製造者かその提携先。会社の Developer アカウント | Apple との契約（料金を含む）、NDA、Apple Business Register、脆弱性の方針、アプレットの認定試験所の審査 | 費用と期間は非公開。申し込むか未決 |

digitaldoor の未確認（同 §8 119 行、00_core.md、開発のシナリオ 86 行）: 扉の製造者が「家の鍵の製造者」に当たるか、Aliro の鍵を財布に載せる手引き CR-31968 の中身、発行者の鍵を管理者が持てるか（R-AC-20 の要）。

**Claude の読み。** 「勉強に入る」の順は、費用の無い物から。(1) パスキー: seed と digitaldoor の両方で今すぐ、同じ ninshou で。(2) Developer Program（99 USD/年）: Sign in with Apple と、Wallet の**パス**（会員証・入館証の形。NFC の鍵ではない。Pass Type ID の証明書で自分で出せるかは §5a）。(3) Wallet の**鍵**: 日本の Credential Manager が現れるのを待つか、Aliro の錠が出るのを待つ。自分で契約する段ではない（作者の 09-16 の結論と同じ）。11-05 夜に公開資料で確かめ直した物は §5a。

### 5a. 公開資料で確かめた物（11-05 夜。Opus が WebSearch で調べ、Fable が読んだ）

作者の 09-16 の整理は今も合う。変わった所と、09-16 に無かった数字:

- **Aliro 1.0 は 2026-02-26 に公開された**（CSA）。仕様書は無料（download request の頁）。認定は認定試験所（UL Solutions、Allion）経由で、「認定と商品化の段階」。最初の認定製品は「2026 後半、iOS 27 と同時か」（仏の報道の予測）。日本の Aliro の錠は未確認のまま。
- **CSA の会費**: Adopter 7,500 USD/年 ＋ 認定 3,000/製品、Participant 21,500/年、Associate 0/年（白ラベルだけ）。会社向けの登録で、個人の記載は無い。
- **Aliro の SDK**: ESP32（esp-aliro、2026-07、NFC だけ）、Nordic、Silabs。Silabs の手順では、Matter の QR で Apple Home に足すと Wallet にホームキーが入る（開発機は「Uncertified Accessory」を Add Anyway で通す）。**開発環境の話で、製品として配る段ではない。Apple が認定無しの Aliro の錠にホームキーを出し続けるか、日本の iPhone で効くかは未確認。**
- **Home Key（HAP の錠）を正規に出す道**: MFi Program（法人名・D-U-N-S・会社のメール。99 USD/年。HAP の仕様と認定は NDA の中）。個人では閉じている可能性が高い（推測）。
- **Access Key**: 09-16 の整理の通り（questionnaire → Apple Business Register、リーダは DESFire／Seos／Aliro ＋ ECP v2.3 ＋ Apple の IOT 認定、サーバは 99.99% と P1 15 分）。費用の記載は無い。日本の例: 三井不動産のホテル 3 軒の部屋の鍵（Travel Voice）。
- **Pass（PassKit）**: Developer Program（個人可、99 USD/年）で Pass Type ID と証明書を自分で作り、**バーコードのパス（会員証・チケット）はそのまま出せる。NFC を付けるには Apple の審査の entitlement**（developer.apple.com/contact/passkit。VAS 認定の読取機が前提。理由無しの却下の報告あり）。
- **NFC & SE Platform**: 日本は対象（iOS 18.1 以降。Apple Japan の 2024-08 の発表）。申し込みは Developer Program の Account Holder が request form から。Apple Business Register に「organization」を登録、Apple と商業契約（料金を含む）＋秘密保持、アプレットは認定試験所の審査。**金額は非公開。個人が通るかは未確認。**
- 逆解析の実装 HomeKey-ESP32（rednblkx、HomeSpan ＋ PN532）で自宅の扉に Home Key を入れている人はいる。非公式で、配る・売るには使えない。

**読めなかった物**: support.apple.com のホームキーの案内の本文（国の注記）、Wallet の鍵の国別の一覧、MFi の Home Key 固有の条件と費用、NFC & SE と Access Program の料金（非公開か NDA）、AppleInsider の Aliro の記事（403、抜粋だけ）。

**Claude の読み（digitaldoor の側）。** 「勉強に入る」なら入口は **Aliro の仕様書（無料）と ESP32／Silabs の SDK で、Matter の試験機に NFC の読み取りを足して Apple Home 経由でホームキーを試す**、が今日からできる唯一の道。認定（CSA 会員 ＋ 試験所）と Wallet の正式な対応は、日本に Aliro の錠が出て、Apple が認定無しの錠をどう扱うかが見えてから。費用の無い物（パスキー）と 99 USD の物（Developer Program のパス）はその前にできる。

出典（確認日 2026-11-05）: mfi.apple.com（how-it-works、enroll、faqs）、register-docs.apple.com/apple-pay/access/program-guide（requirements、next-steps、participant-roles）、support.apple.com/guide/security/sec30bdef041、csa-iot.org（Aliro 1.0 の発表、become-member、specifications-download-request）、ul.com（Aliro の試験）、docs.silabs.com/aliro/2.0.0（Apple Home demo）、developer.espressif.com（esp-aliro 2026-07）、developer.apple.com（programs、wallet/get-started、walletpasses の nfc 辞書、support/nfc-se-platform、forums thread 773982）、apple.com/jp/newsroom 2024-08、travelvoice.jp（三井不動産）、macrumors.com 2026-02-26、github.com/kormax/apple-home-key、github.com/rednblkx/HomeKey-ESP32。

## 6. 控え（基本計画 §6 の 6「控えは切り離し」）

- 夜ごと: `pg_dump`（PostgreSQL）と `rsync`（users/、写真、lab）を halo の外付けの盤へ。盤は LUKS で暗号化し、鍵は作者だけ。
- 週ごと: 同じ物を debpc の hdd2 へ（家の中の二台目）。
- 月ごと: 盤を一つ切り離して別の場所へ（切り離した物は攻撃が届かない）。戻せるかを月に一度試す（戻せない控えは控えではない）。
- 口座（PocketBase）は deb2 にあるので、その控えも同じ輪に（PocketBase の `pb_data` を halo へ引く）。

## 7. 順（11-08 の提出の後。事実が決める）

| 段 | する事 | 決める事実 |
|---|---|---|
| 0 | 11-08 までは halo を触らない。Glimmer・sd-server は動かしたまま | 提出が先 |
| 1 守る | `sudo ufw status`、IPv6 の口、ssh のパスワード認証、11434・11435 に token、外付けの盤を繋いで LUKS | 外から届くか。届くなら 1 が最初 |
| 2 繋ぐ | WireGuard（halo→deb2）、PostgreSQL 17 を halo に（wg0 だけ）、role を分ける、控えの輪を回す | 線が張れるか。pg_dump が戻せるか |
| 3 入口 | PocketBase にパスキー（§4a の結果で、PocketBase 自身か小さい FastAPI か）。seed の `/api/*` が口座の token を受ける。招待コードは門として残す | PocketBase がパスキーを持つか |
| 4 移す | Web 版を halo で動かし deb2 は通すだけ（users/ が deb2 から消える）。客の token（`seed token`） | 家の回線の上りで Web 版が持つか |
| 5 集める | 研究室と写真の集まりを halo へ。索引を PostgreSQL に | 盤と控えが先に在るか |

## 8. 決めること（本人。それぞれ、何の事実で決まるか）

1. **halo の盤の暗号化（作者 11-05 夜「暗号化無しでいいでしょう。必要なものだけ暗号化すればいい」→ Claude が「記録は暗号化しない」まで振り切った → 作者「極端になるな。Apple のドアや社員証の Wallet 用のサーバーは暗号化が必要かもしれない。客観的に考えてみろ」）。** 盤ごとか、物ごとかは、置く物ごとに「誰が困るか」「誰が求めるか」で決まる。表（11-05 夜。Apple の資料は Claude が読んだ）:

| halo に置く物 | 読まれて困るのは | 求める物 | 暗号化 |
|---|---|---|---|
| seed の作者の記録（観察、写真、座標） | 作者 | 無し | 盤の上は無し。持ち出す控えの盤は LUKS |
| seed の Web 版 `users/`（招待の人の記録。座標と写真） | 他の人 | 個人情報保護法の安全管理措置（技術的措置の手法は例示で、暗号化を義務とは書いていない。例示の追加を見直し中、2026-10 の事務局資料） | 他人の記録を置く段で、暗号化した区画（LUKS の一区画か fscrypt）に。盤を抜かれて読める形にしない |
| PocketBase の口座（メール、パスワードのハッシュ、token） | 他の人（seed と digitaldoor で共通の口座） | 同上 | 同じ区画に |
| digitaldoor の発行者の秘密鍵 | 扉の持ち主全員 | digitaldoor R-AC-11: 取り出せない場所（SE、HSM）。盤の暗号化では足りない | 盤でなく SE/HSM |
| digitaldoor の Wallet 用の発行者サーバー（credential、利用者の識別子、Apple との mTLS の鍵） | 扉の持ち主と利用者 | Apple の Platform Security の資料: Apple 側は HSM で包み直し、相手とは mTLS か JWT、credential は HSM の外で平文にならない。**パートナー側の保存の条件は、その資料には無い。Access Program の契約と審査で決まる（未。digitaldoor §5 の読み）。** Aliro の条件も未 | **halo に置かない（§8 の 6）。** 別の機械で、盤ごと＋SE/HSM |
| Ollama のモデル、研究室の公開資料 | 誰も | 無し | 無し |
| 持ち出す控えの盤 | 上の全部 | 家の外に出る | LUKS、鍵は作者だけ |

**それで決まる形。** 11-08 までは今のまま（halo にあるのは作者の記録と作者一人の口座。他人の記録は deb2 の `users/` に留まり halo には来ない）。他人の記録と口座を halo に移す段（§7 の 2）までに、暗号化した区画を作る。Wallet 用のサーバーは halo に置かない（§8 の 6）ので、halo の盤ごとの暗号化を今やる理由は無い。他人の記録と口座の区画だけ（事実: 区画を切るなら、入っている物が 222 GB の今の方が、記録が増えてからより安い。LVM か、`fscrypt` でディレクトリ単位）。鍵と token のファイル（WireGuard の秘密鍵、客の token の表）は区画とは別に `systemd-creds` で（halo で確かめた: systemd 257、`/usr/bin/systemd-creds` あり。`age` は無い。TPM が使えるかは `systemd-creds has-tpm2` で見る、未）。
   - 出典: Apple Platform Security「Access（Wallet のキー）のプロビジョニングのセキュリティ」 https://support.apple.com/guide/security/sec75f6d5040/web。digitaldoor `docs/要求仕様/00_core.md` R-AC-11・R-AC-13・R-NW-01、`docs/使い方.md`「ディスクを暗号化するかは持ち主が選び、その miniPC の覚え書きに書く」。個人情報保護委員会 事務局資料（2026-10、安全管理措置の手法の例示の追加） https://www.ppc.go.jp/files/pdf/261028_shiryou-2-4-3.pdf。
2. **deb2 と halo の線。** WireGuard（Claude の案。家の router に口を開けない）か Cloudflare Tunnel か。決まるのは、halo から外へ張れるか（UDP が通るか）。
3. **口座は PocketBase 一つ**（seed と digitaldoor で共通）でよいか。
4. **Web 版を halo で動かす**（deb2 に users/ を置かない）か、11-06 の形のまま（deb2 に客の記録が残る）か。決まるのは家の回線の上り。
5. **Wallet の勉強の順**（§5 の Claude の読み）でよいか。Developer Program の 99 USD/年を払う時期。
6. **Wallet 用のサーバー（digitaldoor の発行者の機械）は別の PC に（作者 11-05 夜「Wallet は別の PC に置いた方がいいでしょう。よく考えてみろ」→ 決まり）。** Claude の外れ: 前の返事で R-AC-13 を読みながら、halo に置く前提の表を書いた。別の機械になる理由は digitaldoor の決まりと halo の事実で、意見ではない。
   - **digitaldoor R-AC-13**: 発行者の秘密鍵と扉の判断・記録の機械は、外の網に向いたサービス（ウェブ、予約、外部との連携）と同じ機械・同じ仮想化の基盤に置かず、役割ごとに分けた機械に。一台が止まっても他の扉の判断は続く。同じ形の予備の機械と、イメージから一つの手順で戻す復元を持つ。**R-AC-11**: 発行者の秘密鍵は取り出せない場所（SE、HSM）に。**R-AC-09**: 顧客ごとに別の発行者の鍵。
   - **halo の事実**: 実験の機械（Glimmer、sd-server、絵の生成、研究室、これから Web 版と PostgreSQL）。口が四つ開き、認証無しの口が二つ。user の systemd で起動と停止を繰り返す。**Claude のエージェントが ssh で入り、これからは実装も動かす機械**で、AI が書いたコードが走る。扉の鍵の隣に置く物ではない。再起動や実験で止まる機械に、扉の可用性を繋げない。
   - **Apple の審査**: パートナー側の条件は未読だが、審査に出す機械は「役目が一つで、口が少なく、鍵が SE/HSM にある」方が説明も確かめも短い。123 GB の研究の機械は説明が長くなる。
   - **halo の側で決まる事**: 盤ごとの暗号化は要らない（§8 の 1）。halo に置く他人の物は seed の記録と口座だけで、区画の暗号化で足りる。deb2 の PocketBase の口座を seed と digitaldoor で共通にする（§8 の 3）のはそのまま。口座（誰が誰か）は入口の物で、扉の鍵の発行は別の機械の物、という分け方。
   - **別の PC は何か**: digitaldoor の言葉では発行者の機械（事業所サーバー、miniPC。`skills/door-minipc`）。要る物: 盤ごとの暗号化（LUKS、TPM2 で自動解錠）、発行者の秘密鍵の置き場（miniPC の TPM 2.0 で R-AC-11 の「取り出せない場所」に足りるか、別の HSM か。**Apple と Aliro の条件を読んでから決まる。未**）、外の網に向く口は Apple との mTLS だけ、同じ形の予備とイメージからの復元（R-AC-13、R-AP-24）。勉強の順（§5）は、この機械を買う前に Aliro の仕様書と Access Program の条件を読む所から。
   - 確かめ方: digitaldoor `docs/要求仕様/00_core.md` の R-AC-09〜13 を作者が読み直す。halo の口は `ss -ltnp`（11-05 夜に読んだ物。§0）。

## 9. 変更の記録

- 2026-11-05 夜: 初版（Fable）。halo を ssh で読み、deb2 の auth が PocketBase であることを確かめ、digitaldoor の Wallet の整理を Opus が読んだ。
- 2026-11-05 夜: 盤の暗号化は「必要な物だけ」（作者）→ Claude が「記録は暗号化しない」まで振り切り、作者「極端になるな。客観的に」→ §8 の 1 を置く物ごとの表に。§0。
- 2026-11-05 夜: Wallet 用のサーバーは別の PC（作者。digitaldoor R-AC-13・R-AC-11 がそう決めている。Claude は読みながら halo に置く表を書いていた）。§8 の 6、§8 の 1 の表と「決まる形」、§5 の頭。
- 2026-11-06: 「本人未読」「本人未確認」の印を外した（作者「本人未読を書くな」）。出典は url と日付だけ。
