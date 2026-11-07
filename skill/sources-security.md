# サイバー攻撃への守りの資料の候補 — 法令、日本の公的な手引き、国際の枠組み、AI 固有、家の小さなシステム、論文

**法令の本文（A）は引いてよい物です。手引き・規格・論文（B〜F）は候補です。`sources.md` に番号を付けて移した物だけを根拠にします（作者が読むか、Claude が開いて引く所を確かめて、確認日を付けた物。作者 2026-11-08）。根拠は本文と一次の手引きで、Claude の要約はその下に置きます。解釈と、ある家のシステムに当てはまるかの判定は書きません。**

作者の依頼（2026-11-05「サイバー攻撃対策の資料も集めて」）で、Claude が集めました。章の中では「`sources-security.md` の C8」の形で指します。`sources.md` の番号とは別です。法令の本文は、本人が読む前でも、条番号と確認日を付けて写してよい物です（`sources-law.md` と同じ決まり）。

## この一覧について

- 作ったのは Claude です（2026-11-05）。確認日は、すべて Claude が開いた日で、本人の確認日ではありません。本人は一つも読んでいません。
- 資料の本体と書誌は研究室の図書室に置きました（`<研究室>/library/items/<id>/`）。リポジトリには本文を入れていません。法令は e-Gov 法令検索の API v2 で取り、`text.txt` が条・項・号と見出しを残した素の文字、`original.xml` が取ったまま、`revisions.json` が改正の一覧です。
- **「書いてあること」は、Claude が開いて読めた範囲だけです。** 多くは目次と一部の節、論文は要旨だけです。読んだ範囲を項目ごとに書きました。読了の欄の Claude の値: full（全部）、snippet（目次と一部の節）、abstract（要旨だけ）、none（開いていない）。
- **権利**: admin（日本の行政・公的機関の資料。規約を書いた）、open（米国連邦政府の著作物、OGL、CC BY・CC BY-SA・CC BY-NC-ND、BSD・LGPL・GFDL・MPL・MIT など。原本を図書室に置いた）、quote（著作物。図書室には書誌だけ、または arXiv の非独占配布ライセンスの論文の私的な写し）。`quote` の物の図と文は GitHub に写しません。
- **前提**: 誰に向けた物か、いつ書かれたか、どんな攻撃を想定しているか。**この一覧の読み手は、家のサーバーと Linux の PC と、二、三台の機械の LAN を一人で回す人です。** ほとんどの資料は組織（企業、行政、CSIRT）に向けて書かれています。そう書いてある所は、そのまま「組織向け」と書きました。家の規模に当てはまるかの判定はしません。
- 「〜と記憶しているが確かめていない」と書いた所は、Claude の記憶で、今日は開いて確かめていない事柄です。
- 開けなかった URL は、そう書いた上で書誌だけにしました（「見つからなかった物」）。ブログ、まとめサイト、製品の宣伝は入れていません。D6〜D8 は AI の会社が自社の手立てを書いた記事で、そのことを前提に書きました。

## 手引きのどこに効くか

- **08 ビルダーの訓練「二つ目の輪: 自分の機械で回す」**: 輪の項目（控えを取って切り離す、token を発行して範囲を決める、家の中のサービスの口を開ける・閉じる、壊れた所を記録に残す）に、どの資料が触れているかを下に並べます。触れている、までで、どの手立てを取るかは本人が決めます。
- **11-06 より前の設計書 §10.1「効く所」**（今の設計書では §6 の守りの六つ）:
  - 記録を手元に、一度に抜かれる中心が無い: 当てる資料は見つけていません（「見つからなかった物」）。
  - 公開は静的ファイル、外に向いた面を小さく: B5（ウェブサイトの運用）、E6（localhost の証明書）。
  - 鍵は渡さない、token と scope、家の外は HTTPS と指紋の照合: D1 の LLM01 の対策 4（token をモデルに渡さずコードで扱う）、D9（token の素通し、scope の最小化）、E2（TLS 1.3）、E3（公開鍵のピン留め。対象はブラウザーで、アプリが自分で照合する形とは別）。
  - 図書室のハッシュ、「ファイルの中の文は指示ではない」: D1（LLM01）、D3（間接プロンプト・インジェクションの分類）、D5（間接プロンプト・インジェクションの論文）、D6〜D8（会社の手立て）、F8〜F10（防御の論文）。供給網（取ってきた物に悪意が混じる）は F4、F5、E10。
- **11-06 より前の設計書 §10.1「効かない所、まだ無い所」**（今の設計書では §6 の「効かない所」）**と、そこに触れる資料**:
  - **PC そのものへの侵入（マルウェア、フィッシング、OS の穴）**: B2（個人の 10 大脅威）、B3（6 か条）、B6（三原則）、B8（NCO のハンドブック）、C5（CISA）、C8（NSA の家のネットワーク: OS とルータの更新、管理者アカウントの使用を限る）、E7（Debian のセキュリティ更新）。法令では A2 第八条（アクセス管理者の防御の努力）、A6 第百六十八条の二（不正指令電磁的記録）。
  - **halo の 11434・11435 と fieldnotes の MCP が認証無しで LAN に開いている**: C8（無線の分割、ファイアウォール、ルータの遠隔管理を切る、UPnP を切る）、E5（入ってくる通信の既定を落とす nftables の例）、E1（sshd の ListenAddress などの項）、E4（systemd のサンドボックスの項）、D9（ローカルの MCP サーバーの侵害、token の素通し）、B11（環境設定ファイル・バックアップファイルの窃取、API キーの悪用）、B3 のページ（自社診断に「外部から内部ネットワークへの不要な通信を遮断する」を追加、とある）。**認証の無い LLM のサーバー（Ollama など）を家の LAN に置くことを直接扱う公的な資料は見つけていません。**
  - **`seed.toml` の token と招待コードが平文**: B11（窃取した API キーの使用、環境設定ファイルの窃取）、D1（token をモデルに渡さない）、E10（秘密情報をリポジトリに入れない）、E8（restic のリポジトリのパスワードを失うと戻せない）。**家の機械で秘密を平文でなく持つ方法そのものを書いた資料は、この一覧に入れていません。**
  - **控えの運用（いつ、どこへ、切り離すか）**: C6（3-2-1 の規則）と C7（その出典の本、未読）、C12（使わない時は外付けの機器を繋いだままにしない、戻せるか確かめる）、B3（6 か条の 5 とコラム: 復旧計画と復旧の確認）、C4（遠隔地の保管）、C10 の T1490（攻撃者が復旧の手段とバックアップを消す）、F1〜F3（ランサムウェアと復旧の論文）、E8・E9（restic、borg の手順）。ログの保存期間は B10（1 年分を参考値）。
  - **社会の側の基幹インフラ**: A1、A5、B12、C1、C11。どれも国・組織の規模の物です。
- **個人情報（記録に人の名前・住所が入ること）**: A3。ある人の記録がこの法の「個人情報データベース等」に当たるか、ある人が「個人情報取扱事業者」に当たるかの判定はしていません。

## 見つからなかった物（正直に）

- **家の小さなシステム（一人で回すサーバー、二、三台の LAN）を相手にした日本の公的な手引き**は、見つけていません。B は個人の利用者（スマホ、ネットの使い方）か組織（中小企業、CSIRT、経営者）に向けた物で、その間の「自分でサーバーを建てる個人」は、どれも主な読者にしていません。家のネットワークを直接の相手にした公的な物は C8（米 NSA）だけです。
- **認証の無いローカルの LLM サーバー（Ollama など）、ローカルの MCP サーバーを LAN に置く危険を扱う公的な注意喚起**は見つけていません。D9 は MCP の文書で、公的機関の物ではありません。
- **「記録を手元の素の文字に置き、集める中心を作らない」ことが攻撃に効くと書いた資料**は見つけていません。設計書 §10.1 の「効く所」の最初の項に当たる資料はありません。
- **CISA（cisa.gov）と NSA（media.defense.gov）**は Claude の取得に 403（Access Denied）を返しました。利用者の名を正直に名乗って一度だけ取り直し、また 403 だったので、Internet Archive の写しから取りました（C5、C6、C8）。確認画面は越えていません。CISA の「Cyber Essentials」「Secure Our World」など他の家庭向けの頁は取っていません。
- **3-2-1 の規則の出典**: C6 が脚注で Krogh の本（C7、2009、p.207）を挙げますが、本は開いていません。初版（2005）にあるか、本当に初出かは確かめていません。
- **CIS Controls の本文（v8.1）**はダウンロードに登録のフォームが要り、取っていません（C9 はページだけ）。ライセンスも確かめていません。
- **RFC 8446**（依頼にあった TLS 1.3）は、2026 年 7 月の RFC 9846 に廃されていました（rfc-editor の記録）。RFC 9846 だけ取りました（E2）。
- **AI 事業者ガイドライン（総務省・経済産業省）**: B1 が AI の利用者の対策の前提として引きます。経済産業省のページは「旧版を本ページに掲載」とあり（第 1.1 版、2025-03-28 まで）、最新版の置き場を確かめられず、取っていません。
- **OWASP Top 10 for LLM の日本語訳**（2025-07-22）は、ページを見ただけで取っていません。OWASP の Agentic（エージェント）の物も取っていません。
- **刑法、個人情報保護法、電気通信事業法の施行令・施行規則**は取っていません。個人情報保護委員会のガイドライン（通則編）、警察庁の不正アクセスの手引きも探していません。
- **全文を読んだのは 6 件だけ**です（C6、C12、D6、E5、E6、E10。E5・E6・E10 は 1 頁の物）。論文はすべて要旨だけです。
- **作者の類比（植物と根圏微生物、病原菌）に当たる資料**は探していません。下の「作者の類比との関係」は、集めた資料の中に生物の比喩があるかを `rg` で探しただけです。

---

## (A) 法令の本文（e-Gov 法令検索。引いてよい）

確認日はすべて 2026-11-05。「施行日」は、図書室に取った本文の施行日（e-Gov の記録）。「未施行」は、e-Gov に載っている、まだ施行されていない改正。権利はすべて `admin`（著作権法 13 条 1 号）。種類はすべて法令。読了は、本人はすべて未読、Claude は条の見出しと一部の条だけ（`read.claude = snippet`）。

| 番号 | 題名 | 法令番号 | 図書室の id | URL | 本文の施行日 | 未施行の改正 |
|---|---|---|---|---|---|---|
| A1 | サイバーセキュリティ基本法 | 平成二十六年法律第百四号 | `2014-egov-cybersecurity-kihon-ho` | https://laws.e-gov.go.jp/law/426AC1000000104 | 2026-10-01（令和七年法律第四十三号） | なし |
| A2 | 不正アクセス行為の禁止等に関する法律 | 平成十一年法律第百二十八号 | `1999-egov-fusei-access-ho` | https://laws.e-gov.go.jp/law/411AC0000000128 | 2025-06-01 | なし |
| A3 | 個人情報の保護に関する法律 | 平成十五年法律第五十七号 | `2003-egov-kojin-joho-ho` | https://laws.e-gov.go.jp/law/415AC0000000057 | 2026-11-02（令和八年法律第六十二号） | 5 件: 2027-01-17（令和八年法律第五十六号）、2027-04-01（令和六年法律第六十号）、2027-04-16（令和八年法律第五十九号）、2028-07-16（令和八年法律第五十六号）、2028-12-23（令和八年法律第四十六号）。改正後の本文は取っていない |
| A4 | 電気通信事業法（依頼では任意） | 昭和五十九年法律第八十六号 | `1984-egov-denki-tsushin-jigyo-ho` | https://laws.e-gov.go.jp/law/359AC0000000086 | 2026-05-27 | 2027-05-27（令和七年法律第四十六号）、2028-06-13（令和五年法律第五十三号） |
| A5 | 重要電子計算機に対する不正な行為による被害の防止に関する法律 | 令和七年法律第四十二号 | `2025-egov-juyo-denshi-keisanki-ho` | https://laws.e-gov.go.jp/law/507AC0000000042 | 2026-10-01（制定時の本文。改正なし） | 2027-11-22 に施行される部分（改正法ではなく、この法の段階的な施行） |
| A6 | 刑法 | 明治四十年法律第四十五号 | `1907-egov-keiho` | https://laws.e-gov.go.jp/law/140AC0000000045 | 2026-05-21 | なし |

依頼にあった三つ（A1〜A3）と任意の A4 に、A5（2025 年の新しい法）と A6（不正指令電磁的記録の罪がある）を足しました。施行令・施行規則は取っていません。

本文から Claude が見た所（条の見出しと字面だけ。解釈ではない）:

- A1 サイバーセキュリティ基本法: 第二条（「サイバーセキュリティ」の定義）、第三条（基本理念）、第六条・第七条（重要社会基盤事業者、サイバー関連事業者その他の事業者の責務）、第九条（国民の努力）「国民は、基本理念にのっとり、サイバーセキュリティの重要性に関する関心と理解を深め、サイバーセキュリティの確保に必要な注意を払うよう努めるものとする。」（確認日 2026-11-05）、第十五条（中小企業者その他の民間事業者の自発的な取組の促進）。
- A2 不正アクセス禁止法: 第二条（アクセス管理者、識別符号、アクセス制御機能、不正アクセス行為の定義）、第三条（不正アクセス行為の禁止）、第四条〜第六条（他人の識別符号の不正取得・助長・不正保管の禁止）、第七条（識別符号の入力を不正に要求する行為の禁止。アクセス管理者になりすます形）、第八条（アクセス管理者による防御措置。識別符号の適正な管理、アクセス制御機能の有効性の検証、必要なら高度化その他の措置を「講ずるよう努めるものとする」）、第十一条「三年以下の拘禁刑又は百万円以下の罰金」（第三条違反、確認日 2026-11-05）。
- A3 個人情報保護法: 第二条（個人情報、個人識別符号、要配慮個人情報の定義）、第十六条（個人情報データベース等、第 2 項「個人情報取扱事業者」とは「個人情報データベース等を事業の用に供している者をいう」）、第二十三条（安全管理措置）、第二十六条（漏えい等の報告等）、第二十七条（第三者提供の制限）。
- A5: 第二条の二（この法の適用は目的の達成に必要な最小限度、通信の秘密への配慮）。題名どおり重要電子計算機と特別社会基盤事業者が相手の法。
- A6 刑法: 第百六十八条の二（不正指令電磁的記録作成等。人の電子計算機で、その意図に沿う動作をさせず、または意図に反する動作をさせる不正な指令を与える電磁的記録を、正当な理由なく作成・提供・供用する罪）、第百六十八条の三（取得・保管）、第二百三十四条の二（電子計算機損壊等業務妨害）、第二百四十六条の二（電子計算機使用詐欺）、第百六十一条の二（電磁的記録不正作出及び供用）。

---

## (B) 日本の公的な手引き

#### B1. 情報セキュリティ10大脅威 2026 解説書［組織編］
- 発行・年: 独立行政法人情報処理推進機構（IPA）、2026 年（10 大脅威の決定 2026-01-29、解説書 2026-03-12、四版 2026-04-10）
- URL: https://www.ipa.go.jp/security/10threats/10threats2026.html
- 図書室の id: `2026-ipa-10threats-soshiki`
- 確認日: 2026-11-05
- 権利: admin（IPA「ウェブサイトのご利用について」: 著作権は IPA、引用・転載は出所を明示。10 大脅威のページに引用の決まり: 出典明記、原文のまま、イラストは単体で使わない）
- 種類: 手引き（脅威の一覧と解説）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次、序文、表、3 位の節）: 2025 年の事案から IPA が候補を選び、約 250 名の選考会が投票で決めた。組織の 1 位ランサム攻撃による被害、2 位サプライチェーンや委託先を狙った攻撃、3 位 AI の利用をめぐるサイバーリスク（初選出）、4 位システムの脆弱性を悪用した攻撃（ページの表）。3 位の節: シャドー AI、ハルシネーション、AI による攻撃の容易化、Microsoft 365 Copilot の「EchoLeak」（外部から注入された不正なプロンプトで社内の秘密データが流出しうる脆弱性）を挙げ、対策は「AI 事業者ガイドライン」の AI 利用者を想定、と書く（pp.16–18 の辺り）。
- 前提: 企業・組織向け。2025 年の日本の事案が中心。

#### B2. 情報セキュリティ10大脅威 2026 個人編 ハンドブック［一般利用者向け］
- 発行・年: IPA、2026 年（公開 2026-05-21）
- URL: https://www.ipa.go.jp/security/10threats/10threats2026.html
- 図書室の id: `2026-ipa-10threats-kojin`
- 確認日: 2026-11-05
- 権利: admin（B1 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 初めの数頁）: 個人向けは順位なしの五十音順の 10 件（不正ログイン、フィッシング、サポート詐欺、個人情報の窃取など）。脅威ごとに「どんな手口・被害？」「被害に遭うとどうなるの？」「対策」を並べる。例: 個人情報の窃取の対策に、使わないアカウントの削除、必須でない情報を登録しない、多要素認証。
- 前提: 一般の利用者（スマホとネットのサービス）向け。家のサーバーや LAN の運用は、開いた範囲には無い。

#### B3. 中小企業の情報セキュリティ対策ガイドライン 第4.0版
- 発行・年: IPA セキュリティセンター、2026 年 3 月 27 日（第 4.0 版。ページの最終更新 2026-09-30）
- URL: https://www.ipa.go.jp/security/guide/sme/about.html
- 図書室の id: `2026-ipa-sme-security-guideline`
- 確認日: 2026-11-05
- 権利: admin（B1 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: ページ、目次、「本ガイドラインの対象」、情報セキュリティ６か条、バックアップのコラム）: 対象は中小企業及び小規模事業者（法人、個人事業主、各種団体を含む）、想定読者は経営者と情報管理を統括する人（p.5）。6 か条は、OS やソフトウェアを最新に、ウイルス対策ソフト、パスワードの強化（長く・複雑に・使い回さない）、共有設定の見直し、バックアップを取ろう（4.0 版で追加）、脅威や攻撃の手口を知ろう（p.20）。コラム「適切なバックアップ運用を行う」は、復旧計画を立てる、正しく復旧できることを確認する、と書く。ページは、自社診断に「外部から内部ネットワークへの不要な通信を遮断する」「ウェブサイトを安全に運用する」を追加した、と書く。
- 前提: 個人事業主を含むが、規程・体制・委託先など組織の話が多い。

#### B4. 中小企業のためのセキュリティインシデント対応の手引き
- 発行・年: IPA セキュリティセンター、2026 年 6 月（B3 の付録）
- URL: https://www.ipa.go.jp/security/guide/sme/about.html
- 図書室の id: `2026-ipa-sme-incident-tebiki`
- 確認日: 2026-11-05
- 権利: admin（B1 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 初めの数頁）: 対応を「検知・初動対応」「報告・公表」「復旧・再発防止」の 3 段階に分ける（p.2）。インシデントは情報の漏えい・改ざん・破壊・消失、システムの機能停止、またはそれにつながる事象（p.3）。復旧の段に証拠保全がある。
- 前提: 組織向け（報告・公表は取引先や監督官庁への報告を想定）。

#### B5. 安全なウェブサイトの作り方 改訂第7版
- 発行・年: IPA セキュリティセンター、2021 年 3 月
- URL: https://www.ipa.go.jp/security/vuln/websecurity/about.html
- 図書室の id: `2021-ipa-safe-website`
- 確認日: 2026-11-05
- 権利: admin（B1 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次、第 2 章の見出し）: 第 1 章はウェブアプリの脆弱性 11 種（SQL インジェクション、OS コマンド・インジェクション、XSS、CSRF など）の根本的な解決と影響の低減。第 2 章は運用面（ウェブサーバ、DNS、ネットワーク盗聴、フィッシングを助長しない、パスワード、WAF）。第 3 章は失敗例。巻末にチェックリスト。
- 前提: ウェブサイトの開発者・運営者向け。5 年前の版で、LLM を組み込んだアプリは扱っていない。

#### B6. 国民のためのサイバーセキュリティサイト 一般利用者向けの対策（PDF 版）
- 発行・年: 総務省、2024 年（サイトのリニューアル 2024-05-24、PDF の表記 ©2024）
- URL: https://www.soumu.go.jp/main_sosiki/cybersecurity/kokumin/index.html
- 図書室の id: `2024-soumu-kokumin-enduser`
- 確認日: 2026-11-05
- 権利: admin（総務省のサイトの著作権の定め: 公共データ利用規約（第 1.0 版）に準拠、出典を記載）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: サイトのトップと PDF の初め）: 初心者のための三原則「ソフトウェアを最新に保とう」「強固なパスワードの設定と多要素認証を活用しよう」「不用意に開かない・インストールしないようにしよう」（トップページ）。サイトには家庭・職場の対策、IoT 機器（ルータやネットワークカメラ）への対策、Wi-Fi の項がある。
- 前提: 一般の利用者向け。

#### B7. 国民のためのサイバーセキュリティサイト システムを“管理”する人向けの対策（PDF 版）
- 発行・年: 総務省、2024 年
- URL: https://www.soumu.go.jp/main_sosiki/cybersecurity/kokumin/security/business/admin/
- 図書室の id: `2024-soumu-kokumin-admin`
- 確認日: 2026-11-05
- 権利: admin（B6 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: HTML 版の目次だけ）: 項目は、関連文書の整備、データ・端末の廃棄、ソフトウェアの最新化・脆弱性管理、マルウェア対策管理、メールと Web サイト、脆弱性診断、教育、テレワーク端末、アカウント管理、アクセス制御・管理、監査ログの管理、データ復旧・バックアップの管理、インシデントレスポンス体制整備。各項の中身は読んでいない。
- 前提: 企業・組織の情報管理担当者向け。

#### B8. インターネットの安全・安心ハンドブック Ver5.10
- 発行・年: 内閣官房 国家サイバー統括室（NCO。旧 内閣サイバーセキュリティセンター NISC）、2025 年 3 月 11 日
- URL: https://security-portal.cyber.go.jp/guidance/handbook.html （旧 security-portal.nisc.go.jp から転送）
- 図書室の id: `2025-nco-anshin-handbook`（全体版 PDF、105 MB）
- 確認日: 2026-11-05
- 権利: admin（著作権は NCO。普及啓発の範囲で、内容を改変しないことを条件に活用できる、とページにある）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 章立てと、マルウェアの説明の頁）: 章は、基礎、よくある攻撃の手口、SNS と情報モラル、スマホ・パソコン・IoT 機器の設定、パスワードと暗号化、中小企業等向け、付録（手引き・ガイダンスの一覧）、用語集。マルウェアの説明で生物の比喩を使う（下の「作者の類比との関係」）。
- 前提: 一般の利用者と中小企業向け。

#### B9. インシデントハンドリングマニュアル
- 発行・年: 一般社団法人 JPCERT コーディネーションセンター、2021 年 11 月 30 日
- URL: https://www.jpcert.or.jp/csirt_material/operation_phase.html
- 図書室の id: `2021-jpcert-incident-handling-manual`
- 確認日: 2026-11-05
- 権利: admin（JPCERT/CC「ご利用にあたって」: 引用は自由、転載・再配布は広報に連絡。行政機関ではないが公的な調整機関として admin に入れた）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次）: 基本的ハンドリングフローは、検知／連絡受付、トリアージ、インシデントレスポンス（分析、対応計画、対応）、報告／情報公開。CSIRT マテリアルのページは、すべての組織内 CSIRT がそれらを達成しなければならないわけではない、と書く。
- 前提: 組織内 CSIRT（インシデント対応チーム）向け。

#### B10. 高度サイバー攻撃への対処におけるログの活用と分析方法 1.2版
- 発行・年: JPCERT/CC、2022 年 5 月 10 日
- URL: https://www.jpcert.or.jp/research/apt-loganalysis.html
- 図書室の id: `2022-jpcert-log-analysis`
- 確認日: 2026-11-05
- 権利: admin（B9 と同じ）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次、3.1.1「ログの保存」、コラム「ログ保存期間に関する考え方」）: メールサーバ・Firewall・Web プロキシ・DNS・認証サーバのログで攻撃の痕跡を探す例。保存期間はログの量の見積もりと、遡って調べる必要とコストの取引で決め、JPCERT/CC は参考値として 1 年分の保存を推奨、と書く（pp.12–13）。長期保存の問題（媒体、費用）も挙げる。
- 前提: 組織内のサーバとネットワーク機器のシステム管理者向け。標的型攻撃を想定。

#### B11. 直近で相次いでいる国内組織における不正アクセスに関する注意喚起（JPCERT-AT-2026-0030）
- 発行・年: JPCERT/CC、2026-10-08 公開、2026-10-23 更新
- URL: https://www.jpcert.or.jp/at/2026/at260030.html （注意喚起の一覧 https://www.jpcert.or.jp/at/2026.html）
- 図書室の id: `2026-jpcert-at-unauthorized-access`
- 確認日: 2026-11-05
- 権利: admin（B9 と同じ）
- 種類: 注意喚起
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: I と II のケース A・B）: 国内組織で不正アクセスによる個人情報等の漏えいが相次いでいる。ケース A は標的ごとに既知の脆弱性を探して悪用を試みるもので、脆弱性ではない管理不備の悪用（環境設定ファイルやバックアップファイルの窃取など）も試みている可能性。ケース B は管理用 API への不正なリクエスト（公開アプリの解析で API のエンドポイントやキーを特定、他のシステムで窃取した API キーを使う）。10-23 の更新で「ケース E: AI を用いたペネトレーションテスト基盤を悪用した攻撃試行」を追加（中身は開いていない）。
- 前提: 組織のシステムが相手。注意喚起は日付の物で、後で更新される。

#### B12. サイバーセキュリティ経営ガイドライン Ver 3.0
- 発行・年: 経済産業省・IPA、2023 年 3 月 24 日
- URL: https://www.meti.go.jp/policy/netsecurity/mng_guide.html
- 図書室の id: `2023-meti-cybersecurity-keiei-guideline`
- 確認日: 2026-11-05
- 権利: admin（経済産業省の利用規約: 公共データ利用規約（第 1.0 版））
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: ページと目次）: 経営者が認識すべき「3 原則」と、CISO 等に指示すべき「重要 10 項目」。
- 前提: **企業の経営者向け**。対象は大企業及び中小企業（小規模事業者を除く）のうち、IT のシステム・サービスを供給する企業と、経営戦略上 IT の利活用が不可欠な企業（ページの「概要」）。規模の比較のために入れた。

---

## (C) 国際の枠組み

#### C1. The NIST Cybersecurity Framework (CSF) 2.0
- 発行・年: 米国 NIST、2024-02-26（CSWP 29）
- URL: https://doi.org/10.6028/NIST.CSWP.29
- 図書室の id: `2024-nist-csf-2`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格（枠組み）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 序と Functions の節）: GOVERN、IDENTIFY、PROTECT、DETECT、RESPOND、RECOVER の 6 つ。あらゆる規模と分野の組織が使える、と書く（p.1）。結果（outcomes）を並べる枠組みで、手順は書かない。
- 前提: 組織向け。

#### C2. Incident Response Recommendations and Considerations for Cybersecurity Risk Management (SP 800-61 Rev. 3)
- 発行・著者・年: NIST、Nelson A.、Rekhi S.、Souppaya M.、Scarfone K.、2025 年 4 月
- URL: https://doi.org/10.6028/NIST.SP.800-61r3
- 図書室の id: `2025-nist-sp800-61r3`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格（手引き）
- 読了: Claude abstract、本人 none
- 書いてあること（読んだ所: 要旨と表紙）: インシデント対応の推奨と考慮事項を、CSF 2.0 のリスク管理の中に組み込む助け。副題は「A CSF 2.0 Community Profile」。
- 前提: 組織向け。

#### C3. Digital Identity Guidelines: Authentication and Authenticator Management (SP 800-63B-4)
- 発行・著者・年: NIST、Temoshok D.、Fenton J.L.、Choong Y.-Y.、Lefkovitz N.、Regenscheid A.、Galluzzo R.、Richer J.P.、2025 年 7 月
- URL: https://doi.org/10.6028/NIST.SP.800-63B-4
- 図書室の id: `2025-nist-sp800-63b-4`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 3.1.1.2 Password Verifiers）: 単一要素で使うパスワードは最低 15 文字（SHALL）、多要素の一部なら最低 8 文字、最大長は少なくとも 64 文字を許す（SHOULD）、文字種の混在などの構成規則を課さない（SHALL NOT）、定期的な変更を要求しない（SHALL NOT）、ただし侵害の証拠があれば変更させる、よく使われるパスワードの blocklist と照合する。
- 前提: 認証を提供する側（verifier、CSP）への要件。

#### C4. Contingency Planning Guide for Federal Information Systems (SP 800-34 Rev. 1)
- 発行・著者・年: NIST、Swanson M.、Bowen P.、Phillips A.W.、Gallup D.、Lynes D.、2010 年 5 月
- URL: https://doi.org/10.6028/NIST.SP.800-34r1
- 図書室の id: `2010-nist-sp800-34r1`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格（手引き）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次と 3.4.1 の初め）: 3.4.1 Backup and Recovery、3.4.2 Backup Methods and Offsite Storage。頻度と保管場所（onsite／offsite）を計画に書く、と並べる。
- 前提: **米連邦政府の機関向けで、16 年前の版**。ランサムウェアの語は本文に無い（`rg` で 0 件）。

#### C5. Shields Up
- 発行・年: 米国 CISA、ページ（Internet Archive の 2026-09-14 の写し）
- URL: https://www.cisa.gov/shields-up
- 図書室の id: `2026-cisa-shields-up`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物。cisa.gov は 403 で、Internet Archive の写しを取った）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: ページ全体）: 家族・組織・経営者向けの案内の入口。Quick Tips（ウイルス対策、多要素認証、強いパスワード、フィッシングを避ける）。身代金を払っても復号や再侵害が無いことは保証されず、CISA などは支払いを勧めない、と書く。
- 前提: 米国の組織（州・地方政府、重要インフラ）が主。

#### C6. Data Backup Options
- 著者・年: Ruggiero P.、Heckathorn M.A.、2012 年（Carnegie Mellon University が US-CERT のために作成）
- URL: https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf
- 図書室の id: `2012-ruggiero-data-backup-options`（書誌だけ）
- 確認日: 2026-11-05
- 権利: quote（頁に「© 2012 Carnegie Mellon University」。連邦政府の著作物ではなく、許諾の記載は見当たらない。Internet Archive の写しで読んだ）
- 種類: 手引き
- 読了: Claude full（5 頁）、本人 none
- 書いてあること（読んだ所: 全部）: 3-2-1 の規則: 大事なファイルは 3 つ（元 1 つと控え 2 つ）、2 種類の媒体、1 つは家や事業所の外に（p.1、p.5）。出典として Krogh の本（C7）を脚注に挙げる。クラウド、取り外せる媒体、外付けの HDD、光学媒体の長所・短所。
- 前提: 家庭の利用者から専門家まで、と書き出す。**2012 年の物で、ランサムウェアの語も、切り離した（オフラインの）控えの語も無い**（`rg` で 0 件）。

#### C7. The DAM Book: Digital Asset Management for Photographers, 2nd Edition
- 著者・年: Krogh P.、O'Reilly Media、2009
- 図書室の id: `2009-krogh-dam-book`（書誌だけ）
- 権利: quote（本）
- 種類: 本
- 読了: Claude none、本人 none
- 書いてあること: 開いていない。C6 が 3-2-1 の規則の出典として p.207 を挙げる本。
- 前提: 写真家のデジタル資産の管理の本。

#### C8. Best Practices for Securing Your Home Network
- 発行・年: 米国 NSA（Cybersecurity Information Sheet）、2023 年 2 月
- URL: https://media.defense.gov/2023/Feb/22/2003165170/-1/-1/0/CSI_BEST_PRACTICES_FOR_SECURING_YOUR_HOME_NETWORK.PDF
- 図書室の id: `2023-nsa-home-network`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物。TLP:CLEAR。media.defense.gov は 403 で、Internet Archive の写しを取った）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 見出しの一覧といくつかの項）: OS とルータを新しく保つ。無線を分ける（少なくとも主の Wi-Fi、ゲスト Wi-Fi、IoT のネットワーク）。ファイアウォール（NAT、IPv6 のファイアウォール）。管理者アカウントの使用を限る。ルータの遠隔管理を切り、内部からだけ設定する。UPnP を切る。少なくとも週に一度ルータ・スマホ・PC を再起動する（持続しない埋め込みを消すため）。
- 前提: **この一覧で、家のネットワークを直接の相手にした唯一の公的な手引き**。米国の在宅勤務者も想定。

#### C9. CIS Critical Security Controls Implementation Group 1
- 発行・年: Center for Internet Security（ページ。Controls v8.1）
- URL: https://www.cisecurity.org/controls/implementation-groups/ig1
- 図書室の id: `2026-cis-controls-ig1`（書誌だけ）
- 確認日: 2026-11-05
- 権利: quote（本文はダウンロードに登録が要り取っていない。ライセンスは確かめていない）
- 種類: 規格
- 読了: Claude snippet（ページだけ）、本人 none
- 書いてあること（読んだ所: IG1 と v8.1 のページ）: IG1 は「essential cyber hygiene」で 56 の Safeguard。IG1 の組織は中小で IT の専門性が限られ、Safeguard は小さな事業所・家庭の事務所（small or home office）の市販の機器とソフトで働くように作られている、と書く。v8.1 は NIST CSF 2.0 の Govern に合わせた。
- 前提: 企業（enterprise）向けの枠組みの、いちばん小さい段。

#### C10. MITRE ATT&CK: Design and Philosophy（と技術 T1490）
- 著者・年: Strom B.E.、Applebaum A.、Miller D.P.、Nickels K.C.、Pennington A.G.、Thomas C.B.、The MITRE Corporation、2020 年 3 月
- URL: https://attack.mitre.org/docs/ATTACK_Design_and_Philosophy_March_2020.pdf （T1490: https://attack.mitre.org/techniques/T1490/）
- 図書室の id: `2020-strom-mitre-attack-design`（同じ項目に `T1490.html` と `terms-of-use.html`）
- 確認日: 2026-11-05
- 権利: open（ATT&CK の Terms of Use: 研究・開発・商用の目的の非独占・無償の許諾、写しに著作権表示と許諾文を付ける。論文は「Approved for Public Release. Distribution unlimited」）
- 種類: 枠組み（知識ベース）
- 読了: Claude abstract、本人 none
- 書いてあること（読んだ所: 要旨、T1490 のページの説明）: ATT&CK は実際の観測に基づく攻撃者の戦術と技術の知識ベースで、攻撃と防御の共通の分類（要旨）。T1490「Inhibit System Recovery」: 攻撃者が復旧を助けるデータとサービスを消し、使えるバックアップと復旧の手段を奪う、と書き、ランサムウェアの例が並ぶ。
- 前提: 企業のネットワーク（Enterprise）が主。2026-11 時点で ATT&CK は v20（サイトの告知）。

#### C11. ENISA Threat Landscape 2026
- 発行・年: 欧州連合サイバーセキュリティ機関（ENISA）、2026 年 9 月
- URL: https://www.enisa.europa.eu/publications/enisa-threat-landscape-2026
- 図書室の id: `2026-enisa-threat-landscape`
- 確認日: 2026-11-05
- 権利: open（CC BY 4.0。表紙の画像は対象外）
- 種類: 報告（脅威の動向）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: Executive Summary）: 2025 年 1〜12 月の EU の事案。DDoS（51.3%）と不正アクセス（39.5%）が記録の多くを占める。フィッシング（77.8%）が社会工学の主、脆弱性の悪用が不正アクセスの侵入経路の 60.4%。金銭目的（29.3%）、とくにランサムウェアが短期で最も影響が大きい。AI の悪用が進んだ。数字の母数（何に対する割合か）は本文で確かめる所。
- 前提: EU の当局と民間向け。

#### C12. Small organisations guide to cyber security
- 発行・年: 英国 NCSC、公開 2026-04-09、見直し 2026-07-21（旧 Small Business Guide）
- URL: https://www.ncsc.gov.uk/collection/small-organisations-guide-to-cyber-security
- 図書室の id: `2026-ncsc-small-organisations-guide`（6 頁を `text.txt` に繋いだ）
- 確認日: 2026-11-05
- 権利: open（Open Government Licence v3.0。写真・第三者の物は対象外）
- 種類: 手引き
- 読了: Claude full、本人 none
- 書いてあること（読んだ所: 6 頁全部）: バックアップの頁: 事業に要るデータの写しを作る、オンライン（クラウド）か外付けの機器に、外付けは安全な所に置き、使わない時は繋いだままにしない（繋がった機器に及ぶウイルスがあるため）、オンラインと機器の二つの控え、オンラインの控えは 2 段階認証で守る、控えから戻せるか確かめる。他の頁はメール、大事なアカウント、機器の保護、攻撃の見分け。
- 前提: 0〜49 人の組織向け（Written for: Small & medium sized organisations）。

---

## (D) AI 固有

#### D1. OWASP Top 10 for LLM Applications 2025
- 発行・年: OWASP Top 10 for LLM Applications & Generative AI Project、2024-11-18（版 2025）
- URL: https://genai.owasp.org/llm-top-10/
- 図書室の id: `2024-owasp-llm-top10`
- 確認日: 2026-11-05
- 権利: open（CC BY-SA 4.0）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次と LLM01 の対策の節）: 10 項目は LLM01 Prompt Injection、LLM02 Sensitive Information Disclosure、LLM03 Supply Chain、LLM04 Data and Model Poisoning、LLM05 Improper Output Handling、LLM06 Excessive Agency、LLM07 System Prompt Leakage、LLM08 Vector and Embedding Weaknesses、LLM09 Misinformation、LLM10 Unbounded Consumption。LLM01 の対策の節は、確実な防ぎ方があるかは分からないとした上で、振る舞いの制限、出力の形を決めて決定的なコードで確かめる、入出力のフィルタ、最小の権限（API token はモデルに渡さずコードで扱う）、危険な操作に人の承認、外部の内容を分けて印を付ける、攻撃の試験、を並べる（p.4）。
- 前提: LLM を組み込むアプリの開発者向け。

#### D2. Artificial Intelligence Risk Management Framework (AI RMF 1.0)
- 発行・年: NIST（AI 100-1）、2023 年 1 月
- URL: https://doi.org/10.6028/NIST.AI.100-1
- 図書室の id: `2023-nist-ai-rmf`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格（枠組み）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 序と概要）: 任意（voluntary）で、分野と用途を問わない。Core は GOVERN、MAP、MEASURE、MANAGE。
- 前提: AI を設計・開発・配備・利用する組織向け。サイバー攻撃への個別の手立ては、開いた範囲には無い。

#### D3. Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations (NIST AI 100-2e2025)
- 発行・著者・年: NIST、Vassilev A.、Oprea A.、Fordyce A.、Anderson H.、Davies X.、Hamin M. ほか、2025 年 3 月
- URL: https://doi.org/10.6028/NIST.AI.100-2e2025
- 図書室の id: `2025-nist-ai-100-2`
- 確認日: 2026-11-05
- 権利: open（米国連邦政府の著作物）
- 種類: 規格（用語と分類）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次と攻撃の一覧）: 生成 AI の部に 3.4「Indirect Prompt Injection Attacks and Mitigations」（p.50）。間接プロンプト・インジェクションに ID NISTAML.015 を付ける。
- 前提: 用語の整理で、手順書ではない。

#### D4. Guidelines for secure AI system development
- 発行・年: 英国 NCSC、米国 CISA ほか各国の機関の共同、2023 年 11 月
- URL: https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development
- 図書室の id: `2023-ncsc-secure-ai-guidelines`
- 確認日: 2026-11-05
- 権利: open（本文は Open Government Licence v3.0。写真と図は対象外。TLP:CLEAR）
- 種類: 手引き
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: About、Who should read、目次）: 4 つの段（secure design、secure development、secure deployment、secure operation and maintenance）。プロンプト・インジェクションは脅威の例として出る。
- 前提: AI システムの提供者（自分でホストするモデルでも外部 API を使う物でも）が主な読者。

#### D5. Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection
- 著者・年: Greshake K.、Abdelnabi S.、Mishra S.、Endres C.、Holz T.、Fritz M.、2023（arXiv:2302.12173、v2 2023-05-05）
- URL: https://arxiv.org/abs/2302.12173
- 図書室の id: `2023-greshake-indirect-prompt-injection`
- 確認日: 2026-11-05
- 権利: quote（arXiv の非独占配布ライセンス。図書室の私的な写し）
- 種類: 論文
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: LLM を組み込んだアプリはデータと指示の境を曖昧にする。取り込まれそうなデータに指示を仕込んで、直接の窓口なしに遠隔でアプリを悪用する「間接プロンプト・インジェクション」を示す。
- 前提: 2023 年初めの LLM アプリ（検索と組み合わせたチャットなど）。

#### D6. Mitigating the risk of prompt injections in browser use
- 発行・年: Anthropic、2025-11-24
- URL: https://www.anthropic.com/research/prompt-injection-defenses
- 図書室の id: `2025-anthropic-prompt-injection-browser`（書誌だけ）
- 確認日: 2026-11-05
- 権利: quote
- 種類: 会社の記事
- 読了: Claude full、本人 none
- 書いてあること（読んだ所: 全部）: ブラウザーを使うエージェントでは訪れるページのすべてが攻撃の経路になりうる。攻撃の成功率 1% でも意味のあるリスクで、プロンプト・インジェクションを免れたブラウザー・エージェントは無い、解決したとは言わない、と書く。手立ては学習（強化学習）、文脈に入る信頼できない内容の分類器、人のレッドチーム。
- 前提: **このリストを作った Claude を作った会社が、自社のモデルについて書いた記事**。

#### D7. Mitigating prompt injection attacks with a layered defense strategy
- 発行・年: Google GenAI Security Team、2025-06-13
- URL: https://security.googleblog.com/2025/06/mitigating-prompt-injection-attacks.html （blog.google に転送）
- 図書室の id: `2025-google-prompt-injection-layered`（書誌だけ）
- 確認日: 2026-11-05
- 権利: quote
- 種類: 会社の記事
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 初めと見出し）: 間接プロンプト・インジェクションを、メール・文書・カレンダーの招待などに隠した指示、と説明する。層: 注入を見つける分類器、セキュリティの考えの強化、Markdown の無害化と疑わしい URL の伏せ字、利用者の確認の枠組み、利用者への通知。
- 前提: Google が自社の Gemini について書いた記事。

#### D8. How Microsoft defends against indirect prompt injection attacks
- 著者・年: Paverd A.（Microsoft Security Response Center）、2025-07-29
- URL: https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks
- 図書室の id: `2025-paverd-msrc-indirect-prompt-injection`（書誌だけ）
- 確認日: 2026-11-05
- 権利: quote
- 種類: 会社の記事
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 要約と初めの節）: 予防（強化したシステムプロンプト、信頼できない入力を区別する Spotlighting）、検知（Prompt Shields）、影響の緩和（データの統制、利用者の同意の流れ、既知の流出の方法の決定的な遮断）。決定的な防御は確かな保証を与えるので望ましいが、確率的な系では常には使えない、と書く。
- 前提: Microsoft が自社の製品について書いた記事。企業向けの製品の話が多い。著者は F10 の共著者の一人。

#### D9. Model Context Protocol: Security Best Practices
- 発行・年: Model Context Protocol project、版 2025-11-25
- URL: https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices
- 図書室の id: `2025-mcp-security-best-practices`
- 確認日: 2026-11-05
- 権利: open（リポジトリの LICENSE: 仕様を除く文書は CC-BY-4.0）
- 種類: 手引き（プロトコルの文書）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 目次と Introduction）: MCP の認可の仕様を補う。節は Confused Deputy、Token Passthrough、SSRF、Session Hijacking、Local MCP Server Compromise、OAuth の認可 URL の検証、stdio の代理、Scope Minimization。各節の中身は読んでいない。
- 前提: MCP の認可を実装する開発者、MCP サーバーの運用者向け。公的機関の物ではない。

---

## (E) 家の小さなシステムの実務

#### E1. sshd_config(5)
- 発行・年: OpenBSD / OpenSSH、man.openbsd.org（2026-11-05 に取得）
- URL: https://man.openbsd.org/sshd_config.5
- 図書室の id: `2026-openbsd-sshd-config`
- 確認日: 2026-11-05
- 権利: open（OpenSSH の LICENCE: すべての部品が BSD かそれより自由）
- 種類: 文書（設定の定義）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: PermitRootLogin ほか）: PermitRootLogin の値は yes、prohibit-password、forced-commands-only、no で、既定は prohibit-password。PasswordAuthentication、AuthenticationMethods、ListenAddress、AllowUsers の項がある（中身は読んでいない）。
- 前提: OpenBSD 版。Debian の版の既定値と同じかは確かめていない。手順書ではなく項目の定義。

#### E2. The Transport Layer Security (TLS) Protocol Version 1.3 (RFC 9846)
- 著者・年: Rescorla E.、IETF、2026 年 7 月（Proposed Standard）
- URL: https://www.rfc-editor.org/rfc/rfc9846
- 図書室の id: `2026-rfc9846-tls13`
- 確認日: 2026-11-05
- 権利: open（IETF Trust Legal Provisions、BCP 78）
- 種類: 規格
- 読了: Claude abstract、本人 none
- 書いてあること（読んだ所: 要旨と頭書）: TLS 1.3 の仕様。RFC 8446 を廃した（Obsoletes: 5077, 5246, 6961, 7627, 8422, 8446）。
- 前提: 実装者向けの仕様。自己署名の証明書と指紋の照合は主題ではない。

#### E3. Public Key Pinning Extension for HTTP (RFC 7469)
- 著者・年: Evans C.、Palmer C.、Sleevi R.、IETF、2015 年 4 月（Proposed Standard）
- URL: https://www.rfc-editor.org/rfc/rfc7469
- 図書室の id: `2015-evans-rfc7469-hpkp`
- 確認日: 2026-11-05
- 権利: open（IETF Trust Legal Provisions）
- 種類: 規格
- 読了: Claude abstract、本人 none
- 書いてあること（読んだ所: 要旨と頭書）: HTTP のヘッダーで、ウェブの主が公開鍵の指紋（pin）をブラウザーに覚えさせる仕組み。
- 前提: ブラウザーとウェブサイトの間の仕組み。主要なブラウザーが対応をやめた、と Claude は記憶しているが確かめていない。アプリが自分で指紋を照合する形とは別。

#### E4. systemd.exec(5)
- 発行・年: systemd project（systemd 262）、freedesktop.org
- URL: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- 図書室の id: `2026-systemd-exec`
- 確認日: 2026-11-05
- 権利: open（LGPL-2.1-or-later。systemd の LICENSES/README.md）
- 種類: 文書（設定の定義）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 見出しと項の名前）: ProtectSystem=、ProtectHome=、PrivateTmp=、NoNewPrivileges=、PrivateNetwork= などのサンドボックスの項がある。各項の文は読んでいない。
- 前提: 項目の定義で、どれを使うかの推奨はこのページの目的ではない。

#### E5. Simple ruleset for a server
- 発行・年: nftables wiki
- URL: https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_server
- 図書室の id: `2026-nftables-server-ruleset`
- 確認日: 2026-11-05
- 権利: open（GFDL 1.3 or later）
- 種類: 文書（例）
- 読了: Claude full、本人 none
- 書いてあること（読んだ所: 全部）: ウェブサーバーの基本的な例。入ってくる通信の既定を落とし（policy drop）、確立済みの接続、ループバック、TCP の 22・80・443 だけ通す。ICMP の echo-request は、許すと存在が分かる、と注に書く。forward は落とす（ルータでない前提）。
- 前提: 一台のウェブサーバーの例。家の LAN の構成は扱っていない。

#### E6. Certificates for localhost
- 発行・年: Let's Encrypt、最終更新 2025-07-31
- URL: https://letsencrypt.org/docs/certificates-for-localhost/
- 図書室の id: `2025-letsencrypt-localhost-certs`
- 確認日: 2026-11-05
- 権利: open（letsencrypt/website リポジトリの LICENSE.txt が MPL-2.0。ページ上の記載は見つからなかった）
- 種類: 文書
- 読了: Claude full、本人 none
- 書いてあること（読んだ所: 全部）: Let's Encrypt は「localhost」の証明書を出せない。手元の開発には、自己署名か手元のルートで署名した証明書を作って OS の信頼の置き場に入れるのが最良、と書く。ネイティブアプリが localhost に口を開ける場合の注意。
- 前提: 手元の開発とネイティブアプリ。家の LAN の別の機械への HTTPS は扱っていない。

#### E7. Debian security FAQ
- 発行・年: Debian Security Team、debian.org
- URL: https://www.debian.org/security/faq
- 図書室の id: `2026-debian-security-faq`
- 確認日: 2026-11-05
- 権利: open（Debian WWW Pages License: MIT または GPL-2.0-or-later）
- 種類: 文書（問答）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 問いの一覧と初めの数問）: DSA（Debian Security Advisory）を受けたときの更新の仕方、署名の検証、安定版の古い版に修正を後から入れる理由、unstable・testing の扱い。
- 前提: Debian を使う人向け。

#### E8. restic documentation（Preparing a new repository、Working with repositories）
- 発行・年: restic authors、restic 0.19.1
- URL: https://restic.readthedocs.io/en/stable/
- 図書室の id: `2026-restic-docs-repo`（二つの頁）
- 確認日: 2026-11-05
- 権利: open（BSD-2-Clause）
- 種類: 文書（手順）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 見出しと初め）: リポジトリの置き場（ローカル、SFTP、REST Server、S3 など）。パスワードを失うとデータは取り戻せない、と書く。check による整合性の確認。
- 前提: 手順の文書。控えの方針（いつ、どこへ、切り離すか）は書かない。

#### E9. Borg Quick Start
- 発行・年: The Borg Collective、Borg 1.4.5
- URL: https://borgbackup.readthedocs.io/en/stable/quickstart.html
- 図書室の id: `2026-borg-quickstart`
- 確認日: 2026-11-05
- 権利: open（BSD-3-Clause）
- 種類: 文書（手順）
- 読了: Claude snippet、本人 none
- 書いてあること（読んだ所: 見出しと初め）: 段階の例、空き容量と権限の注意、Automating backups、Repository encryption（`borg init --encryption=repokey`）。
- 前提: 手順の文書。

#### E10. Concise Guide for Developing More Secure Software
- 発行・年: OpenSSF Best Practices Working Group、2023-06-14
- URL: https://best.openssf.org/Concise-Guide-for-Developing-More-Secure-Software
- 図書室の id: `2023-openssf-concise-guide`
- 確認日: 2026-11-05
- 権利: open（CC-BY-4.0。リポジトリの README）
- 種類: 手引き
- 読了: Claude full、本人 none
- 書いてあること（読んだ所: 全部）: 特権のある開発者は多要素認証、依存関係を選ぶ前に評価する、更新は少し待ってから（cooldown）取り込む、秘密情報をリポジトリに入れない、変更は確かめてから受け入れる、重要なリリースに署名する、SBOM、などを並べる。
- 前提: ソフトを作って配る人向け。家のサーバーの運用の話ではない。

---

## (F) 研究論文（すべて要旨だけ読んだ）

| 番号 | 題名 | 著者・年 | 図書室の id | 権利 | 要旨に書いてあること | 前提 |
|---|---|---|---|---|---|---|
| F1 | A Survey on Ransomware: Evolution, Taxonomy, and Defense Solutions | Oz H. ほか、ACM Computing Surveys 2022（arXiv 2021） doi:10.1145/3514229 | `2021-oz-ransomware-survey` | open（CC BY-NC-ND 4.0） | PC、モバイル、IoT/CPS のランサムウェアと防御の研究を一つの絵にまとめる総説 | 研究の総説 |
| F2 | Lifecycle-Based Design and Evaluation of Real-Time Backup Triggers for Ransomware Damage Mitigation | Higuchi K.、Kobayashi R.、arXiv 2026-10 | `2026-higuchi-backup-triggers` | open（CC BY-NC-ND 4.0） | 攻撃の始まりから検知までの間のファイルを実時間の控えで守る。open・read・write・rename のどこで控えを取るかで、戻せる割合と控えの数が変わる | 査読前。一台の機械のファイルシステムの話 |
| F3 | From Backup Restoration to Minimum Viable Factory Recovery | Chiu C.Y.、arXiv 2026-05 | `2026-chiu-manufacturing-ransomware-recovery` | quote（arXiv 非独占） | 製造業の復旧は控えを戻すだけの問題ではない（認証、端末の信頼、OT、取引先）。PRISMA に沿った文献の総説 | **工場の規模**。査読前 |
| F4 | Backstabber's Knife Collection: A Review of Open Source Software Supply Chain Attacks | Ohm M. ほか、arXiv 2020 | `2020-ohm-backstabbers-knife` | quote（arXiv 非独占） | npm・PyPI・RubyGems で実際に使われた悪意のパッケージ 174 件（2015-11〜2019-11）の分析 | 依存関係を自動で取り込む開発 |
| F5 | Taxonomy of Attacks on Open-Source Software Supply Chains | Ladisa P. ほか、IEEE S&P 2023 doi:10.1109/SP46215.2023.00010 | `2022-ladisa-supply-chain-taxonomy` | open（CC BY-SA 4.0） | 攻撃木の形の分類: 107 の経路、94 の事案、33 の緩和策 | 開発と配布の側 |
| F6 | Smart Home Survey on Security and Privacy | Panwar N. ほか、arXiv 2019 | `2019-panwar-smart-home-survey` | quote（arXiv 非独占） | スマートホームのセキュリティ要件と脅威、プライバシーを守るモデル、既存の暗号の手法の当て方 | 7 年前。自分で建てるサーバーは主題ではない |
| F7 | A Survey of User Perspectives on Security and Privacy in a Home Networking Environment | Pattnaik N.、Li S.、Nurse J.R.C.、ACM Computing Surveys 2022 doi:10.1145/3558095 | `2022-pattnaik-home-user-perspectives` | open（CC BY 4.0） | 126 本の系統的レビュー。足りない所に、多様な家の機器、家の利用者の間のやり取り、複雑なデータの流れ | 家の利用者の視点 |
| F8 | Formalizing and Benchmarking Prompt Injection Attacks and Defenses | Liu Y. ほか、arXiv 2023（v5 2025-11） | `2023-liu-prompt-injection-benchmark` | open（CC BY 4.0） | プロンプト・インジェクションを形式化し、5 つの攻撃と 10 の防御を 10 の LLM と 7 つの課題で評価 | LLM を組み込むアプリ |
| F9 | Defeating Prompt Injections by Design（CaMeL） | Debenedetti E. ほか、arXiv 2025 | `2025-debenedetti-camel` | open（CC BY 4.0） | 信頼できる問いから制御とデータの流れを先に取り出し、取ってきたデータが流れを変えられないようにする層。capability で道具を呼ぶときの方針を強制 | 道具を持つエージェント |
| F10 | Design Patterns for Securing LLM Agents against Prompt Injections | Beurer-Kellner L. ほか 14 名、arXiv 2025 | `2025-beurerkellner-design-patterns` | open（CC BY 4.0） | 証明できる形で注入に強くする設計の型の一覧と取引。最も単純な Action-Selector の型は、LLM が道具の結果を見ないので注入に影響されない（本文） | 道具を持つエージェント |

確認日はすべて 2026-11-05。種類はすべて論文。読了は Claude abstract（F10 だけ snippet）、本人 none。URL は `https://arxiv.org/abs/<番号>`（番号は図書室の `item.toml` の container）。arXiv の非独占配布ライセンスの物（quote）は、図書室の私的な写しで、GitHub に本文・図を写しません。

---

## 作者の類比との関係

作者の類比（植物と根圏微生物、人と病原菌、繋がったシステム。11-06 より前の基本計画 §1、設計書 §10.1）を、Claude はここで組み立てません。集めた資料の**中に**生物の比喩があるかを、`text.txt` を `rg`（immun、biolog、hygiene、vaccin、pathogen、免疫、衛生、病原、生物）で探しただけです。

- **B8（NCO のハンドブック）**: マルウェアを病気を起こす原因の総称「病原体」に、ウイルスを細胞に寄生しないと増殖できない病原体に例え、トロイの木馬・ワームを細菌などと並べる。「公衆衛生的なマナー意識」の語もある。
- **F1（ランサムウェアの総説）**: 自然と生物から着想した検知の手法と、人工免疫系（Artificial Immune System）に基づくランサムウェアの検知の研究に触れる。
- **「cyber hygiene」（衛生）の語**: C5（CISA）、C8（NSA）、C9（CIS の IG1 は「essential cyber hygiene」）、C11（ENISA）が使う。
- 他の資料で見つかった「immune」は、D6、F8、F10 の「注入に影響されない」の意味の普通の語で、比喩ではありません。「ecosystem」（生態系）の語は多くの資料にありますが、ソフトウェアの供給網・サービスの集まりの意味で、生物の話はしていません（開いた範囲）。
- 植物の防御、根圏微生物との協力の比喩を使う資料は、この一覧にはありません。植物の側の資料は `sources-defense.md` です。
