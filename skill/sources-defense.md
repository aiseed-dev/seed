# 植物の防御機構の資料の候補 — 誘導抵抗性、菌根菌、植食者への防御、窒素、混植

**ここにある物は候補です。本人がまだ一つも読んでいません。読んだ物だけ `sources.md` に移ります。根拠にはしません。** すべて「Claude が確認」です。

作者の依頼（2026-11-05「植物の防御機構の資料もあつめておいて」）で、Claude が集めました。章の中では「`sources-defense.md` の B3」の形で指します。`sources.md` の番号とは別です。

## 手引きのどこに効くか

- **04 生物（菌根菌・草・混植）**: B（菌根菌・土の微生物が誘導する抵抗性、発病抑止土壌）、E と F3・F4・F9・F10（間作・混作と害虫・病気）、C3・C4・C6・C7（ケイ素とトライコーム）、G（植物の間の信号）、H（有機・自然農法・不耕起の系）。混植の一次資料の候補は E1、E2、E11、E18〜E20、E25、F3、F4、F9、F10 などです。
- **06 畑を読む**: 防御している植物が写真でどう見えるかを書いた資料は、ここに**ありません**。F1 の「抵抗性誘導剤でトマトやキュウリの葉が黄化し生育が遅くなる」（p.73）は薬剤を与えた時の話です。D5（解説の冒頭）に「傷ついた植物は近くの傷ついていない植物より小さく見える」という一般論があるだけで、畑の写真の読みの資料ではありません。
- **10 種**: 品種・系統と防御を結ぶ候補が増えました（どれも要旨だけ）。栽培化で防御が弱まった話（C21〜C24）、品種の混植（E15〜E17、E25、F14）、品種と菌根菌の相性（B10）、品種によるトライコームの違い（C7、C8）、種子のプライミング（A12）と親から子への防御の伝わり（A22、A23）、成長と防御の取引と育種（D8、G3、G6）。
- **05 鳥獣害**: 脊椎動物を扱うのは C3（ハタネズミ、有蹄類）、C4（哺乳類を含むメタ解析）、C15（シジュウカラが食害された木の匂いで獲物を探す）、E13（鳥を除く囲いの試験を含む）、H12（自然農法の地域で害虫を食べる鳥が増えた）です。鳥を天敵として見る資料で、畑の作物のイノシシ・シカ・サル・鳥の**被害**を扱う資料は**ありません**。

## この一覧について

- 作ったのは Claude です（2026-11-05。同じ日に 20 件で始め、158 件を足した）。確認日は、すべて Claude が開いた日で、本人の確認日ではありません。
- 数: A 25、B 28、C 24、D 17、E 29、F 16、G 19、H 20、合わせて 178 件（図書室に 178 件）。足した 158 件の権利は open 54、quote 74、unknown 30。全文（XML か PDF）を図書室に置いたのは 48 件。足した 158 件の Claude の読了は abstract 150、snippet 4、none 4（題名と書誌だけ）で、**全文を読んだ物はありません**。全文を置いた物も、読んだのは要旨だけです。
- 探し方: Europe PMC の検索（題名の語と総説の型、被引用の多い順）、OpenAlex と Crossref の書誌、J-STAGE の検索。OpenAlex の検索はこの日は止まっていた（匿名の検索の一時停止）ので、OpenAlex は DOI での書誌の取得にだけ使いました。Europe PMC は医学寄りで、農学・生態学の雑誌は拾いにくく、有名な論文 26 件は DOI を指定して足しました。
- 資料の本体と書誌は研究室の図書室に置きました（`<研究室>/library/items/<id>/`）。リポジトリには本文を入れていません。
- **「書いてあること」は、Claude が開いて読めた範囲だけです。** ほとんどは要旨だけです。読んだ範囲（要旨、頁、節）を項目ごとに書きました。読了の欄の Claude の値: full（全部）、snippet（要旨と一部の節、または記録の要旨の欄に入っていた本文の冒頭）、abstract（要旨だけ）、none（題名と書誌だけ）。
- **権利**: open（CC の license を記録か本文で見た。全文を取れた物は原本を図書室に置いた。取れなかった物は書誌と要旨だけ）、admin（行政の資料。規約を書いた）、quote（著作物。図書室には書誌と要旨、または記事のページだけ。原本は置いていない）、unknown（ライセンスを見つけられなかった。原本は置いていない）。有料の PDF は置いていません。CC BY のほか、CC BY-NC、CC BY-NC-ND、CC BY-NC-SA、CC0 の物があります（項目ごとに書いた）。
- **前提**: 作物、系（室内・温室・圃場）、国・地域、施肥・農薬の有無。**書いていない物は「記載なし」**、要旨しか読んでいない物は「要旨からは分からない」です。どちらも「無い」の意味ではありません。
- **無肥料・無農薬に関わるか**: 項目ごとに書きました。無肥料・無農薬の畑で作物の防御を試験した資料は、要旨で確かめた範囲では**一つもありません**。近い物: 合成の肥料・農薬を使わない自然農法（ゼロ予算自然農法。牛糞・牛尿の資材とマルチは使う）の収量と土（H11）と鳥（H12）、30 年以上の「自然農法」のリンゴ園の病気と微生物（H13。病気は慣行より重かった。施肥の有無は要旨に無い）、窒素無施肥の区を持つ陸稲の保全農業（H10。いもち病が軽かった）、農薬なしのキャベツとクローバの間作（E11）。施肥の量・形を比べた資料（B8、B19、D2、D3、D7、D9、D12〜D14、E1、E20、H5、H18）、窒素を抜いた資料（B3）、植物の窒素の多少を見た資料（D4）、有機と慣行を比べた資料（F3、F7、F8、H1〜H6、H15、H16、H18〜H20）はあります。慣行の施肥・農薬の上での試験は、その旨を前提に書きました。
- 解釈（ある畑に当てはまるか）は書きません。

## 見つからなかった物（正直に）

- **無肥料・無農薬（自然農法）の畑と慣行の畑とで、作物の防御（誘導抵抗性、防御物質、害虫・病気の被害）を比べた一次資料**は、まだ見つけていません。近い物は上の「無肥料・無農薬に関わるか」に挙げた物だけです。日本の自然農法（無肥料）の畑の病害虫の試験は、J-STAGE の「有機栽培」「不耕起」の検索では出ませんでした。「自然農法」の語では探していません。
- **防御している植物が見た目（写真）でどう分かるか**を書いた資料は、見つけていません（06 に効く物が無い）。
- **農研機構・農林水産省の、誘導抵抗性・植物の防御の一般向けの解説**は、見つかりませんでした。農研機構の物は F7（有機 JAS の施設ミニトマトの 10 年）だけです。
- **J-STAGE の、アーバスキュラー菌根菌による病害抑制の日本語の総説**は、見つかりませんでした。菌根菌と植食者の総説（F5）はあります。
- **J-STAGE で CC の license が付いていた物は F8 の一件だけ**（CC BY-NC-SA 4.0）。他の日本語の資料は、記事のページだけを置きました。J-STAGE の検索は語が雑多な物まで拾い、森林学会の大会の要旨などが多く、論文は少なかった。
- **全文を取れなかった物**: 前回の MDPI（Access Denied）、Springer（Client Challenge）、Wiley、PubMed Central（reCAPTCHA の確認画面）、HAL、Turku・ETH の置き場に加え、今回は出版社のページを開きに行っていません（Europe PMC の全文 XML、bioRxiv と Chimia の PDF だけ取った）。CC の license があるのに全文を置けなかった物は 6 件（B18、B24、C18、E17、G3、H8。C18 は Europe PMC の XML に CC の記載が無く置かなかった。B24 と E17 は sciencedirect と Wiley に版があるが取りに行っていない）。
- **要旨が記録に無かった物**: H7（高投入と有機の系の病気、1995）、D16（Dordas 2008、養分と病害）、H17（Altieri & Nicholls 2003、土の肥沃度と害虫）、H19（Muneret ら 2018、有機農業と害虫防除の証拠）。題名と書誌だけで、中身は読んでいません。
- **要旨の欄に本文の冒頭が入っていた物**: A10、D5、E9（F11 は PDF の冒頭の一節だけ読んだ）。読めたのは冒頭だけです。
- **探していない物**: 鳥獣（イノシシ・シカ）への植物の防御、ウイルス病と媒介虫、線虫に絞った検索、雑草のアレロパシー、2025〜2026 年の新しい論文の網羅。

---

## (A) 誘導抵抗性（SAR・ISR、サリチル酸・ジャスモン酸、プライミング）

#### A1. The Induced Resistance Lexicon: Do's and Don'ts
- 著者・年: De Kesel J., Conrath U., Flors V., Luna E., Magerøy M.H., Mauch-Mani B., Pastor V., Pozo M.J., Pieterse C.M.J., Ton J., Kyndt T.（2021）
- 誌名: Trends in Plant Science 26(7): 685–691
- DOI: https://doi.org/10.1016/j.tplants.2021.01.001 （確認日 2026-11-05）
- 図書室の id: `2021-dekesel-ir-lexicon`（書誌と要旨だけ）
- 権利: quote（Crossref の license は Elsevier の user license。CC の記載は見ていない）
- 種類: 総説（言葉の使い方の提案）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物の免疫は構成的な防御と誘導される防御から成る。ある刺激を受けた後に、来る病原体・害虫への防御の力が高まった状態の表現型を「誘導抵抗性（IR）」と呼ぶ。言葉の混乱を整理するため、局所か全身か、直接の防御かプライミングされた防御か、の二つの面で IR を書く決まりを提案する。
- 前提: 用語の論文。作物・圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない（言葉の整理）。

#### A2. Induced Systemic Resistance for Improving Plant Immunity by Beneficial Microbes
- 著者・年: Yu Y., Gui Y., Li Z., Jiang C., Guo J., Niu D.（2022）
- 誌名: Plants 11(3): 386
- DOI: https://doi.org/10.3390/plants11030386 （確認日 2026-11-05）
- 図書室の id: `2022-yu-isr-microbes`（全文 XML、Europe PMC PMC8839143）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude snippet（要旨と節の見出し）、本人 none
- 書いてあること（要旨と見出し）: 有用微生物の施用で、宿主に広い病原体への抵抗性の高まった状態（誘導全身抵抗性、ISR）が起きる。ISR の信号の伝わりはジャスモン酸・エチレン依存でサリチル酸非依存とされてきたが、この十年で両方の経路と small RNA の役割が更新された。節は、微生物の認識、初期の応答（活性酸素、カロース、Ca²⁺、転写因子、防御遺伝子、二次代謝物、気孔）、信号の伝達、small RNA。
- 前提: 分子機構の総説。主に室内の研究の整理（各節を読んでいないので、扱う作物と系は確かめていない）。
- 無肥料・無農薬に関わるか: 開いた範囲では施肥に触れていない。

#### A3. Induced Systemic Resistance by Beneficial Microbes
- 著者・年: Pieterse C.M., Zamioudis C., Berendsen R.L., Weller D.M., Van Wees S.C., Bakker P.A.（2014）
- 誌名: Annual Review of Phytopathology 52(1): 347–375
- DOI: https://doi.org/10.1146/annurev-phyto-082712-102340 （確認日 2026-11-05）
- 図書室の id: `2014-pieterse-isr-beneficial-microbes`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 根の微生物叢の有用な細菌・菌類（Pseudomonas、Bacillus、Trichoderma、菌根菌）が、高くつく防御を直接動かさずに植物全体の免疫を感作（プライミング）し、広い範囲の病原体と植食性昆虫に対する防御を高める（ISR）。根の転写因子 MYB72 が ISR の始まりに中心的な役割を持つ。根の微生物叢の中での ISR を起こす微生物の生態的な働きも論じる。
- 前提: 総説。分子の研究のまとめ（要旨）。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### A4. Induced Systemic Resistance (ISR) Against Pathogens in the Context of Induced Plant Defences
- 著者・年: Heil M., Bostock R.M.（2002）
- 誌名: Annals of Botany 89(5): 503–512
- DOI: https://doi.org/10.1093/aob/mcf076 （確認日 2026-11-05）
- 図書室の id: `2002-heil-isr-induced-defences`（書誌と要旨だけ）
- 権利: quote（PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 総説（短い総説）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 局所の感染で起こり、サリチル酸に依存して全身に広がる、長く続く広い範囲の抵抗性（著者らは ISR と呼ぶが、内容は SAR に当たる）。細胞壁の変化、PR タンパク質（キチナーゼ、グルカナーゼ）、ファイトアレキシンが伴う。ジャスモン酸を介した植食者への誘導抵抗性との関係は、交差抵抗性の報告と、一方が他方を抑える取引の報告があり、誘導・信号・防御物質の生産の三つの段階を分けて考える枠組みを出す。
- 前提: 総説（Botanical Briefing）。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### A5. Triple interactions for induced systemic resistance in plants
- 著者・年: Jung J., Ahn S., Kim D.H., Riu M.（2024）
- 誌名: Frontiers in Plant Science 15: 1464710
- DOI: https://doi.org/10.3389/fpls.2024.1464710 （確認日 2026-11-05）
- 図書室の id: `2024-jung-isr-triple-interactions`（全文 XML、Europe PMC PMC11620860）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 地上部の病原体に感染した植物の根圏で有用微生物が増える「土の遺産効果（soil legacy effect）」と、それらの微生物が次の感染への防御を高めることを、地上の攻撃者・植物・根圏微生物・次の攻撃の四段の防御としてまとめる。動けない植物の限界を越える能動的な防御だ、と書く。
- 前提: 総説。Bacillus、Pseudomonas、Trichoderma の研究が中心。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### A6. Systemic Acquired Resistance: Turning Local Infection into Global Defense
- 著者・年: Fu Z.Q., Dong X.（2013）
- 誌名: Annual Review of Plant Biology 64(1): 839–863
- DOI: https://doi.org/10.1146/annurev-arplant-042811-105606 （確認日 2026-11-05）
- 図書室の id: `2013-fu-sar-local-global`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 全身獲得抵抗性（SAR）は特異性の無い広い範囲の誘導免疫。局所の細胞死を起こす病原体が移動する信号とサリチル酸の蓄積と PR タンパク質の分泌を起こし、植物の残りの部分を数週間から数か月守る。エピジェネティックな調節で子に伝わることもある。NPR1 が主な調節因子。
- 前提: 総説。シロイヌナズナの分子の研究。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない（分子の機構）。

#### A7. Systemic Acquired Resistance (50 Years after Discovery): Moving from the Lab to the Field
- 著者・年: Gozzo F., Faoro F.（2013）
- 誌名: Journal of Agricultural and Food Chemistry 61(51): 12473–12491
- DOI: https://doi.org/10.1021/jf404156x （確認日 2026-11-05）
- 図書室の id: `2013-gozzo-sar-lab-field`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: SAR の発見から 50 年の総説。信号、長距離の信号、外から与える誘導剤（合成と天然）、SAR を起こす殺菌剤、プライミングと次の世代への伝達、SAR の適応度の費用と利益、圃場での利用、圃場で効き方を左右する要因を順に扱う。管理された条件では見えない力が圃場で働いているらしい、と書く。
- 前提: 総説。圃場での利用の節を含む（要旨の目次）。
- 無肥料・無農薬に関わるか: 要旨からは分からない（圃場の効き方の要因の節はあるが中身は読んでいない）。

#### A8. Priming for Enhanced Defense
- 著者・年: Conrath U., Beckers G.J., Langenbach C.J., Jaskiewicz M.R.（2015）
- 誌名: Annual Review of Phytopathology 53(1): 97–119
- DOI: https://doi.org/10.1146/annurev-phyto-080614-120132 （確認日 2026-11-05）
- 図書室の id: `2015-conrath-priming-enhanced-defense`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は病原体、傷の信号、非生物ストレスを感じると、防御が速く強く動く「プライミング」の状態に入る。天然・合成の化学物質でも起こる。機構として、パターン認識受容体と休眠中の信号酵素の増加、転写因子 HsfB1、クロマチンの状態の変化、β-アミノ酪酸の受容体（アスパラギン酸 tRNA 合成酵素）を挙げる。プライミングの遺伝、農業での可能性も論じる。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### A9. Defense Priming: An Adaptive Part of Induced Resistance
- 著者・年: Mauch-Mani B., Baccelli I., Luna E., Flors V.（2017）
- 誌名: Annual Review of Plant Biology 68(1): 485–512
- DOI: https://doi.org/10.1146/annurev-arplant-042916-041132 （確認日 2026-11-05）
- 図書室の id: `2017-mauchmani-defense-priming-adaptive`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: プライミングは植物の防御の力を高める適応的な戦略。病原体、有用微生物、節足動物、化学物質、非生物の手がかりが警告の信号になり、生理・転写・代謝・エピジェネティックな変化が起こる（プライミングの段階）。次の攻撃で速く強い防御が出る。植物の一生続き、次の世代に伝わることもあり、植物の免疫の記憶の一つの形。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。

#### A10. Plant Defense Priming against Herbivores: Getting Ready for a Different Battle
- 著者・年: Frost C.J., Mescher M.C., Carlson J.E., De Moraes C.M.（2008）
- 誌名: Plant Physiology 146(3): 818–824
- DOI: https://doi.org/10.1104/pp.107.113027 （確認日 2026-11-05）
- 図書室の id: `2008-frost-priming-herbivores`（書誌と要旨だけ）
- 権利: quote（OUP の標準の出版モデルの頁。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude snippet、本人 none
- 書いてあること（記録の要旨の欄＝本文の冒頭）: OpenAlex の記録の要旨の欄には本文の冒頭が入っていた。読んだ冒頭: 誘導防御が適応的なのは、防御が高くつく、敵の分布が時間・空間で変わる、敵の間で防御の取引がある、の三つの時。誘導が間に合わない弱さを補うため、攻撃の確率が上がったことを知らせる手がかり（食害された隣の植物の揮発性物質など）で、植物が防御をプライミングする、という概念の模式図を出す。
- 前提: 総説。圃場の試験ではない。記録の要旨の欄の文は途中から語が抜けていて、全体は読めていない。
- 無肥料・無農薬に関わるか: 関わらない。

#### A11. Chemical priming of plant defense responses to pathogen attacks
- 著者・年: Hönig M., Roeber V.M., Schmülling T., Cortleven A.（2023）
- 誌名: Frontiers in Plant Science 14: 1146577
- DOI: https://doi.org/10.3389/fpls.2023.1146577 （確認日 2026-11-05）
- 図書室の id: `2023-honig-chemical-priming`（全文 XML、Europe PMC PMC10200928）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 天然・人工の化合物を外から与えると、病原体の攻撃への反応が早く・速く・強くなる（化学的プライミング）。プライミングされた防御は、ストレスの無い期間を越えて続き、処理していない器官にも出ることがある。ISR と SAR での化学的プライミングの信号の経路、NPR1 の役割、農業での使い方をまとめる。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない（与える化合物の話）。

#### A12. A comprehensive meta-analysis reveals the key variables and scope of seed defense priming
- 著者・年: Talavera-Mateo L., Garcia A., Santamaria M.E.（2023）
- 誌名: Frontiers in Plant Science 14: 1208449
- DOI: https://doi.org/10.3389/fpls.2023.1208449 （確認日 2026-11-05）
- 図書室の id: `2023-talaveramateo-seed-priming-meta`（全文 XML、Europe PMC PMC10398571）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 種子の防御プライミングの、全ての入手できる実験データのメタ解析。種子プライミングは植物の抵抗性を高め、病原体・害虫の成績を下げ、植物の適応度の罰を伴わなかった。作物と穀類に正の効果、菌類・細菌・節足動物に負の効果。植物の天然化合物と生物の分離株が、合成化学物質や揮発性物質より強く効いた。
- 前提: メタ解析。作物・系・施肥の条件は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。種子に生物の分離株や天然化合物を使う話で、10 種に関わり得る。

#### A13. Hormone Crosstalk in Plant Disease and Defense: More Than Just JASMONATE-SALICYLATE Antagonism
- 著者・年: Robert-Seilaniantz A., Grant M., Jones J.D.（2011）
- 誌名: Annual Review of Phytopathology 49(1): 317–343
- DOI: https://doi.org/10.1146/annurev-phyto-073009-114447 （確認日 2026-11-05）
- 図書室の id: `2011-robertseilaniantz-hormone-crosstalk-disease`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 病原体との関係でのホルモンの研究は SA・JA・ET が中心だったが、病原体はオーキシン、アブシジン酸、サイトカイニン、ブラシノステロイドの信号も操って病原性を高める。結果は病原体の生き方と宿主の遺伝で変わる。信号の正と負の調節因子がホルモンの間の干渉の標的になる、と論じる。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。

#### A14. Signaling Crosstalk between Salicylic Acid and Ethylene/Jasmonate in Plant Defense: Do We Understand What They Are Whispering?
- 著者・年: Li N., Han X., Feng D., Yuan D., Huang L.J.（2019）
- 誌名: International Journal of Molecular Sciences 20(3): 671
- DOI: https://doi.org/10.3390/ijms20030671 （確認日 2026-11-05）
- 図書室の id: `2019-li-sa-et-ja-crosstalk`（全文 XML、Europe PMC PMC6387439）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: SA の経路は生きた細胞から栄養を取る病原体（Pseudomonas syringae など）への局所と全身の抵抗性に、ET/JA の経路は宿主を殺して栄養を取る病原体（Botrytis cinerea など）への防御に中心的に働く。SA と ET/JA の経路は互いに抑え合う、という証拠が増えている。他のホルモンは主にこの二つを調節して免疫に関わる。
- 前提: 総説。シロイヌナズナ中心。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。

#### A15. Jasmonate Signaling Pathway Modulates Plant Defense, Growth, and Their Trade-Offs
- 著者・年: Li C., Xu M., Cai X., Han Z., Si J., Chen D.（2022）
- 誌名: International Journal of Molecular Sciences 23(7): 3945
- DOI: https://doi.org/10.3390/ijms23073945 （確認日 2026-11-05）
- 図書室の id: `2022-li-jasmonate-growth-tradeoff`（全文 XML、Europe PMC PMC8999811）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ジャスモン酸（JA）の合成、中心の信号経路、終わらせる仕組み、進化の起源。JA は再生・生殖・栄養成長と、病原体・ウイルス・植食者・非生物ストレスへの応答を調節する。ジベレリン、オーキシン、フィトクロムの信号との干渉で成長と防御の取引を仲立ちし、複雑な環境に合わせて両者の釣り合いを取る。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。

#### A16. Salicylic Acid Steers the Growth–Immunity Tradeoff
- 著者・年: van Butselaar T., Van den Ackerveken G.（2020）
- 誌名: Trends in Plant Science 25(6): 566–576
- DOI: https://doi.org/10.1016/j.tplants.2020.02.002 （確認日 2026-11-05）
- 図書室の id: `2020-vanbutselaar-salicylic-growth-immunity`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: SA の蓄積は大きな転写の組み換え、細胞壁の強化、二次代謝物と抗菌タンパク質の生産を起こすが、その代わりに成長と発達を能動的に抑える。逆に盛んな成長と発達は SA の生産と免疫を抑える。この取引を迂回した例を挙げ、成長と免疫の両方を備えた抵抗性の育種に役立つと書く。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。育種の話で 10 に関わり得る。

#### A17. Practical application of induced resistance to plant diseases: an appraisal of effectiveness under field conditions
- 著者・年: Walters D.R., Fountaine J.M.（2009）
- 誌名: The Journal of Agricultural Science 147(5): 523–535
- DOI: https://doi.org/10.1017/s0021859609008806 （確認日 2026-11-05）
- 図書室の id: `2009-walters-ir-field-appraisal`（書誌と要旨だけ）
- 権利: quote（Cambridge の利用規約。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: SAR（サリチル酸と NPR1 に依存）と ISR（根圏細菌が起こし、JA・ET に依存）を説明し、誘導抵抗性は広い範囲に長く効くが完全でなく、多くの誘導剤の防除は 0.20〜0.85 に留まる、と書く。圃場では環境、遺伝子型、作物の栄養、植物がすでに誘導されている程度が効き方に影響するはずだが、その理解はまだ初歩的。
- 前提: 総説（圃場での効き方の評価）。
- 無肥料・無農薬に関わるか: 間接に関わる（作物の栄養と、すでに誘導されている程度が効き方に影響する、と要旨にある）。中身は読んでいない。

#### A18. Effect of Application Frequency and Reduced Rates of Acibenzolar-S-Methyl on the Field Efficacy of Induced Resistance Against Bacterial Spot on Tomato
- 著者・年: Huang C.H., Vallad G.E., Zhang S., Wen A., Balogh B., Figueiredo J.F.L., Behlau F., Jones J.B. ほか（2012）
- 誌名: Plant Disease 96(2): 221–227
- DOI: https://doi.org/10.1094/pdis-03-11-0183 （確認日 2026-11-05）
- 図書室の id: `2012-huang-asm-tomato-field`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 一次（圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 合成の誘導剤アシベンゾラル-S-メチル（ASM）をトマトの細菌性斑点病に、米国フロリダの圃場で試した。2 週に 1 回の散布は、銅・マンコゼブの慣行や無処理と比べて病気を有意に減らさなかった（4 試験のうち 1 試験だけ最高濃度で減った）。2009–10 年の 3 試験では毎週の散布が 2 週ごとより良く効いた。収量は無処理と慣行に比べて上がらなかった。
- 前提: 米国フロリダの圃場、2007–2010 年。慣行区は銅・マンコゼブ。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わらない（合成の誘導剤の散布）。

#### A19. Induced resistance in potato to Phytphthora infestans—effects of BABA in greenhouse and field tests with different potato varieties
- 著者・年: Liljeroth E., Bengtsson T., Wiik L., Andreasson E.（2010）
- 誌名: European Journal of Plant Pathology 127(2): 171–183
- DOI: https://doi.org/10.1007/s10658-010-9582-4 （確認日 2026-11-05）
- 図書室の id: `2010-liljeroth-baba-potato-blight`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（温室と圃場）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: β-アミノ酪酸（BABA）でジャガイモの疫病への抵抗性を誘導した。温室では病斑が平均 40〜50% 小さくなったが、効果は処理後 4〜5 日しか続かなかった。部分抵抗性の品種（Ovatio、Superb）は感受性の Bintje より低い濃度で反応した。圃場では、殺菌剤の量を 20〜25% 減らして BABA と組み合わせると、全量の殺菌剤と同じくらいだった。
- 前提: スウェーデンの圃場と温室。殺菌剤（Shirlan）との組み合わせ。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わらない（殺菌剤との組み合わせ）。品種で反応が違う点は 10 に関わり得る。

#### A20. The Practical Role of Induced Resistance for Crop Protection
- 著者・年: Reglinski T., Havis N., Rees H.J., de Jong H.（2023）
- 誌名: Phytopathology® 113(4): 719–731
- DOI: https://doi.org/10.1094/phyto-10-22-0400-ia （確認日 2026-11-05）
- 図書室の id: `2023-reglinski-ir-practical-role`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 誘導抵抗性は実験室と温室では病気を抑えるが、圃場で合成農薬と同じ水準になることはまれ。合成化学物質を減らす法の動きで関心が戻っている。殺菌剤・殺細菌剤や他の生物的防除と組み合わせれば、効き目を落とさずに化学物質を減らせる。作付け体系ごとの使い方と、他の耕種的な防除との組み合わせを論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（農薬を減らす文脈）。無農薬の畑の話ではない。

#### A21. Induced resistance against spider mites in cotton: Field verification
- 著者・年: Karban R.（1986）
- 誌名: Entomologia Experimentalis et Applicata 42(3): 239–242
- DOI: https://doi.org/10.1111/j.1570-7458.1986.tb01028.x （確認日 2026-11-05）
- 図書室の id: `1986-karban-cotton-mites-field`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 子葉の時期にハダニや機械的なこすりで傷を受けたワタは、その季節の早い時期にハダニが付きにくかった。誘導抵抗性が農業の系で害虫の数を減らせることを示した最初の圃場の結果、と書く。季節初めのハダニの差は、収穫時の生育や収量の差にはならなかった。
- 前提: ワタの圃場（国は要旨からは分からない）。施肥・農薬は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。若い時の傷が後の抵抗性になる、という点は作者の見立て（攻撃されて逞しくなる）を確かめる材料になり得る。

#### A22. Transgenerational Defense Priming for Crop Protection against Plant Pathogens: A Hypothesis
- 著者・年: Ramírez-Carrasco G., Martínez-Aguilar K., Alvarez-Venegas R.（2017）
- 誌名: Frontiers in Plant Science 8: 696
- DOI: https://doi.org/10.3389/fpls.2017.00696 （確認日 2026-11-05）
- 図書室の id: `2017-ramirezcarrasco-transgenerational-priming-bean`（全文 XML、Europe PMC PMC5415615）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: β-アミノ酪酸でインゲンマメに Pseudomonas syringae pv. phaseolicola への抵抗性を誘導し、プライミングによく反応する PvPR1 遺伝子の発現の型が少なくとも 2 世代続くことを示した。育種で、誘導剤で圃場の抵抗性をプライミングし、防御に向けてプライミングされた状態が遺伝した子を選ぶべきだ、と提案する。
- 前提: インゲンマメ。系は要旨からは分からない（遺伝子発現の解析）。
- 無肥料・無農薬に関わるか: 関わらない。種と世代の話で 10 に関わり得る。

#### A23. Transgenerational effects alter plant defence and resistance in nature
- 著者・年: Colicchio J.（2017）
- 誌名: Journal of Evolutionary Biology 30(4): 664–680
- DOI: https://doi.org/10.1111/jeb.13042 （確認日 2026-11-05）
- 図書室の id: `2017-colicchio-transgenerational-mimulus`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 一次（野外）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ミゾホオズキの一種（Mimulus guttatus）で、葉の毛（トライコーム）が植食者への防御に働くことを示し、親が傷を受けると子のトライコームの密度と植食者への抵抗性が野外で変わることを示した。この応答は集団で違った。
- 前提: 野生植物（Mimulus guttatus）の野外。
- 無肥料・無農薬に関わるか: 関わらない（野生植物）。親の経験が子の防御を変える点は 10 種に関わり得る。

#### A24. Trichoderma-Induced Resistance to Botrytis cinerea in Solanum Species: A Meta-Analysis
- 著者・年: Risoli S., Cotrozzi L., Sarrocco S., Nuzzaci M., Pellegrini E., Vitti A.（2022）
- 誌名: Plants 11(2): 180
- DOI: https://doi.org/10.3390/plants11020180 （確認日 2026-11-05）
- 図書室の id: `2022-risoli-trichoderma-botrytis-meta`（全文 XML、Europe PMC PMC8780288）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトで、Trichoderma が灰色かび病（Botrytis cinerea）に起こす抵抗性の研究（2010〜2021 年）のメタ解析。40 本から 15 本を選び 9 の指標を解析した。Trichoderma は葉の灰色かび病の強さ・重さ・発生を減らし、抵抗性の遺伝子を調節した。文献の弱い所も指摘する。
- 前提: トマト。系（室内・温室・圃場）は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### A25. Controlling crop diseases using induced resistance: challenges for the future
- 著者・年: Walters D.R., Ratsep J., Havis N.D.（2013）
- 誌名: Journal of Experimental Botany 64(5): 1263–1280
- DOI: https://doi.org/10.1093/jxb/ert026 （確認日 2026-11-05）
- 図書室の id: `2013-walters-ir-challenges-future`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 誘導抵抗性は広い範囲に長く効くが完全ではなく、多くの誘導剤は病気を 20〜85% 減らす。宿主の応答なので、圃場での発現は、環境、遺伝子型、作物の栄養、すでに誘導されている程度に左右されるはずだが、その理解はまだ乏しい。実際の作物保護での使い方の研究は少なく、病害管理に組み込む研究が要る。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（作物の栄養が誘導抵抗性の発現に影響する、と要旨にある）。A17（Walters ら 2009）と同じ筆頭著者。

## (B) 菌根菌と土の有用微生物が誘導する抵抗性

#### B1. Mycorrhiza-induced resistance: more than the sum of its parts?
- 著者・年: Cameron D.D., Neal A.L., van Wees S.C.M., Ton J.（2013）
- 誌名: Trends in Plant Science 18(10): 539–545
- DOI: https://doi.org/10.1016/j.tplants.2013.06.004 （確認日 2026-11-05）
- 図書室の id: `2013-cameron-mir`（書誌と要旨だけ）
- 権利: unknown（Crossref に license の記録が無く、PMC のページは確認画面で開けなかった）
- 種類: 総説（意見論文）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アーバスキュラー菌根菌（AMF）の感染で、植物の防御の力が高まる（菌根誘導抵抗性、MIR）。MIR は広い加害者に全身の保護を与え、SAR・ISR と性質を共有する。菌が免疫を刺激するだけではなく、菌根への植物の直接の応答と、菌根圏の根圏細菌が起こす ISR の、積み重ねだという模型を出す。
- 前提: 模型の提案。試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B2. Mycorrhiza-Induced Resistance and Priming of Plant Defenses
- 著者・年: Jung S.C., Martinez-Medina A., Lopez-Raez J.A., Pozo M.J.（2012）
- 誌名: Journal of Chemical Ecology 38(6): 651–664
- DOI: https://doi.org/10.1007/s10886-012-0134-6 （確認日 2026-11-05）
- 図書室の id: `2012-jung-mir-priming`（書誌と要旨だけ）
- 権利: quote（Springer の TDM の license。OA の版は確かめていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: AMF との共生は、病原体・害虫・寄生植物に対する保護の効果が多くの作物で記載されている。養分の改善と競争に加え、植物の防御が大きな役割を持つ証拠がある。菌根の成立の間に防御が調節され、穏やかだが効く免疫の活性化が局所と全身に起き、プライミングの状態になる。ジャスモン酸で調節される防御のプライミングに焦点を当てる。
- 前提: 総説。扱う作物と系は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨では「養分の改善」に触れるだけ。施肥の比較は分からない。

#### B3. The Nitrogen Availability Interferes with Mycorrhiza-Induced Resistance against Botrytis cinerea in Tomato
- 著者・年: Sanchez-Bel P., Troncho P., Gamir J., Pozo M.J., Camañes G., Cerezo M., Flors V.（2016）
- 誌名: Frontiers in Microbiology 7: 1598
- DOI: https://doi.org/10.3389/fmicb.2016.01598 （確認日 2026-11-05）
- 図書室の id: `2016-sanchezbel-nitrogen-mir`（PDF）
- 権利: open（CC BY、PDF の 1 頁）
- 種類: 一次（実験）
- 読了: Claude snippet（要旨 p.1、方法の栽培条件 p.2–3）、本人 none
- 書いてあること（要旨と方法）: Rhizophagus irregularis を定着させたトマトは、灰色かび病菌（Botrytis cinerea）で病斑が小さく、菌量も少ない。感染の 48 時間前に窒素を抜いた養液に替えた株は灰色かび病に弱くなり、MIR は大きく損なわれるが働きは残る。著者らは、AMF が一時的な窒素欠乏による弱さを緩衝する、と要旨で結ぶ。結果と考察の本文は読んでいない。
- 前提: トマト cv. Better Boy、温室の鉢、養液（Long Ashton 液、方法の節）。窒素欠乏は 48 時間の一時的な処理。スペイン。圃場ではない。
- 無肥料・無農薬に関わるか: 窒素の有無を変えた実験だが、養液で育てた株の 48 時間の窒素抜きで、無肥料の畑の土の窒素とは別の物。

#### B4. Synergistic benefits of AMF: development of sustainable plant defense system
- 著者・年: Boyno G., Rezaee Danesh Y., Çevik R., Teniz N., Demir S., Demirer Durak E., Farda B., Mignini A., Djebaili R., Pellegrini M., Porcel R., Mulet J.M.（2025）
- 誌名: Frontiers in Microbiology 16: 1551956
- DOI: https://doi.org/10.3389/fmicb.2025.1551956 （確認日 2026-11-05）
- 図書室の id: `2025-boyno-amf-defense`（PDF）
- 権利: open（CC BY、PDF の 1 頁）
- 種類: 総説
- 読了: Claude snippet（要旨 p.1、2 章の終わり p.4、節の見出し）、本人 none
- 書いてあること（要旨と p.4）: AMF は陸上植物の 80% 以上の根と共生する。養分の吸収、ストレスへの強さ、病気への抵抗性、AMF が誘導する全身抵抗性を整理する総説。Table 1 は「AMF の露地での施用」の近年の研究の一覧だと本文が言う（表の中身は読んでいない）。
- 前提: 総説。市販の菌の資材（接種）の話を含む（要旨）。土着の菌根菌を活かす畑と、接種する畑の区別は、読んだ範囲には無い。
- 無肥料・無農薬に関わるか: 7 章が「AMF と慣行の農業」の題（読んでいない）。要旨は化学肥料・農薬への依存を減らす、と言う。

#### B5. Unraveling mycorrhiza-induced resistance
- 著者・年: Pozo M.J., Azcón-Aguilar C.（2007）
- 誌名: Current Opinion in Plant Biology 10(4): 393–398
- DOI: https://doi.org/10.1016/j.pbi.2007.05.004 （確認日 2026-11-05）
- 図書室の id: `2007-pozo-unraveling-mir`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アーバスキュラー菌根を持つ植物では、土の病原体への抵抗性の高まりが広く報告されている。地上部の病気への効果は、攻撃者の生き方と攻め方に大きく左右される。菌根の系の抵抗性の機構の候補のうち、植物の防御の誘導が最も議論がある。菌根ができる間に、SA と JA の経路の干渉を通じて防御の応答が調節され、それが組織をプライミングするらしい。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B6. Role and mechanisms of callose priming in mycorrhiza-induced resistance
- 著者・年: Sanmartín N., Pastor V., Pastor-Fernández J., Flors V., Pozo M.J., Sánchez-Bel P.（2020）
- 誌名: Journal of Experimental Botany 71(9): 2769–2781
- DOI: https://doi.org/10.1093/jxb/eraa030 （確認日 2026-11-05）
- 図書室の id: `2020-sanmartin-callose-priming-mir`（全文 XML、Europe PMC PMC7210776）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（温室・室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 菌根菌 Rhizoglomus irregularis を定着させたトマトは、灰色かび病菌の感染でカロース（細胞壁を補強する多糖）の蓄積がプライミングされた。カロースの阻害剤で MIR が消えた。菌根の植物では病原体の感染後にデンプンの分解が速く、糖の輸送体、小胞輸送のタンパク質、カロース合成酵素の遺伝子の発現が高かった。
- 前提: トマト（鉢）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B7. Mycorrhiza-Induced Resistance against Foliar Pathogens Is Uncoupled of Nutritional Effects under Different Light Intensities
- 著者・年: Pozo de la Hoz J., Rivero J., Azcón-Aguilar C., Urrestarazu M., Pozo M.J.（2021）
- 誌名: Journal of Fungi 7(6): 402
- DOI: https://doi.org/10.3390/jof7060402 （確認日 2026-11-05）
- 図書室の id: `2021-pozodelahoz-mir-light-nutrition`（全文 XML、Europe PMC PMC8224078）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 菌根のあるレタスとないレタスを 5 段階の光の強さで育て、灰色かび病への抵抗性を比べた。菌根の定着は光の強さに強く左右された。菌根が生育と養分に与える効果は光の強さで変わったが、菌根は全ての光の強さで発病と重さを減らした。MIR は栄養の効果と切り離せる、つまり栄養や生育の利益が無くても菌根は病気からの保護を与えうる、と結ぶ。
- 前提: レタス。光の強さを変えた制御条件（室内）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 間接に関わる（菌根の防御の効果が栄養の効果と別に出る）。

#### B8. Phosphorus availability drives mycorrhiza induced resistance in tomato
- 著者・年: Dejana L., Ramírez-Serrano B., Rivero J., Gamir J., López-Ráez J.A., Pozo M.J.（2022）
- 誌名: Frontiers in Plant Science 13: 1060926
- DOI: https://doi.org/10.3389/fpls.2022.1060926 （確認日 2026-11-05）
- 図書室の id: `2022-dejana-phosphorus-mir-tomato`（全文 XML、Europe PMC PMC9806178）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（温室）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトと菌根菌 Funneliformis mosseae で、リン施肥の中程度の違いが MIR に与える影響を見た。リン施肥は植物の栄養価、防御、病気の進み、イモムシ（シロイチモジヨトウ）の生存に影響し、その効果は菌根の有無で変わった。菌根による灰色かび病とイモムシへの抵抗性はリンの量に依存し、最もリンが少ない条件では保護が見られなかった。中程度のリンでは防御のプライミングが見られたが、強いリン欠乏では見られなかった。
- 前提: トマト、リン施肥の段階を変えた試験（温室か室内かは要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わる（リンが最も少ない条件では菌根の保護が出なかった）。リン 0 の区かどうかは要旨からは分からない。

#### B9. Ethylene signaling is essential for mycorrhiza-induced resistance against chewing herbivores in tomato
- 著者・年: Lidoy J., Rivero J., Ramšak Ž., Petek M., Križnik M., Flors V., Lopez-Raez J.A., Martinez-Medina A. ほか（2025）
- 誌名: Journal of Experimental Botany 76(7): 2005–2021
- DOI: https://doi.org/10.1093/jxb/eraf053 （確認日 2026-11-05）
- 図書室の id: `2025-lidoy-ethylene-mir-herbivores`（全文 XML、Europe PMC PMC12066123）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 菌根菌 Funneliformis mosseae はトマトを二種の噛む植食者（シロイチモジヨトウ、タバコスズメガ）から守った。菌根の植物の葉では植食者で動く JA の防御がプライミングされ、エチレンの合成と信号も食害の前後で高かった。エチレンを作れない・感じない系統では、菌根による JA のプライミングも MIR も起こらなかった。
- 前提: トマト（遺伝子組換えの系統を含む）。室内の試験。
- 無肥料・無農薬に関わるか: 関わらない（機構の研究）。

#### B10. Symbiotic compatibility between rice cultivars and arbuscular mycorrhizal fungi genotypes affects rice growth and mycorrhiza-induced resistance
- 著者・年: Guigard L., Jobert L., Busset N., Moulin L., Czernic P.（2023）
- 誌名: Frontiers in Plant Science 14: 1278990
- DOI: https://doi.org/10.3389/fpls.2023.1278990 （確認日 2026-11-05）
- 図書室の id: `2023-guigard-rice-amf-compatibility`（全文 XML、Europe PMC PMC10628536）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: イネ 6 品種（indica 2、japonica 4）と菌根菌 3 系統の組み合わせで、菌根の定着の度合い（27〜84%）、生育（乾物重 −21〜+227%）、白葉枯病の症状が組み合わせで大きく違った。Rhizophagus irregularis DAOM197198 が最も相性がよく、症状を 6〜27% 減らした。Azucena と R. intraradices の組み合わせでは黄化が 68% 増えた。
- 前提: イネ、制御条件の試験（要旨からは系は分からない）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。品種と菌の相性で結果が逆にもなる点は 10 種に関わる。

#### B11. The rhizosphere microbiome and plant health
- 著者・年: Berendsen R.L., Pieterse C.M., Bakker P.A.（2012）
- 誌名: Trends in Plant Science 17(8): 478–486
- DOI: https://doi.org/10.1016/j.tplants.2012.04.001 （確認日 2026-11-05）
- 図書室の id: `2012-berendsen-rhizosphere-microbiome-health`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 根に付く微生物は数万種に及び、「植物の第二のゲノム」として健康に欠かせない。同じ土で育てても植物の種が違えば根圏の微生物群集が違い、植物は根圏の微生物叢を形づくる。病原体や虫に攻撃されると、植物は守ってくれる微生物を呼び寄せ、根圏の微生物の活動を高めて病原体を抑える、という証拠を論じる。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B12. Foliar Pathogen Infection Manipulates Soil Health through Root Exudate-Modified Rhizosphere Microbiome
- 著者・年: Luo L., Zhang J., Ye C., Li S., Duan S., Wang Z., Huang H., Liu Y. ほか（2022）
- 誌名: Microbiology Spectrum 10(6): e02418-22
- DOI: https://doi.org/10.1128/spectrum.02418-22 （確認日 2026-11-05）
- 図書室の id: `2022-luo-foliar-infection-soil-health`（全文 XML、Europe PMC PMC9769671）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内・ポット）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 三七人参（Panax notoginseng）で、葉の病原菌（Alternaria panax）の感染が、植物と土のフィードバックを負から正に変えた。葉の感染で根圏の微生物群集が変わり、土の病原菌 Ilyonectria destructans の増加が逆転し、Trichoderma、Bacillus、Streptomyces などの有用菌が増えた。根からの有機酸・糖・アミノ酸の滲出が増え、それらが病原体を抑えつつ有用菌を増やした。
- 前提: 三七人参（連作障害が問題の薬用作物）。室内と植木鉢の試験（in vitro と in 国は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。地上部の攻撃で地下の土が良くなる例で、作者の見立てに関わる。

#### B13. The Chemistry of Stress: Understanding the ‘Cry for Help’ of Plant Roots
- 著者・年: Rizaludin M.S., Stopnisek N., Raaijmakers J.M., Garbeva P.（2021）
- 誌名: Metabolites 11(6): 357
- DOI: https://doi.org/10.3390/metabo11060357 （確認日 2026-11-05）
- 図書室の id: `2021-rizaludin-cry-for-help-roots`（全文 XML、Europe PMC PMC8228326）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 地上部と同じく、根もストレスを受けると有用な微生物を呼び寄せて被害を減らす「助けを呼ぶ叫び」の応答を持つらしい。呼び寄せは、少なくとも一部は根の滲出物の量と質の変化による。揮発性と水溶性の両方の化合物が信号に関わる。
- 前提: 総説。圃場の試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。

#### B14. Toward understanding the genetic bases underlying plant‐mediated “cry for help” to the microbiota
- 著者・年: Wang Z., Song Y.（2022）
- 誌名: iMeta 1(1): e8
- DOI: https://doi.org/10.1002/imt2.8 （確認日 2026-11-05）
- 図書室の id: `2022-wang-cry-for-help-genetics`（全文 XML、Europe PMC PMC10989820）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ストレスに応じて植物が微生物叢を作り直すことが利益になる、という「助けを呼ぶ」仮説を、宿主の遺伝的な調節因子からまとめる。多くの変異体で微生物叢が変わるが、特定の微生物の変化と植物の表現型（適応度の利益など）の因果を確かめるのは難しい。ストレスの時に有用な微生物を呼べる作物の設計に役立つと書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。作物の設計（育種）で 10 に関わり得る。

#### B15. A cry for help from leaf to root
- 著者・年: Yi H.S., Yang J.W., Ghim S.Y., Ryu C.M.（2011）
- 誌名: Plant Signaling & Behavior 6(8): 1192–1194
- DOI: https://doi.org/10.4161/psb.6.8.15780 （確認日 2026-11-05）
- 図書室の id: `2011-yi-cry-leaf-to-root`（書誌と要旨だけ）
- 権利: quote（PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 短報（自身の研究の紹介）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 葉にコナジラミが付くと、空気伝染の病原体と土の病原体の両方への全身の防御が動いた（SA と JA の経路の PR 遺伝子の全身の発現）。さらに植物は、コナジラミを減らす根圏の植物生育促進細菌・菌類を呼び寄せて、次の食害から自分を守った。地上と地下の植物を介したやり取りは予想より普通だ、と書く。
- 前提: 著者らの研究の紹介（作物は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。食害が根圏の有用菌を呼ぶ例で、作者の見立てに関わる。

#### B16. Revisiting the cry-for-help hypothesis in plant–microbe interactions
- 著者・年: Tharp C.L., Custer G.F., Castrillo G., Dini-Andreote F.（2026）
- 誌名: Trends in Plant Science 31(1): 14–16
- DOI: https://doi.org/10.1016/j.tplants.2025.07.015 （確認日 2026-11-05）
- 図書室の id: `2026-tharp-revisiting-cry-for-help`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 意見（短い論文）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ストレスの下で根の滲出物が変わり有用な微生物が呼び寄せられる、という「助けを呼ぶ」仮説は広く使われているが、よくある誤解と限界を検討し、仮説を見直すべきだと主張する。
- 前提: 意見の論文。試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。仮説に対する批判として、B の他の候補と合わせて読む物。

#### B17. Deciphering the mechanism of fungal pathogen‐induced disease‐suppressive soil
- 著者・年: Wen T., Ding Z., Thomashow L.S., Hale L., Yang S., Xie P., Liu X., Wang H. ほか（2023）
- 誌名: New Phytologist 238(6): 2634–2650
- DOI: https://doi.org/10.1111/nph.18886 （確認日 2026-11-05）
- 図書室の id: `2023-wen-cucumber-suppressive-soil`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（室内・ポット）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: キュウリにつる割病菌を接種して 8 世代続けて育て（根を二つに分けた系）、土を条件付けた。感染に伴って発病が次第に減り、根の活性酸素が増え、Bacillus と Sphingomonas が溜まった。これらの菌は根の活性酸素を高めてキュウリを守った。トレオン酸とリシンがこれらの菌を呼ぶ鍵らしい。発病抑止土壌ができる基本の仕組みの一つかもしれない、と書く。
- 前提: キュウリ、ポットで 8 作の連作。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。連作で病気が減る（抑止土壌）点は畑の連作の話に関わる。

#### B18. Plant-Driven Assembly of Disease-Suppressive Soil Microbiomes
- 著者・年: Spooren J., van Bentum S., Thomashow L.S., Pieterse C.M.J., Weller D.M., Berendsen R.L.（2024）
- 誌名: Annual Review of Phytopathology 62(1): 1–30
- DOI: https://doi.org/10.1146/annurev-phyto-021622-100127 （確認日 2026-11-05）
- 図書室の id: `2024-spooren-suppressive-soil-assembly`（書誌と要旨だけ。CC BY 4.0 だが全文は取れなかった）
- 権利: open（CC BY 4.0、Crossref）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は種子・土・空気から微生物に定着されるが、根の滲出物で微生物叢を選び、免疫で門番と見張りをする。発病抑止土壌は、ふつう病気の最初の流行の後にでき、特定の微生物が溜まって病原体を抑える。コムギの立枯病の衰退（take-all decline）などから、病原体に攻撃された植物が助けを呼び、守る微生物を集め、次の世代を守る土の遺産を作る、という概念のモデルを出す。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。病気の流行の後に土が病気を抑えるようになる、という点は畑の年を重ねた変化に関わる。

#### B19. Phosphorus availability influences disease-suppressive soil microbiome through plant-microbe interactions
- 著者・年: Cao Y., Shen Z., Zhang N., Deng X., Thomashow L.S., Lidbury I., Liu H., Li R. ほか（2024）
- 誌名: Microbiome 12(1): 185
- DOI: https://doi.org/10.1186/s40168-024-01906-w （確認日 2026-11-05）
- 図書室の id: `2024-cao-phosphorus-suppressive-microbiome`（全文 XML、Europe PMC PMC11439275）
- 権利: open（CC BY-NC-ND 4.0、本文の記載）
- 種類: 一次（圃場 6 年と温室）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトの連作で施肥を変えた 6 年の圃場試験で、リンの量が青枯病の抑制を左右する鍵だった。温室試験で、リン不足を和らげると根圏（周りの土ではなく）の微生物叢の病気を抑える力が上がった。リンが足りると根から L-トリプトファンなどが出て Chryseobacterium などが増えた。リンが不足すると、ブルメノール A やケルセチンを出して菌根菌との共生を作る別の防御の戦略に移った。
- 前提: トマトの連作、6 年の圃場試験（国は要旨からは分からない）と温室。施肥を変えた区がある。
- 無肥料・無農薬に関わるか: 関わる（リンの不足と充足で、病気を抑える戦略が変わる）。無肥料の区を含むかは要旨からは分からない。

#### B20. Disease Suppressive Soils: New Insights from the Soil Microbiome
- 著者・年: Schlatter D., Kinkel L., Thomashow L., Weller D., Paulitz T.（2017）
- 誌名: Phytopathology® 107(11): 1284–1297
- DOI: https://doi.org/10.1094/phyto-03-17-0111-rvw （確認日 2026-11-05）
- 図書室の id: `2017-schlatter-suppressive-soils-microbiome`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 土の病原体を抑える土は 60 年ほど前から世界で知られ、主に拮抗微生物によるとされる。特異的な抑止と一般的な抑止の二つの型がある。コムギの立枯病（take-all）、Rhizoctonia の裸地斑、Streptomyces の三つの例を出し、仮説と新しい分子の手法の可能性と限界を論じる。土着の微生物を使った持続的な病害管理に役立つ、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B21. Current Insights into the Role of Rhizosphere Bacteria in Disease Suppressive Soils
- 著者・年: Gómez Expósito R., de Bruijn I., Postma J., Raaijmakers J.M.（2017）
- 誌名: Frontiers in Microbiology 8: 2529
- DOI: https://doi.org/10.3389/fmicb.2017.02529 （確認日 2026-11-05）
- 図書室の id: `2017-gomezexposito-rhizosphere-bacteria-suppressive`（全文 XML、Europe PMC PMC5741648）
- 権利: open（CC BY、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 発病抑止土壌は、菌類・卵菌・細菌・線虫の土の病原体から植物を守る。特異的な抑止はほとんどの場合微生物による。鍵になるとされる属はいくつかあるが、微生物の相互作用と機構は多くの抑止土壌でまだ分からない。オミクスの研究の結果を、根圏の細菌に重点を置いてまとめる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B22. A Coevolutionary Framework for Managing Disease-Suppressive Soils
- 著者・年: Kinkel L.L., Bakker M.G., Schlatter D.C.（2011）
- 誌名: Annual Review of Phytopathology 49(1): 47–67
- DOI: https://doi.org/10.1146/annurev-phyto-072910-095232 （確認日 2026-11-05）
- 図書室の id: `2011-kinkel-coevolution-suppressive-soils`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 発病抑止の土の微生物群集を、共進化の枠組みで研究し管理することを論じる。拮抗的な微生物の相互作用が抑止に特に大事なので、拮抗的な共進化の理論と実証を見直し、抑止の力を生む要因の予測を立てる。土着の病原性の無い微生物どうしの種の相互作用の役割を強調する。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B23. Disease-Suppressive Soils—Beyond Food Production: a Critical Review
- 著者・年: Jayaraman S., Naorem A.K., Lal R., Dalal R.C., Sinha N.K., Patra A.K., Chaudhari S.K.（2021）
- 誌名: Journal of Soil Science and Plant Nutrition 21(2): 1437–1465
- DOI: https://doi.org/10.1007/s42729-021-00451-x （確認日 2026-11-05）
- 図書室の id: `2021-jayaraman-suppressive-soils-review`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 集約的な農業（土地利用の変化、偏った施肥、有機物の少ない投入、保全の手立ての欠如）で土の健康が落ち、農薬の使用も増えた。代わりになる手立てとして発病抑止土壌（DSS）をまとめる。抑止は宿主と病原体がいても土の病気が減ることで、主に土の多様な微生物群集による。耕起、施肥、堆肥、灌漑、資材の投入が土の物理化学的な環境を変え、拮抗微生物の生育と振る舞いに影響する。作物の齢・種類・根の振る舞いも根圏の微生物の多様性を左右する。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（偏った施肥と有機物の不足を土の劣化の原因に挙げ、施肥・耕起が拮抗微生物に影響すると書く）。

#### B24. The occurrence of pathogen suppressive soils in Sweden in relation to soil biota, soil properties, and farming practices
- 著者・年: Löbmann M.T., Vetukuri R.R., de Zinger L., Alsanius B.W., Grenville-Briggs L.J., Walter A.J.（2016）
- 誌名: Applied Soil Ecology 107: 57–65
- DOI: https://doi.org/10.1016/j.apsoil.2016.05.011 （確認日 2026-11-05）
- 図書室の id: `2016-lobmann-sweden-suppressive-soils`（書誌と要旨だけ。CC BY-NC-ND 4.0 だが全文は取れなかった）
- 権利: open（CC BY-NC-ND 4.0、Crossref）
- 種類: 一次（農場の土の室内検定）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: スウェーデン南部の 10 農場（6 つの作付け・管理）の土で、Pythium ultimum の根腐れの抑止を、そのままの土と加熱殺菌した土で比べた。6 つの土が抑止的だった。常に土が覆われている農場の土では、抑止・助長が生きた土の生物に関係した。生物的に助長する土は陽イオンの養分が高いか低く、生物的に抑止する土は中程度だった。常に土が覆われていることと、釣り合った養分の供給が、生物的な抑止と相関した。
- 前提: スウェーデン南部の 10 の農場の土。病気の検定はポットか室内（要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わる（常に土が覆われていること、養分が多すぎも少なすぎもしないことが抑止と相関）。無肥料の農場が含まれるかは要旨からは分からない。

#### B25. Induced Systemic Resistance and Plant Responses to Fungal Biocontrol Agents
- 著者・年: Shoresh M., Harman G.E., Mastouri F.（2010）
- 誌名: Annual Review of Phytopathology 48(1): 21–43
- DOI: https://doi.org/10.1146/annurev-phyto-073009-114450 （確認日 2026-11-05）
- 図書室の id: `2010-shoresh-isr-biocontrol-fungi`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 生物防除の菌類（Trichoderma、Sebacinales）は葉・根・果実の病原体や線虫を抑えるだけでなく、非生物ストレスを和らげ、養分の吸収と作物の窒素利用効率を大きく高める。これらの方が病気の防除より農業に大事かもしれない、と書く。どれも植物の遺伝子の発現の組み換えによるらしい。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（窒素利用の効率）。

#### B26. Plant immunity suppression via PHR1‐RALF‐FERONIA shapes the root microbiome to alleviate phosphate starvation
- 著者・年: Tang J., Wu D., Li X., Wang L., Xu L., Zhang Y., Xu F., Liu H. ほか（2022）
- 誌名: The EMBO Journal 41(6): EMBJ2021109102
- DOI: https://doi.org/10.15252/embj.2021109102 （確認日 2026-11-05）
- 図書室の id: `2022-tang-phr1-immunity-microbiome`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: シロイヌナズナで、リン欠乏の応答の調節因子 PHR1 が RALF 遺伝子を直接動かし、RALF が FERONIA を通じてパターン誘導免疫（PTI）の受容体の複合体の形成を抑えた。この免疫の抑制で、リン欠乏を和らげる特定の根の微生物が定着できた。
- 前提: シロイヌナズナ、室内。
- 無肥料・無農薬に関わるか: 間接に関わる（リンが足りない時、植物は免疫を下げて根の微生物を受け入れる）。

#### B27. Deciphering the Rhizosphere Microbiome for Disease-Suppressive Bacteria
- 著者・年: Mendes R., Kruijt M., de Bruijn I., Dekkers E., van der Voort M., Schneider J.H., Piceno Y.M., DeSantis T.Z. ほか（2011）
- 誌名: Science 332(6033): 1097–1100
- DOI: https://doi.org/10.1126/science.1203980 （確認日 2026-11-05）
- 図書室の id: `2011-mendes-rhizosphere-suppressive-bacteria`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 一次（圃場の土と室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 発病抑止土壌の根圏の微生物叢を PhyloChip のメタゲノム解析と培養による機能の解析で調べ、根の病原菌（要旨には「菌類の根の病原体」とだけある）の抑止に関わる細菌の分類群と遺伝子を見つけた。3 万 3 千以上の細菌・古細菌の種が検出され、プロテオバクテリア、フィルミクテス、アクチノバクテリアが一貫して抑止と結びついた。γ-プロテオバクテリアの抑止の活性は非リボソームペプチド合成酵素が担った。根の病原体に攻撃されると植物は土の微生物の集まりを守りに使える、と書く。
- 前提: 発病抑止土壌（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### B28. Root symbionts: Powerful drivers of plant above‐ and belowground indirect defenses
- 著者・年: Rasmann S., Bennett A., Biere A., Karley A., Guerrieri E.（2017）
- 誌名: Insect Science 24(6): 947–960
- DOI: https://doi.org/10.1111/1744-7917.12464 （確認日 2026-11-05）
- 図書室の id: `2017-rasmann-root-symbionts-indirect-defense`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 菌根菌、菌根でない菌類、植物生育促進根圏細菌は、養分の獲得と生育を高めるだけでなく、地上・地下の植食者への直接の防御も高める。さらに、植物が揮発性物質で捕食者・寄生者を呼ぶ間接防御にも影響する。持続的な作物保護への応用と、知識の欠けた所を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

## (C) 植食者への防御（二次代謝物、物理的防御、食害誘導性の匂いと天敵）

#### C1. Mechanisms of plant defense against insect herbivores
- 著者・年: War A.R., Paulraj M.G., Ahmad T., Buhroo A.A., Hussain B., Ignacimuthu S., Sharma H.C.（2012）
- 誌名: Plant Signaling & Behavior 7(10): 1306–1320
- DOI: https://doi.org/10.4161/psb.21663 （確認日 2026-11-05）
- 図書室の id: `2012-war-herbivore-defense`（書誌と要旨だけ）
- 権利: unknown（Crossref に license の記録が無く、PMC は確認画面で開けなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は形態・生化学・分子の仕組みで食害に応じる。防御物質は構成的にも、傷の後にも作られ、植食者の摂食・成長・生存に効く。天敵を呼ぶ揮発性物質も出す。誘導抵抗性は殺虫剤の量を減らす害虫管理の道具になりうる、エリシターの散布、遺伝子工学、軽い食害で応答する品種の育成、と要旨は言う。
- 前提: 総説。要旨からは作物と系は分からない。
- 無肥料・無農薬に関わるか: 要旨は殺虫剤を減らす話に触れるが、施肥には触れない。

#### C2. Herbivore-induced plant volatiles and tritrophic interactions across spatial scales
- 著者・年: Aartsma Y., Bianchi F.J.J.A., van der Werf W., Poelman E.H., Dicke M.（2017）
- 誌名: New Phytologist 216(4): 1054–1063
- DOI: https://doi.org/10.1111/nph.14475 （確認日 2026-11-05）
- 図書室の id: `2017-aartsma-hipv-spatial`（全文 XML、Europe PMC PMC6079636）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude snippet（要約と節の見出し）、本人 none
- 書いてあること（要約）: 食害で出る植物の匂い（HIPV）は、寄生蜂が寄主を探す手がかり。小さな空間では調べられてきたが、大きな空間ではほとんど調べられていない。匂いの空間の模様（volatile mosaic）は、匂いを出す株の並び、匂いの濃さと成分と分解、風・乱流・植生で決まる。景観の規模での理解が持続的な害虫管理に要る。節は株・区画・景観の三つの規模と応用。
- 前提: 総説。寄生蜂が中心。
- 無肥料・無農薬に関わるか: 開いた範囲では触れていない。

#### C3. The ecology of herbivore-induced silicon defences in grasses
- 著者・年: Hartley S.E., DeGabriel J.L.（2016）
- 誌名: Functional Ecology 30(8): 1311–1322
- DOI: https://doi.org/10.1111/1365-2435.12706 （確認日 2026-11-05）
- 図書室の id: `2016-hartley-silicon-grasses`（PDF、White Rose の公開版）
- 権利: open（CC BY、置き場の表紙と Crossref）
- 種類: 総説
- 読了: Claude snippet（Summary p.1311、序論の初め）、本人 none
- 書いてあること（Summary）: イネ科のケイ素の防御は、気候・土の種類・水・季節・前の食害で変わる。人の刈り取りは、唾液を伴う食害と同じようにはケイ素の防御を誘導しないようだ。誘導には食害の閾値があることが室内と野外で示された。ハタネズミでは、温室と野外で誘導の閾値と時間が量的に似ていた。草食獣の種類で効き方が違い、一般の傾向は見えにくい。
- 前提: 野生のイネ科と草食獣（昆虫、ハタネズミ、有蹄類）の生態の総説。序論で、農業ではケイ素が作物の害虫への抵抗性を高めることが古くから知られている、と書く（p.1311）。
- 無肥料・無農薬に関わるか: 開いた範囲では施肥に触れていない。「刈り取りと食害で誘導が違う」は、草を刈る畑に関わる話題だが、野生のイネ科の研究。

#### C4. Plant Silicon Defences Suppress Herbivore Performance, but Mode of Feeding Is Key
- 著者・年: Johnson S.N., Waterman J.M., Hartley S.E., Cooke J., Ryalls J.M.W., Lagisz M., Nakagawa S.（2024）
- 誌名: Ecology Letters 27(10): e14519
- DOI: https://doi.org/10.1111/ele.14519 （確認日 2026-11-05）
- 図書室の id: `2024-johnson-silicon-herbivores`（PDF、Reading 大学の公開版）
- 権利: open（CC BY 4.0、置き場の表紙と Europe PMC）
- 種類: 一次（メタ解析）
- 読了: Claude snippet（要旨と方法の一部）、本人 none
- 書いてあること（要旨）: 150 の研究のメタ解析。ケイ素の多い植物はケイ素が 52% 高く、植食者の成績は全体で 33% 下がった。吸汁性は −14%、哺乳類 −45%、咀嚼性の節足動物 −33%、穿孔性の節足動物 −39%。食性の幅の広い吸汁性と、多年生の植物の上の吸汁性はほとんど影響を受けなかった。ケイ素の多少は、補給（施用）か自然の変異による（方法の節）。
- 前提: 研究ごとに作物・野生植物・室内・野外が混ざる（研究の内訳は読んでいない）。
- 無肥料・無農薬に関わるか: ケイ素を補給した研究を含む。施肥（N・P・K）の比較ではない。

#### C5. Insect herbivore counteradaptations to the plant glucosinolate–myrosinase system
- 著者・年: Winde I., Wittstock U.（2011）
- 誌名: Phytochemistry 72(13): 1566–1575
- DOI: https://doi.org/10.1016/j.phytochem.2011.01.016 （確認日 2026-11-05）
- 図書室の id: `2011-winde-glucosinolate-counteradaptations`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アブラナ目のグルコシノレート–ミロシナーゼの系は、組織が壊れると有毒なイソチオシアネートを作る、よく調べられた化学防御。ジェネラリストとスペシャリストの植食者がアブラナ科作物に大きな被害を出す。スペシャリストは、細胞を壊さない、グルコシノレートを素早く吸収する、無害な物に変える、などでイソチオシアネートができるのを避け、自分の防御に使う物もいる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### C6. Role of trichomes in defense against herbivores: comparison of herbivore response to woolly and hairless trichome mutants in tomato (Solanum lycopersicum)
- 著者・年: Tian D., Tooker J., Peiffer M., Chung S.H., Felton G.W.（2012）
- 誌名: Planta 236(4): 1053–1066
- DOI: https://doi.org/10.1007/s00425-012-1651-9 （確認日 2026-11-05）
- 図書室の id: `2012-tian-tomato-trichome-mutants`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトの毛の少ない変異体と毛の多い（woolly）変異体で、トライコームの形と化学成分と、オオタバコガの近縁種とコロラドハムシの応答を比べた。腺毛にはモノテルペンとセスキテルペンが多かった。葉の非腺毛の高い密度はハムシの摂食と生育を下げたが、オオタバコガ近縁種の生育は促した。腺毛の高い密度は後者の生育を下げ、ハムシには効かなかった。トライコームの数はジャスモン酸メチルで増え、腺毛の防御タンパク質は食害で強く誘導された。
- 前提: トマトの変異体と野生型。室内。
- 無肥料・無農薬に関わるか: 関わらない。同じ毛が虫によって逆に効く例。

#### C7. Nonglandular silicified trichomes are essential for rice defense against chewing herbivores
- 著者・年: Andama J.B., Mujiono K., Hojo Y., Shinya T., Galis I.（2020）
- 誌名: Plant, Cell & Environment 43(9): 2019–2032
- DOI: https://doi.org/10.1111/pce.13775 （確認日 2026-11-05）
- 図書室の id: `2020-andama-rice-silicified-trichomes`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場と室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アフリカ向けの種間交雑イネ NERICA 1・4・10 は、日本の品種「日本晴」より水田で植食者（セセリ、バッタ）に多く食われた。揮発性物質の間接防御は同じか高かったが、直接の防御物質（モミラクトン A・B など）は NERICA で少なかった。日本晴の葉はケイ素の入った鋭い非腺毛に覆われていたが、NERICA にはほとんど無かった。毛を取り除くと幼虫の成績が上がり、ケイ化したトライコームがイネの噛む虫への重要な防御だ、と提案する。
- 前提: イネの品種比較、水田（場所は要旨からは分からない。日本の可能性）と室内。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。品種の違いで食害が変わる例で 10 に関わる。

#### C8. The costs of anti‐herbivore defense traits in agricultural crop plants: a case study involving leafhoppers and trichomes
- 著者・年: Kaplan I., Dively G.P., Denno R.F.（2009）
- 誌名: Ecological Applications 19(4): 864–872
- DOI: https://doi.org/10.1890/07-1566.1 （確認日 2026-11-05）
- 図書室の id: `2009-kaplan-potato-trichome-costs`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場・品種比較）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ジャガイモ 17 品種のトライコームの密度の自然な違いで、ジャガイモヒメヨコバイ（Empoasca fabae）への抵抗性と、その費用を調べた。毛の密度が高くてもヨコバイの数は減らなかったが、葉の壊死（被害）は毛の密度と負に相関した。毛の密度は収量とも食害への耐性とも相関せず、この抵抗性の費用の証拠は見つからなかった。
- 前提: ジャガイモ 17 品種（国は要旨からは分からない）。圃場か温室かは要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。収量を落とさない防御の形質がある、という点は 10 種に関わる。

#### C9. Regulation of Lignin Biosynthesis and Its Role in Growth-Defense Tradeoffs
- 著者・年: Xie M., Zhang J., Tschaplinski T.J., Tuskan G.A., Chen J.G., Muchero W.（2018）
- 誌名: Frontiers in Plant Science 9: 1427
- DOI: https://doi.org/10.3389/fpls.2018.01427 （確認日 2026-11-05）
- 図書室の id: `2018-xie-lignin-growth-defense`（全文 XML、Europe PMC PMC6172325）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 二次細胞壁の成分のうちリグニンの合成を変えると、成長と防御の両方が変わることがよく観察される。リグニンの合成経路（チロシンの近道、C-リグニン）と、階層的な転写の調節をまとめ、成長・防御・リグニン合成の間のエネルギーの配分を調整する転写の共調節の仕組みを提案する。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### C10. Silicon and plant disease resistance against pathogenic fungi
- 著者・年: Fauteux F., Rémus-Borel W., Menzies J.G., Bélanger R.R.（2005）
- 誌名: FEMS Microbiology Letters 249(1): 1–6
- DOI: https://doi.org/10.1016/j.femsle.2005.06.034 （確認日 2026-11-05）
- 図書室の id: `2005-fauteux-silicon-fungi`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ケイ素は植物の機械的・生理的な性質に良い効果を持ち、非生物・生物のストレスを和らげ、病原性の菌類への抵抗性を高める。ケイ素は防御の応答の時期と大きさを調節する、信号伝達のタンパク質に結合する、酵素の陽イオンの補因子に干渉する、などの形で、誘導抵抗性につながるストレスの信号系と関わるらしい。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C11. Silicon: Potential to Promote Direct and Indirect Effects on Plant Defense Against Arthropod Pests in Agriculture
- 著者・年: Reynolds O.L., Padula M.P., Zeng R., Gurr G.M.（2016）
- 誌名: Frontiers in Plant Science 7: 744
- DOI: https://doi.org/10.3389/fpls.2016.00744 （確認日 2026-11-05）
- 図書室の id: `2016-reynolds-silicon-arthropods`（全文 XML、Europe PMC PMC4904004）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ケイ素は植食者への抵抗性を物理的な機構と生化学的・分子的な機構の二つで与える。ケイ素を与えた植物は、虫に攻撃されると天敵をより強く引き寄せ、それが圃場の生物的防除の向上に表れた、という報告がある。可溶性のケイ素が JA の経路を通じて食害誘導性揮発性物質を増やす可能性を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C12. Tritrophic Interactions Mediated by Herbivore-Induced Plant Volatiles: Mechanisms, Ecological Relevance, and Application Potential
- 著者・年: Turlings T.C.J., Erb M.（2018）
- 誌名: Annual Review of Entomology 63(1): 433–452
- DOI: https://doi.org/10.1146/annurev-ento-020117-043507 （確認日 2026-11-05）
- 図書室の id: `2018-turlings-hipv-tritrophic`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 食害誘導性植物揮発性物質（HIPV）は、植食者に攻撃された植物に捕食者・寄生者を引き寄せる。発見から 30 年、生態的な重要さは広く認められたが、HIPV の第一の働きはまだ議論があり、作物保護への利用の可能性も同様。三者系での HIPV の役割を生態と機構の両面からまとめ、知識の欠けた所を挙げる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C13. Further Field Evaluation Of Synthetic Herbivore-Induced Plan Volatiles As Attractants For Beneficial Insects
- 著者・年: James D.G.（2005）
- 誌名: Journal of Chemical Ecology 31(3): 481–495
- DOI: https://doi.org/10.1007/s10886-005-2020-y （確認日 2026-11-05）
- 図書室の id: `2005-james-synthetic-hipv-field`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 米国ワシントン州の開けた畑とホップ園で、15 の合成 HIPV を粘着トラップに付け、天敵の誘引を試した。11 の種・科が 13 の HIPV に有意に誘引された（サリチル酸メチルにテントウムシの一種、ハナカメムシ、オオメカメムシなど。ハナアブ科、コマユバチ科など）。農業生態系に天敵を呼び込む道具としての可能性を論じる。
- 前提: 米国ワシントン州の圃場とホップ園。施肥・農薬は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C14. Herbivore‐induced plant volatiles induce an indirect defence in neighbouring plants
- 著者・年: Kost C., Heil M.（2006）
- 誌名: Journal of Ecology 94(3): 619–628
- DOI: https://doi.org/10.1111/j.1365-2745.2006.01120.x （確認日 2026-11-05）
- 図書室の id: `2006-kost-hipv-neighbour-efn`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（野外）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: リママメで、食害された蔓の揮発性物質（と、それに似せた合成の混合物）が、隣の同種の植物の花外蜜の分泌を誘導した。成分の一つ（Z）-3-ヘキセニルアセテートだけで足りた。長期の試験で、揮発性物質や花外蜜を繰り返し与えた蔓には、アリやハチなどの捕食者・寄生者が多く来て、食害が少なく、花序と葉の生産が多かった。自然の条件で、匂いが誘導する花外蜜から植物が利益を得ることを示した。
- 前提: 野生のリママメ（国は要旨からは分からない）、自然条件。
- 無肥料・無農薬に関わるか: 関わらない（野生植物）。隣の植物の匂いで防御が上がる例。

#### C15. Birds exploit herbivore‐induced plant volatiles to locate herbivorous prey
- 著者・年: Amo L., Jansen J.J., van Dam N.M., Dicke M., Visser M.E.（2013）
- 誌名: Ecology Letters 16(11): 1348–1355
- DOI: https://doi.org/10.1111/ele.12177 （確認日 2026-11-05）
- 図書室の id: `2013-amo-birds-hipv`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（野外と室内の選択試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: シジュウカラは、イモムシの付いた木と付いていない木を見分け、幼虫や食痕が見えなくても付いた木に引き寄せられた。付いた木と付いていない木は揮発性物質と見た目の両方で違った。鳥が匂いの違いで獲物の付いた木を嗅ぎ分けることを初めて示した。
- 前提: 木（樹種は要旨からは分からない）とシジュウカラ。
- 無肥料・無農薬に関わるか: 関わらない。鳥が天敵として植物の匂いを使う点で 05 に関わり得る（鳥害ではない）。

#### C16. Indirect defence via tritrophic interactions
- 著者・年: Heil M.（2008）
- 誌名: New Phytologist 178(1): 41–61
- DOI: https://doi.org/10.1111/j.1469-8137.2007.02330.x （確認日 2026-11-05）
- 図書室の id: `2008-heil-indirect-defence-tritrophic`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 多くの植物は、植食者への間接防御として肉食者と関わる。揮発性物質の放出と花外蜜の分泌は虫の摂食で誘導され、ジャスモン酸が仲立ちする。揮発性物質は主に捕食性ダニと寄生蜂を、花外蜜は主にアリを呼ぶ。食物体やダニ室（domatia）もある。環境に優しい作物保護として論じられるが、その前に適応度への効果をもっと知る必要がある、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C17. Tritrophic Interactions: Microbe-Mediated Plant Effects on Insect Herbivores
- 著者・年: Shikano I., Rosa C., Tan C.W., Felton G.W.（2017）
- 誌名: Annual Review of Phytopathology 55(1): 313–331
- DOI: https://doi.org/10.1146/annurev-phyto-080516-035319 （確認日 2026-11-05）
- 図書室の id: `2017-shikano-microbe-mediated-tritrophic`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物と虫に付く微生物は、植物と虫の関係を大きく変える。虫に付く微生物は植物の防御を抑えたり防御物質を解毒したりする。植物病原体は植物の質と防御を変えて虫の行動と適応度を操る。植物の有用微生物は生育と栄養・化学成分を変え、虫の適応度に正にも負にも働く。昆虫病原菌は内生菌として直接、あるいは虫の生理を変えて間接に防御に影響しうる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### C18. Tritrophic defenses as a central pivot of low-emission, pest-suppressive farming systems
- 著者・年: Wyckhuys K.A., Zhang W., Colmenarez Y.C., Simelton E., Sander B.O., Lu Y.（2022）
- 誌名: Current Opinion in Environmental Sustainability 58: 101208
- DOI: https://doi.org/10.1016/j.cosust.2022.101208 （確認日 2026-11-05）
- 図書室の id: `2022-wyckhuys-tritrophic-low-emission-farming`（書誌と要旨だけ。CC BY-NC-ND 4.0 だが全文は取れなかった）
- 権利: open（CC BY-NC-ND 4.0、Crossref）
- 種類: 総説（総合）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 農薬中心の作物保護は生態系の回復力を落とし人の健康を害する。生態の力を使って作物の害虫・病原体・雑草への「三者系の防御」を高める方法を、生息地による・育種による・エピジェネティックな、の三つにまとめる。種子から景観までの規模で、生態的な基盤、多様化、土の健康の回復で生物多様性を作物保護に使う。抵抗性品種、輪作、混植、プライミングを挙げる。
- 前提: 総説（Synthesis）。
- 無肥料・無農薬に関わるか: 関わる（農薬を使わない方向の総説）。無肥料の話は要旨には無い。

#### C19. Soil chemistry determines whether defensive plant secondary metabolites promote or suppress herbivore growth
- 著者・年: Hu L., Wu Z., Robert C.A.M., Ouyang X., Züst T., Mestrot A., Xu J., Erb M.（2021）
- 誌名: Proceedings of the National Academy of Sciences 118(43): e2109602118
- DOI: https://doi.org/10.1073/pnas.2109602118 （確認日 2026-11-05）
- 図書室の id: `2021-hu-benzoxazinoids-soil-iron`（全文 XML、Europe PMC PMC8639379）
- 権利: open（CC BY-NC-ND 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トウモロコシのベンゾキサジノイドは葉の防御と根の鉄の取り込み（シデロフォア）の二役を持つ。可給態の鉄がとても少ない土では、ベンゾキサジノイドはツマジロクサヨトウの生育を抑えたが、鉄の多い土では逆に生育を促した。遊離の鉄がある時、ベンゾキサジノイドが幼虫に鉄を運ぶことが原因らしい。土の化学性が、植物の防御物質の植食者への効果を決める要因だ、と示す。
- 前提: トウモロコシ、土と培地を変えた室内の試験。
- 無肥料・無農薬に関わるか: 関わる（土の化学性で同じ防御物質が逆に働く）。施肥の試験ではない。

#### C20. Defensive Function of Herbivore-Induced Plant Volatile Emissions in Nature
- 著者・年: Kessler A., Baldwin I.T.（2001）
- 誌名: Science 291(5511): 2141–2144
- DOI: https://doi.org/10.1126/science.291.5511.2141 （確認日 2026-11-05）
- 図書室の id: `2001-kessler-hipv-nature-tobacco`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 一次（野外）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 自然の群落で育つ野生タバコ（Nicotiana attenuata）の、三種の葉を食べる植食者による揮発性物質の放出を測り、よく出る 5 成分を一つずつ再現した。3 成分（シス-3-ヘキセン-1-オール、リナロール、シス-α-ベルガモテン）がジェネラリストの捕食者による卵の捕食を増やし、リナロールと全体の混合がチョウ目の産卵を減らした。揮発性物質で植食者の数を 90% 以上減らしうる。間接防御が自然の中で働くことを確かめた。
- 前提: 野生植物の自然の群落（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わらない（野生植物）。

#### C21. Fine‐tuning the ‘plant domestication‐reduced defense’ hypothesis: specialist vs generalist herbivores
- 著者・年: Gaillard M.D.P., Glauser G., Robert C.A.M., Turlings T.C.J.（2018）
- 誌名: New Phytologist 217(1): 355–366
- DOI: https://doi.org/10.1111/nph.14757 （確認日 2026-11-05）
- 図書室の id: `2018-gaillard-domestication-maize-teosinte`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ヨーロッパのトウモロコシ 6 系統と祖先のテオシント 6 集団で、3 つの食べ方の 8 種の植食性昆虫の成績を比べた。虫は一貫してトウモロコシの方でよく育ち、その差はふだんテオシントに付かないジェネラリストで大きかった。ベンゾキサジノイドは葉ではテオシントで、根ではトウモロコシで高い傾向があった。栽培化で、スペシャリストへの防御は保たれ、ジェネラリストに効く広い防御が弱まったらしい。
- 前提: トウモロコシとテオシント、室内。
- 無肥料・無農薬に関わるか: 関わらない。栽培化と防御の話で 10 種に関わる。

#### C22. Consequences of squash (Cucurbita argyrosperma) domestication for plant defence and herbivore interactions
- 著者・年: Jaccard C., Ye W., Bustos-Segura C., Glauser G., Kaplan I., Benrey B.（2023）
- 誌名: Planta 257(6): 106
- DOI: https://doi.org/10.1007/s00425-023-04139-7 （確認日 2026-11-05）
- 図書室の id: `2023-jaccard-domestication-squash`（全文 XML、Europe PMC PMC10151309）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: カボチャの一種（Cucurbita argyrosperma）の野生 3 系統と栽培 4 品種で、栽培品種は根にククルビタシンがほとんど無く、子葉にもとても少なかった。野生の根では合成の遺伝子が強く発現した。ジェネラリストとスペシャリストのハムシの幼虫はどちらも野生の根を強く好み、ジェネラリストの成績は下がったがスペシャリストは下がらなかった。栽培化は組織特異的に化学防御を抑え、共進化した植食者には魅力を下げた。
- 前提: 室内。
- 無肥料・無農薬に関わるか: 関わらない。栽培化と防御の話で 10 種に関わる。

#### C23. Crop Domestication and Its Impact on Naturally Selected Trophic Interactions
- 著者・年: Chen Y.H., Gols R., Benrey B.（2015）
- 誌名: Annual Review of Entomology 60(1): 35–58
- DOI: https://doi.org/10.1146/annurev-ento-010814-020601 （確認日 2026-11-05）
- 図書室の id: `2015-chen-domestication-trophic`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 作物の栽培化は、植物・植食者・天敵の関係を大きく変えうる。原産地で祖先の植物と同じ所に生え、同じ節足動物の群集を共有する場合の影響は、あまり分かっていない。概して栽培化は植食性昆虫への化学的な抵抗性を下げ、植食者と天敵の成績を上げてきた。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。栽培化と防御で 10 種に関わる。

#### C24. Domestication impacts on plant–herbivore interactions: a meta-analysis
- 著者・年: Whitehead S.R., Turcotte M.M., Poveda K.（2017）
- 誌名: Philosophical Transactions of the Royal Society B: Biological Sciences 372(1712): 20160034
- DOI: https://doi.org/10.1098/rstb.2016.0034 （確認日 2026-11-05）
- 図書室の id: `2017-whitehead-domestication-meta`（書誌と要旨だけ）
- 権利: quote（Royal Society の規定。PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 73 作物・89 研究の 2098 の比較の、系統を考慮したメタ解析で、作物と野生の近縁種の植食者への抵抗性と防御の形質を比べた。栽培化は一貫して植食者への抵抗性を下げたが、大きさは器官と測り方で変わった。抵抗性の元になる個々の防御の形質（二次代謝物、物理的な障壁）には一貫した効果が無く、増えることも減ることもあった。一貫した負の効果は、繁殖器官か収穫される器官で測った時だけ見られた。
- 前提: メタ解析。
- 無肥料・無農薬に関わるか: 関わらない。栽培化と防御で 10 種に関わる。

## (D) 成長と防御の取引、窒素と施肥

#### D1. Growth–Defense Tradeoffs in Plants: A Balancing Act to Optimize Fitness
- 著者・年: Huot B., Yao J., Montgomery B.L., He S.Y.（2014）
- 誌名: Molecular Plant 7(8): 1267–1287
- DOI: https://doi.org/10.1093/mp/ssu049 （確認日 2026-11-05）
- 図書室の id: `2014-huot-growth-defense`（書誌と要旨だけ）
- 権利: quote（Elsevier の open archive の user license。CC ではない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 成長と防御の取引は、資源の制約で成長か防御かに優先をつけることから生じると考えられている。分子の仕組みの多くは未解明だが、ホルモンの相互作用が調整の主役として出てきた。育種の戦略の土台になる、と要旨は結ぶ。
- 前提: 分子の総説。主にモデル植物（要旨からは確かめていない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### D2. Fertilisers and insect herbivores: a meta-analysis
- 著者・年: Butler J., Garratt M.P.D., Leather S.R.（2012）
- 誌名: Annals of Applied Biology 161(3): 223–233
- DOI: https://doi.org/10.1111/j.1744-7348.2012.00567.x （確認日 2026-11-05）
- 図書室の id: `2012-butler-fertiliser-herbivores`（書誌と要旨だけ）
- 権利: quote（Wiley の terms）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 化学肥料（N、P、K、NPK）と昆虫の個体群のメタ解析。全体で昆虫は肥料に正に応じた。吸汁性は咀嚼性よりずっと強く応じた。試験の環境で応答が大きく変わり、自然の環境では窒素肥料の効果が緩衝されうる。P と K の研究が少ない。
- 前提: 化学肥料を与えた区と与えない区（または少ない区）の比較を集めた物。作物と国は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わる（施肥の有無・量が比べる軸）。ただし有機物の施用や無肥料の畑の長期の比較かは、要旨からは分からない。

#### D3. Fertilization affects severity of disease caused by fungal plant pathogens
- 著者・年: Veresoglou S.D., Barto E.K., Menexes G., Rillig M.C.（2013、オンライン 2012）
- 誌名: Plant Pathology 62(5): 961–969
- DOI: https://doi.org/10.1111/ppa.12014 （確認日 2026-11-05）
- 図書室の id: `2013-veresoglou-fertilization-disease`（書誌と要旨だけ）
- 権利: quote（Wiley の terms）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 57 本の論文のメタ解析。主に窒素の施肥。病原菌の種類と生き方が、窒素施肥による病気の重さの変化を左右した。大多数の例で窒素施肥は病気を重くしたが、軽くなる植物種・病原菌もある（Solanum など）。鉢と圃場、人工接種と自然感染で差は無かった。
- 前提: 商業的な肥料の施用が前提の比較（要旨の書き出し）。作物は多種。
- 無肥料・無農薬に関わるか: 関わる（窒素施肥の有無・量が比べる軸）。

#### D4. Does spatial variation in insect herbivory match variations in plant quality? A meta-analysis
- 著者・年: Zvereva E.L., Castagneyrol B., Kozlov M.V.（2024）
- 誌名: Ecology Letters 27(5): e14440
- DOI: https://doi.org/10.1111/ele.14440 （確認日 2026-11-05）
- 図書室の id: `2024-zvereva-herbivory-quality`（書誌と要旨だけ。CC BY だが全文は取れなかった）
- 権利: open（CC BY 4.0、Crossref と Europe PMC）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 野外の昆虫の食害の多少と植物の性質の 223 の相関係数のメタ解析。食害は、二次代謝物の濃度とも、葉の物理的な性質とも、全体で相関しなかった。有意だったのは窒素だけで、組織の窒素が高いほど食害が多かった。防御とされる性質の情報だけでは野外の食害を予測するのに足りない、と結ぶ。
- 前提: 野外の、場所による違い（主に野生植物か作物かは要旨からは分からない）。施肥の試験ではない。
- 無肥料・無農薬に関わるか: 間接に関わる（植物の窒素と食害）。施肥を比べた研究ではない。

#### D5. Growth–defense trade-offs in plants
- 著者・年: He Z., Webster S., He S.Y.（2022）
- 誌名: Current Biology 32(12): R634-R639
- DOI: https://doi.org/10.1016/j.cub.2022.04.070 （確認日 2026-11-05）
- 図書室の id: `2022-he-growth-defense-primer`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 解説（primer）
- 読了: Claude snippet、本人 none
- 書いてあること（記録の要旨の欄＝本文の冒頭）: 記録の要旨の欄には本文の冒頭が入っていた（読んだのは冒頭の約 1200 字）。庭や畑で、害虫や病原体に傷ついた植物は近くの傷ついていない同じ植物より小さく見える。光合成の組織を失ったことのほかに、攻撃された植物が「わざと」成長を遅くし、それが傷ついた所を越えて全身に起こる、という説明がある。光合成の組織を失わずに攻撃をまねる化学物質や変異でも成長が遅くなる。
- 前提: 解説。試験ではない。
- 無肥料・無農薬に関わるか: 関わらない。攻撃された植物が小さく見える、という見た目の話で 06 に関わり得る（冒頭の一般論）。

#### D6. Rewiring of jasmonate and phytochrome B signalling uncouples plant growth-defense tradeoffs
- 著者・年: Campos M.L., Yoshida Y., Major I.T., de Oliveira Ferreira D., Weraduwage S.M., Froehlich J.E., Johnson B.F., Kramer D.M. ほか（2016）
- 誌名: Nature Communications 7(1): 12570
- DOI: https://doi.org/10.1038/ncomms12570 （確認日 2026-11-05）
- 図書室の id: `2016-campos-jaz-phyb-uncoupling`（全文 XML、Europe PMC PMC5155487）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: シロイヌナズナで、JAZ 抑制因子 5 つと光受容体 phyB を欠く変異体（jazQ phyB）では、ジャスモン酸による成長と防御の取引が切り離された。虫への抵抗性の高まりに伴う成長の抑制は、光合成産物を成長から防御へ回すためではなく、ジャスモン酸の信号が動くと成長を抑えるように組み込まれた転写の網によるらしい。
- 前提: シロイヌナズナ、室内。
- 無肥料・無農薬に関わるか: 関わらない。

#### D7. Life‐history constraints in grassland plant species: a growth‐defence trade‐off is the norm
- 著者・年: Lind E.M., Borer E., Seabloom E., Adler P., Bakker J.D., Blumenthal D.M., Crawley M., Davies K. ほか（2013）
- 誌名: Ecology Letters 16(4): 513–521
- DOI: https://doi.org/10.1111/ele.12078 （確認日 2026-11-05）
- 図書室の id: `2013-lind-grassland-growth-defence`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（世界 39 地点の野外実験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 世界 39 か所の草地で、同じ施肥（養分の制限を除く）と囲い（植食者を除く）の処理の前後に、500 種以上の 706 の植物の集団を観察した。施肥で増えた集団（養分の競争に弱い種）は、植食者を除いた時にも増えた。成長と防御の取引が普通だ、と結ぶ。4 年にわたって、生活史の型の中でも、ほとんどの地点でも成り立った。
- 前提: 世界の草地。施肥と囲いの処理。作物ではない。
- 無肥料・無農薬に関わるか: 関わる（養分を足すと増える種は、植食者を除くとも増える＝防御が弱い）。作物の畑ではない。

#### D8. Revisiting growth–defence trade‐offs and breeding strategies in crops
- 著者・年: Gao M., Hao Z., Ning Y., He Z.（2024）
- 誌名: Plant Biotechnology Journal 22(5): 1198–1205
- DOI: https://doi.org/10.1111/pbi.14258 （確認日 2026-11-05）
- 図書室の id: `2024-gao-crop-tradeoff-breeding`（全文 XML、Europe PMC PMC11022801）
- 権利: open（CC BY-NC-ND 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 免疫を動かすのは高くつき、成長と発達の罰を伴うことが多い。作物では収量が育種の主な目標で、強い病害抵抗性は収量に影響しがち。抵抗性（R）遺伝子、感受性（S）遺伝子、多面的な遺伝子による取引を和らげる最近の試みと、抵抗性と多収を両立する育種の戦略をまとめる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。育種の話で 10 に関わる。

#### D9. Sick plants in grassland communities: a growth‐defense trade‐off is the main driver of fungal pathogen abundance
- 著者・年: Cappelli S.L., Pichon N.A., Kempel A., Allan E.（2020）
- 誌名: Ecology Letters 23(9): 1349–1359
- DOI: https://doi.org/10.1111/ele.13537 （確認日 2026-11-05）
- 図書室の id: `2020-cappelli-grassland-fungal-pathogens`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（野外実験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 草地の地球環境変動と生物多様性の実験で、成長と防御の取引が菌類の病気の発生の主な決め手だった。窒素の添加は、速く育つ種へ群集を移すことで間接にだけ発生を増やした。植物の多様性は発生を減らさなかった（ジェネラリストの病原体のあふれ出しや、感受性の植物の優占が打ち消したらしい）。殺菌剤で生産量が増えた。病原体の影響は多様な群集でより強かった。
- 前提: 草地の野外実験（国は要旨からは分からない）。窒素添加と殺菌剤の処理。作物ではない。
- 無肥料・無農薬に関わるか: 関わる（窒素の添加が速く育つ・病気に弱い種を増やす）。作物の畑ではない。

#### D10. Fungal endophytes can eliminate the plant growth–defence trade‐off
- 著者・年: Bastías D.A., Gianoli E., Gundel P.E.（2021）
- 誌名: New Phytologist 230(6): 2105–2113
- DOI: https://doi.org/10.1111/nph.17335 （確認日 2026-11-05）
- 図書室の id: `2021-bastias-endophytes-eliminate-tradeoff`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 総説とメタ解析
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: イネ科の植物と内生菌 Epichloë の共生は、成長と防御の取引をなくしうる、と提案する。内生菌は成長ホルモン（ジベレリンなど）を刺激し、自分で植食者を防ぐアルカロイドを作る。公表された文献のメタ解析で、内生菌による抵抗性の高まりは成長を損なわない、という考えが支持された。
- 前提: 総説とメタ解析（Epichloë はイネ科の内生菌）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### D11. Moving nitrogen to the centre of plant defence against pathogens
- 著者・年: Mur L.A.J., Simpson C., Kumari A., Gupta A.K., Gupta K.J.（2017）
- 誌名: Annals of Botany 119(5): mcw179
- DOI: https://doi.org/10.1093/aob/mcw179 （確認日 2026-11-05）
- 図書室の id: `2017-mur-nitrogen-centre-defence`（書誌と要旨だけ）
- 権利: quote（PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 窒素肥料を与えると、宿主と病原体のどちらにも釣り合いを傾けうる。窒素を増やすと抵抗性が上がった報告も下がった報告もあり、病原体の感染の戦略の違いを映す。窒素の量だけでなく形も効く: 硝酸態は過敏感反応による抵抗性を高め、アンモニウム態は防御を損ないうる。硝酸態はスペルミンなど防御信号のポリアミンを増やし、アンモニウム態は病原体の栄養になりうる GABA を増やす。一酸化窒素の生産は硝酸態に依存し、アンモニウム態で損なわれる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わる（窒素の量と形が防御を変える）。無肥料の畑の試験ではない。

#### D12. Nitrogen forms and metabolism affect plant defence to foliar and root pathogens in tomato
- 著者・年: Ding S., Shao X., Li J., Ahammed G.J., Yao Y., Ding J., Hu Z., Yu J. ほか（2021）
- 誌名: Plant, Cell & Environment 44(5): 1596–1610
- DOI: https://doi.org/10.1111/pce.14019 （確認日 2026-11-05）
- 図書室の id: `2021-ding-tomato-nitrogen-forms`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトを 4 つの窒素の条件（硝酸態のみか硝酸態・アンモニウム態の混合、合計 1 mM と 7 mM）で育て、二つの細菌病（Pseudomonas syringae、青枯病菌 Ralstonia solanacearum）を接種した。免疫は概して低窒素と硝酸態のみの時に高かった。窒素代謝の遺伝子を抑えると感受性が下がった。窒素による防御の変化はサリチル酸の経路に依存した。
- 前提: トマト、水耕か培地で窒素の濃度と形を変えた室内の試験（要旨からは水耕か土かは分からない）。
- 無肥料・無農薬に関わるか: 関わる（低窒素で免疫が高かった）。畑の無肥料の試験ではない。

#### D13. Nitrogen Deficiency Affects Bottom-Up Cascade Without Disrupting Indirect Plant Defense
- 著者・年: Winter T.R., Rostás M.（2010）
- 誌名: Journal of Chemical Ecology 36(6): 642–651
- DOI: https://doi.org/10.1007/s10886-010-9797-z （確認日 2026-11-05）
- 図書室の id: `2010-winter-soybean-nitrogen-tritrophic`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（水耕）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 水耕のダイズで窒素欠乏の影響を見た。窒素欠乏の植物は光合成の効率、葉の窒素、可溶性タンパク質が下がり、根の量が増えた。食害誘導性の揮発性物質は同じ範囲の成分が出たが、主成分など 3 つの量が変わった。窒素欠乏の葉を食べたツマジロクサヨトウの生育と、その中で育つ寄生蜂の成績は落ちた。寄生蜂の匂いへの行動の応答は変わらなかった。窒素ストレスは三つの栄養段階に強い下からの効果を持ったが、間接防御は保たれた。
- 前提: ダイズ、水耕。
- 無肥料・無農薬に関わるか: 関わる（窒素が少ない植物では植食者の生育が落ち、匂いによる天敵の誘引は保たれた）。畑の試験ではない。

#### D14. Nitrogen enrichment differentially affects above‐ and belowground plant defense
- 著者・年: Jamieson M.A., Seastedt T.R., Bowers M.D.（2012）
- 誌名: American Journal of Botany 99(10): 1630–1637
- DOI: https://doi.org/10.3732/ajb.1100492 （確認日 2026-11-05）
- 図書室の id: `2012-jamieson-linaria-nitrogen-defense`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（温室）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 侵略的な植物 Linaria dalmatica（ウンラン属）で、大気からの窒素の沈着ほどの窒素の増加を温室で与えた。生育・繁殖・植物全体のイリドイド配糖体（防御物質）が増えた。地上と地下で配分が違い、茎葉の濃度は変わらず、花では約 35% 減り、根では 400% 以上増えた。葉だけを見ると防御の変化を見落とす、と書く。
- 前提: 侵略的な野生植物、温室、窒素の添加。
- 無肥料・無農薬に関わるか: 関わる（窒素の添加で防御物質の配分が器官で変わる）。作物ではない。

#### D15. Plant mineral nutrition and disease resistance: A significant linkage for sustainable crop protection
- 著者・年: Tripathi R., Tewari R., Singh K.P., Keswani C., Minkina T., Srivastava A.K., De Corato U., Sansinenea E.（2022）
- 誌名: Frontiers in Plant Science 13: 883970
- DOI: https://doi.org/10.3389/fpls.2022.883970 （確認日 2026-11-05）
- 図書室の id: `2022-tripathi-mineral-nutrition-disease`（全文 XML、Europe PMC PMC9631425）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 完全で釣り合った栄養は植物の防御の第一線、と書く。窒素は物理的な防御と抗菌物質の生産に負に働くが、全身の抵抗性を助ける防御酵素の水準を上げる。カリウムは適量で多価フェノールを増やす。リンには目立つ役割は見られないが、高いリンは侵入者への感受性を上げうる。マンガンは光合成とリグニン合成に、亜鉛は病原体の毒素生産などに関わる。宿主–病原体–無機元素の三者の関係はまだ解かれていない所が多い。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わる（窒素とリンの多さが防御を弱めうる、と要旨に書く）。無肥料の畑の試験ではない。

#### D16. Role of nutrients in controlling plant diseases in sustainable agriculture. A review
- 著者・年: Dordas C.（2008）
- 誌名: Agronomy for Sustainable Development 28(1): 33–46
- DOI: https://doi.org/10.1051/agro:2007051 （確認日 2026-11-05）
- 図書室の id: `2008-dordas-nutrients-disease`（書誌だけ（要旨は記録に無い））
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説（題名だけ）
- 読了: Claude none、本人 none
- 書いてあること: 記録に要旨が無い。題名は「持続的な農業で植物の病気を抑える養分の役割」。中身は読んでいない。
- 前提: 要旨からは分からない（要旨が無い）。
- 無肥料・無農薬に関わるか: 題名からは関わりそうだが、中身は読んでいない。

#### D17. Mechanisms to Mitigate the Trade-Off between Growth and Defense
- 著者・年: Karasov T.L., Chae E., Herman J.J., Bergelson J.（2017）
- 誌名: The Plant Cell 29(4): 666–680
- DOI: https://doi.org/10.1105/tpc.16.00931 （確認日 2026-11-05）
- 図書室の id: `2017-karasov-mitigate-growth-defense`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 防御には成長と繁殖の減少の費用が伴うことが多い。よく知られた取引の多くは、特定の代謝の出費ではなく、ホルモンの間の拮抗から来る。植物は抵抗性を誘導型にする、時期や組織に絞る、プライミングする（子に伝わることもある）ことで費用を和らげる。R 遺伝子の細かい調節とゲノムの配置も費用を減らす。他の種から守りを得ることもでき、植物の遺伝子型が微生物叢の組成に影響する、という新しい証拠がある。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

## (E) 混植・間作と害虫・病気（一次研究とメタ解析）

日本の県の試験（間作・混作）は F3、F4。

#### E1. Intercropping cereals with faba bean reduces plant disease incidence regardless of fertilizer input; a meta-analysis
- 著者・年: Zhang C., Dong Y., Tang L., Zheng Y., Makowski D., Yu Y., Zhang F., van der Werf W.（2019）
- 誌名: European Journal of Plant Pathology 154(4): 931–942
- DOI: https://doi.org/10.1007/s10658-019-01711-4 （確認日 2026-11-05）
- 図書室の id: `2019-zhang-intercrop-faba-disease`（書誌と要旨だけ）
- 権利: quote（Springer の TDM の license）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 穀類とソラマメの間作で、発病（オッズ比）が平均 45% 下がった。6 病原のうち 4 で有意（コムギの黄さび病とうどんこ病、ソラマメの赤色斑点病とフザリウム萎凋病）。オオムギの黄さび病は境界、ソラマメのさび病は有意でない。流行の初期に低下が最大。窒素肥料はコムギうどんこ病を強く増やしたが、他の病気には効かず、間作の効果は窒素の量に左右されなかった。完全な防除には足りない。
- 前提: 穀類／ソラマメの間作。窒素肥料の量の違う試験を含む。国は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わる（窒素の量を変えても間作の効果は変わらなかった、が結果の一つ）。ただし窒素 0 の区を含むかは要旨からは分からない。

#### E2. The effectiveness of intercropping and agri-environmental schemes on ecosystem service of biological pest control: a meta-analysis
- 著者・年: Yousefi M., Marja R., Barmettler E., Six J., Giger Dray A., Ghazoul J.（2024）
- 誌名: Agronomy for Sustainable Development 44(2): 15
- DOI: https://doi.org/10.1007/s13593-024-00947-7 （確認日 2026-11-05）
- 図書室の id: `2024-yousefi-intercrop-pest-control`（書誌と要旨だけ。CC BY だが全文は取れなかった）
- 権利: open（CC BY 4.0、Crossref）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: コムギ・トウモロコシ・ダイズで、畑の中の間作と、畑の周りの多様化（花の帯、生け垣、畦）の節足動物への効果。間作は植食者を減らし、捕食者と寄生者を有意に増やした。畑の周りの多様化は捕食者を増やしたが植食者は減らさなかった。トウモロコシとマメ科・非マメ科の間作、条間作が効いた。コムギ畑では花の帯から 5 m を越えると捕食者の増加が落ちた。
- 前提: 三つの畑作物。数えたのは節足動物の数で、作物の被害や収量ではない（要旨）。施肥・農薬の条件は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E3. The Use of Push-Pull Strategies in Integrated Pest Management
- 著者・年: Cook S.M., Khan Z.R., Pickett J.A.（2007）
- 誌名: Annual Review of Entomology 52(1): 375–400
- DOI: https://doi.org/10.1146/annurev.ento.52.110405.091407 （確認日 2026-11-05）
- 図書室の id: `2007-cook-push-pull-ipm`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: プッシュプルは、守る作物を害虫に魅力の無い・合わない物にする刺激（押す）と、害虫を魅力のある所へ誘い（引く）そこで取り除く刺激を組み合わせ、害虫と天敵の行動を操る。押す・引くの部分はふつう毒性が無いので、生物的防除などの個体数を減らす方法と組み合わせる。農薬の投入を減らす総合的害虫管理の道具。原理、部品の候補、主な分野の事例をまとめる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（農薬を減らす方法）。

#### E4. Integrated pest management: the push–pull approach for controlling insect pests and weeds of cereals, and its potential for other agricultural systems including animal husbandry
- 著者・年: Hassanali A., Herren H., Khan Z.R., Pickett J.A., Woodcock C.M.（2008）
- 誌名: Philosophical Transactions of the Royal Society B: Biological Sciences 363(1491): 611–621
- DOI: https://doi.org/10.1098/rstb.2007.2173 （確認日 2026-11-05）
- 図書室の id: `2008-hassanali-push-pull-cereals-africa`（書誌と要旨だけ）
- 権利: quote（Royal Society の規定。PMC で無料で読めるが、記録に CC の記載が無い。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アフリカの自給的な農業のために、間作（押す）とおとり作物（引く）だけで情報化学物質を届けるプッシュプルの系を作った。主な対象はトウモロコシなど穀類のチョウ目害虫。穀類の面積は減るが単位面積あたりの収量は上がった。伴作物は家畜の良い飼料になり、マメ科の間作は植物の栄養に、おとり作物の一部は保水と土の侵食の軽減に役立つ。ある間作の植物はアフリカの寄生雑草ストライガを劇的に抑えた。
- 前提: 総説（自身の研究の紹介）。東アフリカの小農の畑。
- 無肥料・無農薬に関わるか: 関わる（化学農薬に頼らず、伴作物で害虫と寄生雑草を抑える）。施肥の条件は要旨からは分からない。

#### E5. Ecological Chemistry of Pest Control in Push-Pull Intercropping Systems: What We Know, and Where to Go?
- 著者・年: Lang J., Chidawanyika F., Khan Z.R., Schuman M.C.（2022）
- 誌名: CHIMIA 76(11): 906
- DOI: https://doi.org/10.2533/chimia.2022.906 （確認日 2026-11-05）
- 図書室の id: `2022-lang-push-pull-chemistry`（PDF）
- 権利: open（CC BY 4.0、Crossref）
- 種類: 総説（系統的な文献調査）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: プッシュプルの化学生態の系統的な文献調査。3335 件から、おとり作物・間作の化学を報告する 45 件を見つけ、そのうち 30 件が穀類かアフリカの害虫。一次の化学データを報告したのは 7 件（温室・室内 5、野外の試料 2）。化合物のデータベースを作り、圃場での化合物の空間分布の仮説と、圃場で効き目に影響する要因を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。圃場で化学の機構を測った研究が少ないことを示す。

#### E6. Control of Panama Disease of Banana by Rotating and Intercropping with Chinese Chive (Allium Tuberosum Rottler): Role of Plant Volatiles
- 著者・年: Zhang H., Mallik A., Zeng R.S.（2013）
- 誌名: Journal of Chemical Ecology 39(2): 243–252
- DOI: https://doi.org/10.1007/s10886-013-0243-x （確認日 2026-11-05）
- 図書室の id: `2013-zhang-chinese-chive-banana`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 中国南部で、バナナをニラ（Allium tuberosum）と輪作・間作するとパナマ病（フザリウム萎凋病）が抑えられることが知られる。ニラの葉と根の浸出液と揮発性物質が病原菌 FOC の菌糸の生育と胞子の発芽を抑えた。2-メチル-2-ペンテナールと 4 つの有機硫黄化合物（ジメチルトリスルフィドなど）を同定し、どれも抑制した。
- 前提: 室内の試験。間作の効果そのものは中国南部の現地の経験として書かれる。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E7. Plant-Plant-Microbe Mechanisms Involved in Soil-Borne Disease Suppression on a Maize and Pepper Intercropping System
- 著者・年: Yang M., Zhang Y., Qi L., Mei X., Liao J., Ding X., Deng W., Fan L. ほか（2014）
- 誌名: PLoS ONE 9(12): e115052
- DOI: https://doi.org/10.1371/journal.pone.0115052 （確認日 2026-11-05）
- 図書室の id: `2014-yang-maize-pepper-root-wall`（全文 XML、Europe PMC PMC4281244）
- 権利: open（CC0 1.0、本文の記載）
- 種類: 一次（圃場と室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トウガラシの列の間にトウモロコシを植えた大規模な間作で、土の病気のトウガラシ疫病（Phytophthora capsici）が単作より減った。トウモロコシの根が病原の遊走子を引き寄せて生育を抑え、列を越える広がりを止める「根の壁」を作った。近くに植えると根からベンゾキサジノイド（DIMBOA、MBOA）を多く出した。
- 前提: 圃場（国は要旨からは分からない）と室内。施肥・農薬は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E8. Root Interactions in a Maize/Soybean Intercropping System Control Soybean Soil-Borne Disease, Red Crown Rot
- 著者・年: Gao X., Wu M., Xu R., Wang X., Pan R., Kim H.J., Liao H.（2014）
- 誌名: PLoS ONE 9(5): e95031
- DOI: https://doi.org/10.1371/journal.pone.0095031 （確認日 2026-11-05）
- 図書室の id: `2014-gao-maize-soybean-red-crown-rot`（全文 XML、Europe PMC PMC4014482）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（圃場 2 年と室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 2 年の圃場試験で、トウモロコシ／ダイズの間作がダイズの土の病気（Cylindrocladium parasiticum による red crown rot）を抑えた。抑制は株の間の距離が広がるほど弱まり、低リン・高リンのどちらでも見られ、根の相互作用が栄養の状態と別に効いた。根の相互作用がダイズの PR 遺伝子と酵素の活性を変えた。間作の根の滲出物にケイ皮酸が多く、病原菌を強く抑えた。
- 前提: 圃場 2 年（国は要旨からは分からない）。リン施肥の高低の 2 区。
- 無肥料・無農薬に関わるか: 関わる（低リンでも高リンでも間作の効果があった）。無施肥の区かどうかは要旨からは分からない。

#### E9. Intercropping and Pest Management: A Review of Major Concepts
- 著者・年: Smith H.A., McSorley R.（2000）
- 誌名: American Entomologist 46(3): 154–161
- DOI: https://doi.org/10.1093/ae/46.3.154 （確認日 2026-11-05）
- 図書室の id: `2000-smith-intercropping-concepts`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude snippet、本人 none
- 書いてあること（記録の要旨の欄＝本文の冒頭）: 記録の要旨の欄には本文の冒頭が入っていた。読んだ冒頭: 間作は二つ以上の作物を同じ畑で同時に育てること。列を考えない混作、交互の列、同じ列での交互がある。リレー間作は生活環が一部重なるように植える。「ポリカルチャー」は間作のほか、作物と雑草を意図して組み合わせること、被覆作物などの有益な作物でない植物との組み合わせも含む。品種の混植を含める定義もある。
- 前提: 総説。読んだのは冒頭の定義の段落だけ。
- 無肥料・無農薬に関わるか: 冒頭からは分からない。作物と雑草の意図的な組み合わせも「ポリカルチャー」に含める定義は、草を残す畑に関わる。

#### E10. Molecular Mechanisms Underlying Microbial Disease Control in Intercropping
- 著者・年: Zhu S., Morel J.B.（2019）
- 誌名: Molecular Plant-Microbe Interactions® 32(1): 20–24
- DOI: https://doi.org/10.1094/mpmi-03-18-0058-cr （確認日 2026-11-05）
- 図書室の id: `2019-zhu-intercropping-disease-mechanisms`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 間作は微生物の病気を減らすという報告が多い。圃場の規模の機構（接種源の希釈など）に加え、植物を中心とした機構がある。一つは隣の植物の誘導抵抗性。二つ目は、ある植物が地上・地下で作る分子が病原体を直接抑えるか、隣の植物の免疫を誘導する。三つ目は光や養分の競争が免疫の発現を間接に変える。非血縁・見知らぬ者の認識と競争の枠組みが役立つ、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（養分の競争が免疫を変えうる）。

#### E11. Effects of intercropping white cabbage with clovers on pest infestation and yield
- 著者・年: Theunissen J., Booij C.J.H., Lotz L.A.P.（1995）
- 誌名: Entomologia Experimentalis et Applicata 74(1): 7–16
- DOI: https://doi.org/10.1111/j.1570-7458.1995.tb01869.x （確認日 2026-11-05）
- 図書室の id: `1995-theunissen-cabbage-clover-intercrop`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場 2 年）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 生食用のキャベツ（Minicole）をシロクローバとサブクローバと間作し、単作と 2 年続けて比べた。間作で、ヨトウガ、キャベツアブラムシ、タマナバエなどの産卵と幼虫の数が抑えられた。農薬は使わず、競争でキャベツの重さは減ったが、品質が良く、単作より粗収益が良かった。
- 前提: 圃場 2 年（国は要旨からは分からない）。**農薬なし**（要旨）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わる（農薬なしでクローバの間作が害虫を抑えた）。施肥の条件は要旨からは分からない。F3 の山梨の白クローバ間作と比べられる。

#### E12. Intercropping improves faba bean photosynthesis and reduces disease caused by Fusarium commune and cinnamic acid-induced stress
- 著者・年: Yang W., Zhang Z., Yuan T., Li Y., Zhao Q., Dong Y.（2024）
- 誌名: BMC Plant Biology 24(1): 650
- DOI: https://doi.org/10.1186/s12870-024-05326-8 （確認日 2026-11-05）
- 図書室の id: `2024-yang-faba-intercrop-fusarium`（全文 XML、Europe PMC PMC11232231）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内・ポット）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 集約的な作付けで土にフェノール酸が溜まり土の病気を促す。ソラマメにフザリウム萎凋病菌（Fusarium commune）を接種しケイ皮酸を加えると、単作では葉の生育がさらに落ち病気が増えた。コムギとの間作では、養分の吸収、光合成色素、電子伝達、光合成酵素、同化産物が増え、病気が減り葉の生育が良くなった。
- 前提: ソラマメとコムギ。ポットか室内（要旨からは分からない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E13. Landscape‐level crop diversity benefits biological pest control
- 著者・年: Redlich S., Martin E.A., Steffan‐Dewenter I.（2018）
- 誌名: Journal of Applied Ecology 55(5): 2419–2428
- DOI: https://doi.org/10.1111/1365-2664.13126 （確認日 2026-11-05）
- 図書室の id: `2018-redlich-landscape-crop-diversity`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場 18 か所）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 慣行のコムギ畑 18 か所で、景観の作物の多様性と半自然の生息地の割合の二つの勾配に沿って、天敵の排除の実験（開放、鳥の排除、全排除）でアブラムシの生物的防除を測った。半自然の生息地より作物の多様性がアブラムシの抑制を高め、作物の多様性の高い景観では 8〜33% 高かった（主に 500 m 未満の規模）。鳥・寄生蜂・飛ぶ節足動物以外の天敵が防除を助けたらしい。
- 前提: 慣行のコムギ畑 18 か所（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない（慣行の畑）。鳥を排除した区がある点で 05 に関わり得る。

#### E14. Crop diversity increases disease suppressive capacity of soil microbiomes
- 著者・年: Peralta A.L., Sun Y., McDaniel M.D., Lennon J.T.（2015）
- 誌名: bioRxiv (Cold Spring Harbor Laboratory)
- DOI: https://doi.org/10.1101/030528 （確認日 2026-11-05）
- 図書室の id: `2015-peralta-crop-diversity-suppressive`（PDF）
- 権利: open（CC BY-NC-ND 4.0、Crossref）
- 種類: 一次（長期圃場試験の土。プレプリント）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 長期の圃場試験で、輪作の作物の多様性（単作から 5 種の輪作まで）と春の休閑の 8 つの処理の土を調べた。作物の多様性は細菌の群集組成を変え、被覆作物と休閑を含む最も多様な系は 1〜3 種の系と違った。最も多様な輪作（トウモロコシ・ダイズ・コムギ＋被覆作物 2）では細菌の多様性は単作のトウモロコシより約 4% 低かったが、抗菌物質を作る機能群の遺伝子（prnD）は約 9% 多かった。
- 前提: 長期の圃場試験（国は要旨からは分からない）。bioRxiv のプレプリント（査読前）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E15. USE OF MULTILINE CULTIVARS AND CULTIVAR MIXTURES FOR DISEASE MANAGEMENT
- 著者・年: Mundt C.C.（2002）
- 誌名: Annual Review of Phytopathology 40(1): 381–410
- DOI: https://doi.org/10.1146/annurev.phyto.40.011402.113723 （確認日 2026-11-05）
- 図書室の id: `2002-mundt-multiline-mixtures`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 品種の混植（多系品種と品種混合）が麦類のさび病とうどんこ病の管理に役立つことはよく示されている。役立つかは流行の条件で変わり、試験の規模の問題が大事。大きな植物の作物、宿主特異性の低い病原体、雨滴で飛ぶ・土の・虫が運ぶ病原体でも、低い・高い防除の例がある。実際の難しさは過大に見積もられがちで、持続的な農業で役割が増すだろう、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（農薬に代わる病害管理）。

#### E16. Effects of wheat cultivar mixtures on stripe rust: A meta-analysis on field trials
- 著者・年: Huang C., Sun Z., Wang H., Luo Y., Ma Z.（2012）
- 誌名: Crop Protection 33: 52–58
- DOI: https://doi.org/10.1016/j.cropro.2011.11.020 （確認日 2026-11-05）
- 図書室の id: `2012-huang-wheat-mixtures-stripe-rust-meta`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 抵抗性の違う品種の混植がコムギの黄さび病に与える効果の、11 の研究の 161 の混植のメタ解析。効果は 22.5〜33.4%、平均 28.0% の減少。効果は、混ぜる品種の病気への反応の多様さ、播種量、病気の圧力で有意に変わった。病気が強く出た時と、播種量が中程度の時に効果が大きかった。
- 前提: メタ解析。圃場試験（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E17. Pest suppression in cultivar mixtures is influenced by neighbor‐specific plant–plant communication
- 著者・年: Dahlin I., Rubene D., Glinwood R., Ninkovic V.（2018）
- 誌名: Ecological Applications 28(8): 2187–2196
- DOI: https://doi.org/10.1002/eap.1807 （確認日 2026-11-05）
- 図書室の id: `2018-dahlin-barley-mixtures-volatiles`（書誌と要旨だけ。CC BY-NC-ND 4.0 だが全文は取れなかった）
- 権利: open（CC BY-NC-ND 4.0、Crossref）
- 種類: 一次（室内と圃場）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: オオムギで、他の品種の揮発性物質に曝された株へのアブラムシの定着、単作と 2 品種の混植でのアブラムシの個体群、品種の揮発性物質の組成の違いを調べた。混植の中の品種へのアブラムシの反応は隣の品種に特異的で、それが混植全体の効果や天敵の数より害虫の抑制に大事だった。互いの匂いに曝されると両方の品種でアブラムシの受け入れが下がった組み合わせで、圃場の個体群の増え方が最も遅かった。
- 前提: オオムギ（国は要旨からは分からない）、室内と圃場。
- 無肥料・無農薬に関わるか: 要旨からは分からない。品種の組み合わせを匂いのやり取りで選ぶ、という点で 10 に関わる。

#### E18. Companion planting with French marigolds protects tomato plants from glasshouse whiteflies through the emission of airborne limonene
- 著者・年: Conboy N.J.A., McDaniel T., Ormerod A., George D., Gatehouse A.M.R., Wharton E., Donohoe P., Curtis R. ほか（2019）
- 誌名: PLOS ONE 14(3): e0213071
- DOI: https://doi.org/10.1371/journal.pone.0213071 （確認日 2026-11-05）
- 図書室の id: `2019-conboy-marigold-tomato-whitefly`（全文 XML、Europe PMC PMC6396911）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（大規模温室）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトの隣にフレンチマリーゴールドを植えると温室のオンシツコナジラミから守る、という園芸家の言い伝えを、大規模な温室の 2 試験で確かめた。生育期間を通してマリーゴールドを隣に植えると、コナジラミの増え方が有意に遅くなった。他の非寄主（バジル、ナスタチウム、ハクサイ）を混ぜても減った。コナジラミが増えてからマリーゴールドを入れても効果はわずかだった。マリーゴールドの主成分リモネンの放出器はより効いた。
- 前提: 大規模な温室（国は要旨からは分からない）。施肥・農薬は要旨からは分からない。
- 無肥料・無農薬に関わるか: 要旨からは分からない。混植は最初から、が要点。

#### E19. Companion planting – do aromatic plants disrupt host‐plant finding by the cabbage root fly and the onion fly more effectively than non‐aromatic plants?
- 著者・年: Finch S., Billiald H., Collier R.H.（2003）
- 誌名: Entomologia Experimentalis et Applicata 109(3): 183–195
- DOI: https://doi.org/10.1046/j.0013-8703.2003.00102.x （確認日 2026-11-05）
- 図書室の id: `2003-finch-companion-aromatic-flies`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場のケージ試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: アブラナ科とネギ科の寄主植物を 4 株の非寄主植物で囲み、タマネギバエとタネバエの近縁（キャベツのハエ）の寄主の発見を調べた。24 の非寄主のうち 20 がキャベツのハエの寄主発見を妨げ、最も効いたのは雑草のシロザ（産卵が対照の 18%）。「伴作物」や香りの強い植物が他の植物より妨げるわけではなかった。妨げは匂いや味ではなく緑の葉による。周りの植物の大きさが効いた。
- 前提: 圃場のケージ試験（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わる（雑草のシロザが最もよく寄主の発見を妨げた。妨げは香りではなく緑の葉による）。施肥は要旨からは分からない。

#### E20. Associational resistance through intercropping reduces yield losses to soil‐borne pests and diseases
- 著者・年: Chadfield V.G.A., Hartley S.E., Redeker K.R.（2022）
- 誌名: New Phytologist 235(6): 2393–2405
- DOI: https://doi.org/10.1111/nph.18302 （確認日 2026-11-05）
- 図書室の id: `2022-chadfield-intercrop-soilborne-meta`（全文 XML、Europe PMC PMC9545407）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 間作による連合抵抗性が、植物寄生線虫と土の病気に与える効果のメタ解析。間作で主作物の線虫の被害が 40%、発病が 55% 減った。効果は、畑の施肥の状態、間作する作物の科、試料が鉢か畑か、で変わった。線虫の防除は、間作で主作物の収量が減る分を補って余りあった。
- 前提: メタ解析。施肥の状態を説明変数に含む。
- 無肥料・無農薬に関わるか: 関わる（施肥の状態で間作の効果が変わる、と要旨にある。向きは要旨からは分からない）。

#### E21. Associational resistance in the milpa: herbivore‐induced maize volatiles enhance extrafloral nectar‐mediated defenses in common bean via shared parasitoids
- 著者・年: Grof-Tisza P., Patiño Moreno Y., Erb C., Nobel G., Clancy M.V., Benrey B.（2025）
- 誌名: New Phytologist 246(3): 1319–1332
- DOI: https://doi.org/10.1111/nph.70029 （確認日 2026-11-05）
- 図書室の id: `2025-groftisza-milpa-associational`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（制御条件）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: メソアメリカのミルパ（トウモロコシ・インゲン・カボチャの混作）で、インゲンの花外蜜を吸えた寄生蜂は長生きし、産卵が多く、隣のトウモロコシのツマジロクサヨトウの幼虫に多く寄生し、食害を減らした。イモムシに食われたトウモロコシの揮発性物質が、隣のインゲンの花外蜜の分泌をプライミングした。
- 前提: 制御条件の実験（室内・温室）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E22. Does plant diversity benefit agroecosystems? A synthetic review
- 著者・年: Letourneau D.K., Armbrecht I., Rivera B.S., Lerma J.M., Carmona E.J., Daza M.C., Escobar S., Galindo V. ほか（2011）
- 誌名: Ecological Applications 21(1): 9–21
- DOI: https://doi.org/10.1890/09-2026.1 （確認日 2026-11-05）
- 図書室の id: `2011-letourneau-plant-diversity-agroecosystems-meta`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 過去 10 年の 45 論文・552 実験のメタ解析で、植物の多様化（間作、花の咲く植物、忌避・誘引の植物）が植食者を減らし天敵を増やすかを調べた。植食者の抑制、天敵の増加、作物の被害の抑制は、多様化した作物で単一の作物より有意に強かった。ただし作物の収量の平均効果は小さいが有意に負で、主作物の密度が間作や作物でない植物に置き換わったことが一因。
- 前提: メタ解析（農業の試験）。
- 無肥料・無農薬に関わるか: 間接に関わる（農薬中心の単作に代わる方法）。施肥の条件は要旨からは分からない。

#### E23. REVIEW: Do polycultures promote win‐wins or trade‐offs in agricultural ecosystem services? A meta‐analysis
- 著者・年: Iverson A.L., Marín L.E., Ennis K.K., Gonthier D.J., Connor‐Barrie B.T., Remfert J.L., Cardinale B.J., Perfecto I. ほか（2014）
- 誌名: Journal of Applied Ecology 51(6): 1593–1602
- DOI: https://doi.org/10.1111/1365-2664.12334 （確認日 2026-11-05）
- 図書室の id: `2014-iverson-polyculture-winwin-meta`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（メタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 主作物の収量と害虫の生物的防除の両方を記録した 26 研究・301 の観察のメタ解析。種内の競争を減らす置き換えの植え方の混作では、主作物の株あたり収量と生物的防除が両立した。密植（付け足しの植え方）でマメ科を副作物にすると、生物的防除は上がり面積あたりの収量は変わらなかった。生物的防除が収量を変えたのではなく、両方が混作で別々に変わった。
- 前提: メタ解析。地域と主作物の種類をまたいで一貫した（要旨）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。マメ科を副作物にする点は無肥料の畑に関わり得る。

#### E24. Push-Pull: Chemical Ecology-Based Integrated Pest Management Technology
- 著者・年: Khan Z., Midega C.A., Hooper A., Pickett J.（2016）
- 誌名: Journal of Chemical Ecology 42(7): 689–697
- DOI: https://doi.org/10.1007/s10886-016-0730-y （確認日 2026-11-05）
- 図書室の id: `2016-khan-push-pull`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: サハラ以南アフリカの穀類を、チョウ目の茎の穿孔虫と寄生雑草ストライガが襲う。高い農薬を買えない小農のために、穿孔虫の産卵を強く引くおとり作物（引く）と雌を忌避する間作（押す）を選んだ。マメ科の忌避の間作の根の滲出物は、ストライガの種子の発芽を促す物と、宿主の根への付着を強く妨げる物を含み、「自殺発芽」させる。間作は窒素固定、自然のマルチ、侵食の防止で土の肥沃度も上げる。東アフリカの約 12 万 5 千の農家が採り入れ、トウモロコシの収量を有意に上げた。
- 前提: 総説。東アフリカの小農の畑。
- 無肥料・無農薬に関わるか: 関わる（外からの高い投入でなく、その土地の植物で害虫・雑草を抑え、マメ科で土を肥やす）。

#### E25. Genetic diversity and disease control in rice
- 著者・年: Zhu Y., Chen H., Fan J., Wang Y., Li Y., Chen J., Fan J., Yang S. ほか（2000）
- 誌名: Nature 406(6797): 718–722
- DOI: https://doi.org/10.1038/35021046 （確認日 2026-11-05）
- 図書室の id: `2000-zhu-rice-diversity-yunnan`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（大規模な圃場）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 中国雲南省で、農家・研究者・普及員が協力し、1998 年に 5 郷、1999 年に 10 郷の全ての水田に遺伝的に多様化したイネを植えた。抵抗性品種と混ぜて植えた感受性品種は、単作より収量が 89% 多く、いもち病は 94% 軽かった。2 年の計画の終わりには殺菌剤の散布はされなくなった。
- 前提: 中国雲南省の農家の水田（大規模）。施肥は要旨からは分からない。殺菌剤は計画の終わりに使われなくなった。
- 無肥料・無農薬に関わるか: 関わる（品種の混植で殺菌剤が要らなくなった）。施肥は要旨からは分からない。10 種にも関わる。

#### E26. Plant species diversity for sustainable management of crop pests and diseases in agroecosystems: a review
- 著者・年: Ratnadass A., Fernandes P., Avelino J., Habib R.（2011）
- 誌名: Agronomy for Sustainable Development 32(1): 273–303
- DOI: https://doi.org/10.1007/s13593-011-0022-4 （確認日 2026-11-05）
- 図書室の id: `2011-ratnadass-plant-species-diversity-pests`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 農薬を大きく減らしつつ病害虫を抑えるために、農業生態系に植物の多様性を保つ・入れることを柱にした農業生態学の方法を論じる。機構として、資源の希釈と刺激・忌避による逸らし、空間・時間の環の分断、アレロパシー、一般・特異的な土の抑止、作物の生理的な抵抗性、天敵の保全、構造・物理的な効果の 8 つを挙げる。植生を多様にすれば必ず病害虫が減るわけではないことも確かめ、多くの植物を代わりの寄主にできる病害虫が主な限界、と書く。
- 前提: 総説。熱帯の伝統的な低投入の系を含む。
- 無肥料・無農薬に関わるか: 関わる（農薬を減らす植物の多様性の機構と限界）。

#### E27. Agricultural diversification promotes multiple ecosystem services without compromising yield
- 著者・年: Tamburini G., Bommarco R., Wanger T.C., Kremen C., van der Heijden M.G.A., Liebman M., Hallin S.（2020）
- 誌名: Science Advances 6(45): eaba1715
- DOI: https://doi.org/10.1126/sciadv.aba1715 （確認日 2026-11-05）
- 図書室の id: `2020-tamburini-diversification-second-order-meta`（全文 XML、Europe PMC PMC7673676）
- 権利: open（CC BY-NC 4.0、本文の記載）
- 種類: 一次（二次のメタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 98 のメタ解析、5160 の元の研究、41,946 の比較の二次のメタ解析。多様化は、生物多様性、送粉、害虫の防除、養分の循環、土の肥沃度、水の調節を高め、作物の収量を損なわなかった。地上の多様性を狙う方法は害虫の防除と水の調節を、地下の多様性を狙う方法は養分の循環、土の肥沃度、水の調節を高めた。多くの場合、収量と両立した。
- 前提: 二次のメタ解析（世界）。
- 無肥料・無農薬に関わるか: 間接に関わる（投入を減らしつつ収量を保つ多様化）。

#### E28. Positive but variable effects of crop diversification on biodiversity and ecosystem services
- 著者・年: Beillouin D., Ben-Ari T., Malézieux E., Seufert V., Makowski D.（2021）
- 誌名: Global Change Biology 27(19): 4697–4710
- DOI: https://doi.org/10.1111/gcb.15747 （確認日 2026-11-05）
- 図書室の id: `2021-beillouin-crop-diversification-95-meta`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（二次のメタ解析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 95 のメタ解析、5156 の実験、85 か国・120 作物の 54,500 以上の対の観察の統合。作物の多様化は作物の生産（中央値 +14%）、付随する生物多様性（+24%）、水質（+51%）、病害虫の制御（+63%）、土の質（+11%）を高めた。戦略で大きく違い、アグロフォレストリーが特に多くの役務を与え、品種混合が最も小さく、間作・被覆作物・輪作は中間だった。
- 前提: 二次のメタ解析（世界）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### E29. Multi-country evidence that crop diversification promotes ecological intensification of agriculture
- 著者・年: Gurr G.M., Lu Z., Zheng X., Xu H., Zhu P., Chen G., Yao X., Cheng J. ほか（2016）
- 誌名: Nature Plants 2(3): 16014
- DOI: https://doi.org/10.1038/nplants.2016.14 （確認日 2026-11-05）
- 図書室の id: `2016-gurr-nectar-plants-rice`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（3 か国・4 年の圃場）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: タイ、中国、ベトナムで 4 年、水田の周りに蜜を出す植物を植え、害虫の発生、殺虫剤の使用、収量を見た。全ての場所をまとめると、この安い手立てで二つの主な害虫が有意に減り、殺虫剤の散布が 70% 減り、収量が 5% 増え、経済的な利益が 7.5% あった。蜜の植物があると、主な害虫の捕食者・寄生者と分解者が多かった。
- 前提: タイ・中国・ベトナムの水田、4 年。殺虫剤を使う系（散布回数を比べた）。施肥は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わる（周りの植物で殺虫剤を大きく減らせた）。施肥は要旨からは分からない。

## (F) 日本語の資料

#### F1. 全身誘導性植物免疫の多様な植物ホルモン類による制御機構に関する研究
- 著者・年: 仲下英雄（2023）
- 誌名: 植物の生長調節 58(2): 69–77（植物化学調節学会）
- DOI: https://doi.org/10.18978/jscrp.58.2_69 （確認日 2026-11-05）
- 図書室の id: `2023-nakashita-systemic-immunity`（J-STAGE の記事のページだけ。全文 PDF は読んだが置いていない）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説（学会賞の受賞の総説）
- 読了: Claude snippet（抄録、p.70、3 章 p.73、5 章の菌根菌の所 p.75–76）、本人 none
- 書いてあること: 全身獲得抵抗性（SAR）はサリチル酸が制御し、抵抗性誘導剤（プロベナゾールなど）でイネいもち病の防除に使われている（抄録）。プロベナゾールはサリチル酸の生合成より上流に、他の剤は下流に働く（抄録）。環境ストレスで動くアブシジン酸の信号が誘導剤の効果を抑える（抄録）。イネいもち病の研究の蓄積として「窒素やカリウム等の栄養条件が良い場合には病気に弱くなること」（p.70）。SAR の活性化は生育抑制を起こし、トマトやキュウリでは誘導剤で葉が黄化し生育が著しく遅くなる。プライミングでは PR タンパク質の蓄積が起こらず生育は影響を受けない（3 章、p.73）。アーバスキュラー菌根菌 Gigaspora margarita を定着させたトマト「桃太郎」は病原菌に抵抗性を獲得し、生育への影響は無く、定着だけでは SA・JA の信号は動かなかった（5 章、p.75–76）。
- 前提: シロイヌナズナ、タバコ、イネ、トマトの室内の研究が中心。p.70 の栄養条件の一文は、過去のイネいもち病研究の紹介で、この総説の試験ではない。
- 無肥料・無農薬に関わるか: p.70 の一文（栄養条件が良いと病気に弱い）だけが施肥に触れる。出典の論文は読んでいない。

#### F2. 植物–植食者–天敵相互作用系における植物情報化学物質の機能
- 著者・年: 塩尻かおり、前田太郎、有村源一郎、小澤理香、下田武志、高林純示（2002）
- 誌名: 日本応用動物昆虫学会誌 46(3): 117–133
- DOI: https://doi.org/10.1303/jjaez.2002.117 （確認日 2026-11-05）
- 図書室の id: `2002-shiojiri-infochemicals`（J-STAGE の記事のページだけ。全文 PDF は読んだが置いていない）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説
- 読了: Claude snippet（抄録と、野外での検証の節 p.127–128）、本人 none
- 書いてあること: 捕食者・寄生者は食害誘導性の植物揮発性物質（HIPV）を使って獲物を探す。植物–天敵、植物–植物、植物–植食者などの関係を室内と野外でまとめる（抄録）。コナガコマユバチはコナガ幼虫の食害株にだけ誘引され、アオムシコマユバチは機械的な傷の株にも誘引された（Shiojiri et al. 2000 の紹介）。ハダニアザミウマがナミハダニ食害リママメの匂いに誘引されることを、室内と柑橘園のトラップの両方で示した（Shimoda et al. 1997）。室内の天敵誘引性が野外で再現されるとは限らない、と書く（p.127–128）。
- 前提: キャベツ（アブラナ科）、リママメ、柑橘園などの研究の総説。2002 年の時点。
- 無肥料・無農薬に関わるか: 読んだ範囲では触れていない。

#### F3. 混作や間作を利用したキャベツ、ブロッコリーの有機栽培
- 著者・年: 赤池一彦（山梨県総合農業技術センター）、平成 21 年度成果情報（年は 2010 とした。発行日は見ていない）
- 誌名: 山梨県総合農業技術センター 成果情報
- URL: https://www.pref.yamanashi.jp/documents/31524/konsakukansakuyuukisaibai_1.pdf （一覧 https://www.pref.yamanashi.jp/sounou-gjt/h21seikajouhouitiran.html 、確認日 2026-11-05）
- 図書室の id: `2010-akaike-yamanashi-intercrop-organic`（PDF）
- 権利: admin（山梨県のサイトの「著作権について」: 著作権は県等にあり、私的使用の複製・引用など法で認められた場合を除き無断で転用できない。図は GitHub に写さない）
- 種類: 一次（県の試験の成果情報）
- 読了: Claude full（2 頁）、本人 none
- 書いてあること: 平坦地で春作キャベツ・秋作ブロッコリーを有機栽培する場合、畦間を白クローバや雑草で間作すると、チョウ目害虫やアブラムシの被害が減り可販株率が上がる。表 1（2008 年）: 春作キャベツの可販株率は白クローバ 66.7%、雑草 66.3%、裸地 0.0%。秋作ブロッコリーは 73.6%、61.1%、11.8%。ネギ類・レタスとの混作でさらに上がる。虫害を減らす効果は間作が混作より大きい。レタスとの混作は株ごとの交互植えが畦ごとより虫害が少ない（表 3、2009 年）。雑草の間作区に自生した草の名（ホトケノザ、ナズナ、メヒシバ、イヌビユなど）が表の注にある。
- 前提: 山梨県の平坦地、2008–2009 年、有機栽培。春作は結球初期に BT 水和剤を 1 回散布（表の注）。白クローバ・雑草は刈り込みあり。肥料の種類と量は、この 2 頁には書かれていない。
- 無肥料・無農薬に関わるか: 有機栽培（化学合成農薬なし、ただし BT 剤 1 回）。無肥料かどうかは書かれていない。

#### F4. 春まきタマネギにおける間作オオムギの播種時期がネギアザミウマ発生と収穫物に与える影響
- 著者・年: 関根崇行、大江高穂、駒形泰之（2024）
- 誌名: 北日本病害虫研究会報 75: 119–122
- DOI: https://doi.org/10.11455/kitanihon.2024.75_119 （確認日 2026-11-05）
- 図書室の id: `2024-sekine-onion-barley-thrips`（J-STAGE の記事のページだけ。全文 PDF は読んだが置いていない）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（圃場試験）
- 読了: Claude snippet（p.119–121。考察の後半は読んでいない）、本人 none
- 書いてあること: 春まきタマネギでオオムギを通路に間作し、播種を定植の当日・2 週間後・4 週間後で比べた。当日区と 2 週間後区は 4 週間後区よりネギアザミウマの寄生が有意に少なかった。1 球重と直径は 2 週間後区・4 週間後区で当日区より大きかった（表 3）。ヒラタアブ類の卵はオオムギの上にだけ見られ、幼虫・蛹は 6 月 19 日にタマネギの上で見られた（表 1）。著者らは、オオムギの播種を定植 2 週間後からネギアザミウマの初発までに、と結ぶ（抄録）。
- 前提: 宮城県農業・園芸総合研究所の露地圃場、2023 年、1 作。裸地（間作なし）の対照区は無い。**慣行の施肥と農薬の上の試験**: 施肥は地域慣行（22 kg N/10 a）、5 月 13 日にプロチオホス乳剤、6 月に無機銅水和剤を 2 回、緩衝地帯にトリフルラリン乳剤（p.120）。
- 無肥料・無農薬に関わるか: 関わらない（慣行の施肥・農薬の上で、播種の時期だけを比べた）。

#### F5. アーバスキュラー菌根菌が地上部の植食性昆虫に及ぼす影響 : 植物と昆虫の相互作用研究における地下部からの視点　(<特集2>ミクロな世界からの新展開)
- 著者・年: 西田貴明（2007）
- 誌名: 日本生態学会誌 57(3): 412–420
- DOI: https://doi.org/10.18960/seitai.57.3_412 （確認日 2026-11-05）
- 図書室の id: `2007-nishida-amf-herbivores`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 土に広くいるアーバスキュラー菌根菌（AM 菌）は根に共生して養分の供給を助け、植物の形質を介して植食性昆虫の発育や生存に正から負までいろいろな影響を与える。影響の違いは、昆虫の食べ方ごとに、AM 菌による植物の形質の変化への感受性が違うことによる。AM 菌は植物の上の昆虫の群集の構成を変えうる。土には多くの AM 菌が一緒に住み、AM 菌の種や組み合わせの違いも植物の成長や質に差を生み、昆虫の発育の違いをもたらす。「群集の形成過程」と「植物の誘導防衛」に注目して論じる（抄録）。
- 前提: 総説（日本生態学会誌の特集）。
- 無肥料・無農薬に関わるか: 要旨からは分からない。AM 菌の影響が正にも負にもなる、という点は B の他の資料と合わせて読む物。

#### F6. 天敵利用を考える：岡山県における土着天敵と天敵温存植物を用いたナスのIPM
- 著者・年: 永井一哉（2023）
- 誌名: 有機農業研究 15(2): 41–46
- DOI: https://doi.org/10.24757/joas.15.2_41 （確認日 2026-11-05）
- 図書室の id: `2023-nagai-eggplant-natural-enemies`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説（自身の研究と普及のまとめ）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 土着天敵のナミヒメハナカメムシ・タイリクヒメハナカメムシは、ナスの最も重い害虫ミナミキイロアザミウマを抑えうる。露地のナス畑を防風のソルガムで囲むと、外から飛んで来るアザミウマからナスを守り、ソルガムはワタアブラムシの土着天敵の温存植物にもなる（「露地ナス障壁栽培」、約 20 年前から実用）。周りの植生の管理が天敵の活動を高める大事な技術で、多くの草花の温存植物の候補を選んだ。施設ナスでは土着天敵タバコカスミカメと温存植物を使う IPM が県の全ての施設ナスで実施され、露地・施設とも化学農薬の使用量が大きく減った（抄録）。
- 前提: 岡山県の露地と施設のナス。IPM（化学農薬を減らした系。無農薬ではない）。施肥は抄録からは分からない。
- 無肥料・無農薬に関わるか: 関わる（周りの植物と土着天敵で化学農薬を大きく減らした）。無農薬・無肥料の系ではない。

#### F7. 施設ミニトマト有機ＪＡＳ認証圃場における主要害虫の 10 年間の年次変動に基づいた管理対策
- 著者・年: 長坂幸吉、杜建明、日本典秀、守屋成一、後藤千枝、櫻井民人、山内智史、澤田守（2020）
- 誌名: 農研機構研究報告 2020(5): 31–48
- DOI: https://doi.org/10.34503/naroj.2020.5_31 （確認日 2026-11-05）
- 図書室の id: `2020-nagasaka-organic-minitomato-pests`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（有機認証圃場の 10 年の調査）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 茨城県の有機 JAS 認証の施設ミニトマトの圃場（11〜22 a）で、2009〜2013 年と 2015〜2019 年に 2 週に 1 回、害虫の種と数を調べた。主な害虫はコナジラミ類、アブラムシ類、トマトサビダニ。コナジラミは天敵ツヤコバチ類の放飼で抑えた。ワタアブラムシはコレマンアブラバチのバンカー法（2011 年以降）で低密度に抑えた。2016 年は育苗圃から持ち込まれたアブラムシで栽培を中止したハウスがあった。トマトサビダニはミルベメクチン乳剤が有機適合資材になった 2012 年以降に抑えられた。収穫量は当初 2,000 kg/10 a 未満から 2019 年に 5,000 kg に達した（抄録）。
- 前提: 茨城県の有機 JAS 認証の施設（ハウス）、10 年。天敵の放飼と有機適合の農薬（ミルベメクチン）を使う。施肥は抄録からは分からない。
- 無肥料・無農薬に関わるか: 関わる（有機の施設での害虫管理の長期の記録）。天敵の放飼と有機適合の農薬を使う系で、無農薬ではない。

#### F8. チャの有機栽培への転換が吸汁性害虫およびその土着天敵の発生量に与える影響
- 著者・年: 松田智貴、田中千晴、菅谷耕紀（2022）
- 誌名: 茶業研究報告 2022(134): 19–30
- DOI: https://doi.org/10.5979/cha.2022.134_19 （確認日 2026-11-05）
- 図書室の id: `2022-matsuda-tea-organic-conversion`（PDF）
- 権利: open（CC BY-NC-SA 4.0、J-STAGE の記事のページの記載）
- 種類: 一次（複数の茶園の調査）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 栽培地域と履歴の違う複数の有機茶園で、チャノキイロアザミウマ、チャノミドリヒメヨコバイ、チャトゲコナジラミと、その土着天敵（アザミウマタマゴバチ、ホソハネコバチ類、徘徊性クモ類、シルベストリコバチ）を黄色粘着板で調べた。チャノキイロアザミウマとチャトゲコナジラミの捕獲数は有機転換 3 年目から全ての有機茶園で減り、その天敵の発生量は一部を除いて慣行茶園より多かった。チャノミドリヒメヨコバイには有機茶園で共通の傾向が無く、剪枝などの耕種的管理の影響を受けているかもしれない（抄録）。
- 前提: 日本の複数の有機茶園と慣行茶園（地域は抄録からは分からない）。有機の施肥・資材は抄録からは分からない。
- 無肥料・無農薬に関わるか: 関わる（有機に転換して 3 年目から一部の害虫が減り、天敵が増えた）。無肥料かは抄録からは分からない。

#### F9. 夏秋キュウリのニガウリとの混作を利用した有機栽培
- 著者・年: 赤池一彦、中村知聖、小澤明子、石川寛人（2013）
- 誌名: 有機農業研究 5(2): 5–13
- DOI: https://doi.org/10.24757/joas.5.2_5 （確認日 2026-11-05）
- 図書室の id: `2013-akaike-cucumber-bittergourd-intercrop`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（県の圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 山梨県の甲府盆地で夏秋キュウリを有機栽培する時、ニガウリと混作すると上物収量と上物率が上がった。同じ畦で 6 株ごとの交互混作で上物収量約 7%・上物率約 6%、ニガウリを畦に垂直な障壁として植えると約 10%・約 11% 高かった。畦の両端に 1 株ずつでは差が無かった。交互混作で葉の炭疽病とウリハムシの食害が減り、障壁でアブラムシの寄生が減った。ただし収量の向上は、病害虫の軽減より、混作作物が風害などからキュウリを守り傷果・曲がり果が減ったことの影響が大きい、と著者らは考える（抄録）。
- 前提: 山梨県の甲府盆地、有機栽培。施肥の種類と量は抄録からは分からない。
- 無肥料・無農薬に関わるか: 関わる（有機栽培での混作）。無肥料かは抄録からは分からない。F3 と同じ著者。

#### F10. 混作や間作による有機栽培キャベツ，ブロッコリーの虫害軽減効果
- 著者・年: 赤池一彦、小澤明子、千野正章（2011）
- 誌名: 有機農業研究 3(1): 34–43
- DOI: https://doi.org/10.24757/joas.3.1_34 （確認日 2026-11-05）
- 図書室の id: `2011-akaike-cabbage-broccoli-intercrop`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（県の圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 山梨県の甲府盆地で春作キャベツを有機栽培する時、シロクローバで間作すると、チョウ目害虫やダイコンアブラムシの被害が減り、可販株率が上がった。タマネギやレタスとの混作でさらに減った。秋作ブロッコリーでも、シロクローバの間作でハイマダラノメイガによる心葉の被害が減り、ネギやレタスとの混作でさらに減った。レタスとの混作は株ごとの交互作付けが畦ごとより可販株率が高かった（抄録）。
- 前提: 山梨県の甲府盆地、有機栽培。F3（県の成果情報）と同じ著者・同じ地域・同じ作物の論文（同じ試験かは確かめていない）。施肥は抄録からは分からない。
- 無肥料・無農薬に関わるか: 関わる（有機栽培での間作・混作）。無肥料かは抄録からは分からない。

#### F11. ストリゴラクトンによる植物免疫プライミング 生育を抑制しない病害抵抗性機構
- 著者・年: 草島美幸、藤田萌香、仲下英雄（2025）
- 誌名: 化学と生物 63(2): 60–62
- DOI: https://doi.org/10.1271/kagakutoseibutsu.63.60 （確認日 2026-11-05）
- 図書室の id: `2025-kusajima-strigolactone-priming`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 解説（今日の話題）
- 読了: Claude snippet、本人 none
- 書いてあること（PDF の冒頭）: 副題は「生育を抑制しない病害抵抗性機構」。読んだのは冒頭の一節だけ: トマトのストリゴラクトン（SL）合成の変異体は灰色かび病菌への抵抗性が下がり、イネの SL の信号・合成の変異体はいもち病抵抗性が下がり、シロイヌナズナの SL 変異体は Pseudomonas syringae pv. tomato DC3000 への抵抗性が下がる。SL の信号を抑えると様々な病原菌への抵抗性が下がる。キーワードはストリゴラクトン、病害抵抗性、プライミング、サリチル酸。
- 前提: 解説（3 頁）。PDF の冒頭だけ読んだ（PDF は置いていない）。
- 無肥料・無農薬に関わるか: 読んだ範囲では触れていない。著者に F1 の仲下英雄がいる。

#### F12. リン栄養環境に応じた植物の微生物共生制御
- 著者・年: 土田菜月、井上加奈子、西條雄介（2024）
- 誌名: 作物研究 69: 27–33
- DOI: https://doi.org/10.18964/jcr.69.0_27 （確認日 2026-11-05）
- 図書室の id: `2024-tsuchida-phosphorus-symbiosis`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 植物はリンを主に根から無機リン酸として吸い、欠乏の時にはリン酸の獲得と利用の効率を高める応答（リン枯渇応答）を誘導し、共生微生物も使ってリンを得る。共生微生物には作物の生産性・機能性を上げ、省施肥・省農薬の環境保全型農業の種としての期待がある。植物のリン枯渇への適応の戦略に焦点を当てて免疫と共生の制御を論じ、著者らが見つけたイネの根に共生する植物成長促進細菌の共生制御の研究を紹介する（抄録）。
- 前提: 総説。イネの根の共生細菌の研究の紹介を含む。
- 無肥料・無農薬に関わるか: 関わる（リンが足りない時の免疫と共生の制御。省施肥の文脈）。B26（PHR1 の論文）と同じ流れ。

#### F13. 温湯浸漬を用いた熱ショックにより誘導されるキュウリの灰色かび病抵抗性とその機作
- 著者・年: 芳野未央子、アニウィディアストゥティ、長谷川守文、佐藤達雄（2011）
- 誌名: 園芸学研究 10(3): 429–433
- DOI: https://doi.org/10.2503/hrj.10.429 （確認日 2026-11-05）
- 図書室の id: `2011-yoshino-cucumber-heat-shock`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（室内・ポット）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: キュウリの地上部を 40℃ の温湯に 2 分浸すと、灰色かび病の病斑が有意に小さかった。処理した葉でサリチル酸が増え、抵抗性に関わるペルオキシダーゼ遺伝子の発現が上がった。一部の葉だけ処理した株でも、処理していない所で発現が上がった。温湯の処理で灰色かび病抵抗性を誘導でき、その機作に全身獲得抵抗性が関わる、と考えた（抄録）。
- 前提: キュウリ、接種試験（温室か室内かは抄録からは分からない）。
- 無肥料・無農薬に関わるか: 関わる（薬剤を使わず温湯で抵抗性を誘導する）。施肥は抄録からは分からない。

#### F14. Adaptation of Green Leafhopper, Nephotettix virescens, Populations Reared on a Mixed Cropping of Two Rice Cultivars Resistant to Rice Tungro Disease
- 著者・年: Hiroshi NEMOTO、Hashim HABIBUDDIN（1995）
- 誌名: Japanese Journal of Tropical Agriculture 39(3): 190–194
- DOI: https://doi.org/10.11248/jsta1957.39.190 （確認日 2026-11-05）
- 図書室の id: `1995-nemoto-leafhopper-resistant-mixture`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（室内の飼育）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 非病原性のツマグロヨコバイの一種（Nephotettix virescens）の集団を、ツングロ病に抵抗性の 2 品種（IR42、Pankhari 203）の混作で飼育した。第 1 世代は 43 日かかったが、第 3 世代以降は約 30 日に縮み、感受性品種 TN1 で飼った集団に近づいた。適応した集団は両品種で生き、IR42 には 2 つのツングロウイルスを、Pankhari 203 には 1 つを媒介した。抵抗性品種 2 つの混作は、抵抗性を打破する集団の発達を抑えたり遅らせたりするのに有効ではない、と考えた（Abstract）。
- 前提: イネ（熱帯）、室内の飼育。
- 無肥料・無農薬に関わるか: 関わらない。品種の混植の限界を示す例で 10 に関わる。

#### F15. 水田畦畔の植生管理の違いが斑点米カメムシおよび土着天敵の個体数に及ぼす影響
- 著者・年: 稲垣栄洋、市原実、松野和夫、済木千恵子、山口翔、水元駿輔、山下雅幸、澤田均（2012）
- 誌名: 日本緑化工学会誌 38(1): 240–243
- DOI: https://doi.org/10.7211/jjsrt.38.240 （確認日 2026-11-05）
- 図書室の id: `2012-inagaki-levee-vegetation-stinkbugs`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 一次（畦畔の試験）
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 水稲の害虫の斑点米カメムシは畦畔から水田に入る。地際刈り、高刈り、除草剤、抑草剤、麦わら被覆、放任の 6 つの区で、カメムシの寄主のイネ科雑草と、土着天敵のクモ類の数を調べた。カメムシを抑え天敵の密度を高めるには、地際刈りや除草剤で裸地にするより、高刈りなどで植生を保ちながら管理するのが有効と示唆された（抄録）。
- 前提: 水田の畦畔（場所は抄録からは分からない）。
- 無肥料・無農薬に関わるか: 関わる（草を残して高く刈る管理で、天敵が増え害虫が減る方向）。

#### F16. デンジャーシグナル認識にもとづく植物の免疫制御
- 著者・年: 西條雄介、山田晃嗣（2015）
- 誌名: 日本植物病理学会報 81(4): 322–331
- DOI: https://doi.org/10.3186/jjphytopath.81.322 （確認日 2026-11-05）
- 図書室の id: `2015-saijo-danger-signal-immunity`（J-STAGE の記事のページだけ）
- 権利: quote（J-STAGE のページに CC の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（抄録）: 自然の中で植物は多くの微生物と一緒に生き、病原性の無い微生物は無視・許容するが、感染しうる微生物に出会うと誘導防御を動かす。「危険仮説」は、全ての微生物にほぼ共通の分子パターン（MAMP）に加えて、病原体の攻撃に伴う危険・傷の分子パターン（DAMP）を植物が感じて応じる、と予測する。植物免疫での DAMP の感知と信号の研究をまとめ、MAMP と DAMP の信号経路の重なった干渉が基礎抵抗性と全身獲得抵抗性に大事であることを示す著者らの研究を紹介する（抄録、英文）。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

## (G) 植物免疫（PTI・ETI、受容体）と植物間の信号

細胞表面の受容体（PRR）と細胞内の受容体（NLR）による免疫、傷の信号（DAMP）、揮発性物質と菌根網による植物の間の信号。セイタカアワダチソウの植物間の信号は G9・G13（図書室の Solidago の資料と同じ種）。

#### G1. The plant immune system
- 著者・年: Jones J.D., Dangl J.L.（2006）
- 誌名: Nature 444(7117): 323–329
- DOI: https://doi.org/10.1038/nature05286 （確認日 2026-11-05）
- 図書室の id: `2006-jones-plant-immune-system`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は二つの枝を持つ自然免疫で感染に応じる。一つは病原性の無い物を含む多くの微生物に共通の分子を認識して応じる。もう一つは病原体の病原性因子に、直接、または宿主の標的への効果を通じて応じる。免疫の詳しい理解は、食料・繊維・燃料の作物の改良の基盤になる。
- 前提: 総説（Jones & Dangl の「ジグザグ」モデルの論文）。
- 無肥料・無農薬に関わるか: 関わらない。

#### G2. Thirty years of resistance: Zig-zag through the plant immune system
- 著者・年: Ngou B.P.M., Ding P., Jones J.D.G.（2022）
- 誌名: The Plant Cell 34(5): 1447–1478
- DOI: https://doi.org/10.1093/plcell/koac041 （確認日 2026-11-05）
- 図書室の id: `2022-ngou-zig-zag-thirty-years`（全文 XML、Europe PMC PMC9048904）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は二段の検出と応答の自然免疫で病原体に抵抗する。最初の R 遺伝子は 1992 年にクローン化され、以後多くの細胞表面のパターン認識受容体（PRR）と細胞内の NLR が見つかった。特徴づけられた PRR と NLR の一覧を出し、両者の信号経路、生理的な応答、分子の調節、両者の相互作用をまとめる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G3. The plant immune system: From discovery to deployment
- 著者・年: Jones J.D.G., Staskawicz B.J., Dangl J.L.（2024）
- 誌名: Cell 187(9): 2095–2116
- DOI: https://doi.org/10.1016/j.cell.2024.03.045 （確認日 2026-11-05）
- 図書室の id: `2024-jones-immune-discovery-deployment`（書誌と要旨だけ。CC BY 4.0 だが全文は取れなかった）
- 権利: open（CC BY 4.0、Crossref）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物の病気は飢饉や人の移住を起こし、気候変動で病原体の分布が動く中で農業の持続を脅かす。100 年以上前に育種家が特定の病原体の分離株への抵抗性を与えるメンデル遺伝の座を見つけ、その後の抵抗性の育種が現代の農業を支える。細胞外と細胞内の受容体の発見をまとめ、合理的な抵抗性の強化の土台を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。育種の話で 10 に関わる。

#### G4. Beyond pathogens: microbiota interactions with the plant immune system
- 著者・年: Teixeira P.J.P., Colaianni N.R., Fitzpatrick C.R., Dangl J.L.（2019）
- 誌名: Current Opinion in Microbiology 49: 7–17
- DOI: https://doi.org/10.1016/j.mib.2019.08.003 （確認日 2026-11-05）
- 図書室の id: `2019-teixeira-microbiota-immune-system`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物の免疫が病原体を検出し抑える役割はよく調べられているが、植物に住む多くの共生的な微生物との関係はあまり分かっていない。共生的な微生物も病原体と同じく免疫を抑えたり逃れたりしうる。免疫は微生物叢の組み立てに能動的に関わり、環境の変化に応じて微生物の恒常性を保つ。免疫が微生物叢を形づくり、微生物叢が免疫を広げ、病原体に対する追加の防御の層になる、と提案する。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G5. Plant pattern-recognition receptors
- 著者・年: Zipfel C.（2014）
- 誌名: Trends in Immunology 35(7): 345–351
- DOI: https://doi.org/10.1016/j.it.2014.05.004 （確認日 2026-11-05）
- 図書室の id: `2014-zipfel-pattern-recognition-receptors`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は自然免疫だけに頼るが、ほとんどの微生物に抵抗する。微生物と害虫の危険をすばやく感じるパターン認識受容体（PRR）は、細胞表面の受容体キナーゼか受容体様タンパク質で、病原体の分子パターン（PAMP）や傷の分子パターン（DAMP）を受け取る。PRR とその相手の分子の知見をまとめる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G6. NLR receptors in plant immunity: making sense of the alphabet soup
- 著者・年: Contreras M.P., Lüdke D., Pai H., Toghani A., Kamoun S.（2023）
- 誌名: The EMBO Reports 24(10): EMBR202357495
- DOI: https://doi.org/10.15252/embr.202357495 （確認日 2026-11-05）
- 図書室の id: `2023-contreras-nlr-alphabet-soup`（全文 XML、Europe PMC PMC10561179）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 細胞内の病原体の認識は主に NLR 受容体による。NLR は病原体を感じると、ふつう過敏感反応という細胞死を伴う強く広い免疫を起こす。一つで検出と信号を兼ねる NLR もあるが、対や網で働く物もある。NLR の構造・働き・活性化、調節役の NLR、病原体による抑制、NLR の工学をまとめる。抵抗性の育種の新しい時代を開きうる、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G7. Damage-Associated Molecular Pattern-Triggered Immunity in Plants
- 著者・年: Hou S., Liu Z., Shen H., Wu D.（2019）
- 誌名: Frontiers in Plant Science 10: 646
- DOI: https://doi.org/10.3389/fpls.2019.00646 （確認日 2026-11-05）
- 図書室の id: `2019-hou-damp-triggered-immunity`（全文 XML、Europe PMC PMC6547358）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 微生物や植食者の攻撃や物理的な損傷を受けた細胞は危険の信号（傷の分子パターン、DAMP）を出す。主に細胞壁や細胞外のタンパク質の断片、ペプチド、ヌクレオチド、アミノ酸。周りの細胞の細胞膜の受容体がそれを感じ、侵入者への免疫と傷の修復を調節する。長い距離を動いて全身の傷の応答を仲立ちすることもある。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。傷そのものが防御の信号になる点は、作者の見立て（攻撃されて逞しくなる）の機構の候補。

#### G8. Volatile-mediated plant–plant communication and higher-level ecological dynamics
- 著者・年: Kessler A., Mueller M.B., Kalske A., Chautá A.（2023）
- 誌名: Current Biology 33(11): R519-R529
- DOI: https://doi.org/10.1016/j.cub.2023.04.025 （確認日 2026-11-05）
- 図書室の id: `2023-kessler-volatile-communication-dynamics`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 揮発性有機化合物、特に食害誘導性の物は、植物の組織の間の情報の伝達の主な仲立ち。放出と受け取りの機構が分かってきた。植物の間の化学的な情報の伝達は、個体の関係だけでなく、個体群・群集・生態系の動態にも効く。盗み聞きから、個体群の中で互いに利益のある情報の共有までの行動の連続体の上に植物間の関係を置く考えがある。植物の個体群は、関わる環境によって違う伝達の戦略を進化させると予測される。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G9. Insect Herbivory Selects for Volatile-Mediated Plant-Plant Communication
- 著者・年: Kalske A., Shiojiri K., Uesugi A., Sakata Y., Morrell K., Kessler A.（2019）
- 誌名: Current Biology 29(18): 3128-3133.e3
- DOI: https://doi.org/10.1016/j.cub.2019.08.011 （確認日 2026-11-05）
- 図書室の id: `2019-kalske-solidago-communication-selection`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（野外の選択実験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: セイタカアワダチソウ（Solidago altissima）で、虫の食害による自然選択を受けた集団の植物は、空気中の手がかりで全ての同種の隣の植物に抵抗性を誘導した。植食者を除いた集団の植物は、同じ遺伝子型の隣にしか誘導しなかった。情報を共有する植物は、傷つくと共通の揮発性の信号に収束した。食害が植物間の伝達の進化を駆動しうる。
- 前提: セイタカアワダチソウ、野外の選択実験（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わらない（野生植物）。作者の畑の周りのセイタカアワダチソウ（図書室の Solidago の資料）と同じ種。

#### G10. Plant–Plant Communication: Is There a Role for Volatile Damage-Associated Molecular Patterns?
- 著者・年: Meents A.K., Mithöfer A.（2020）
- 誌名: Frontiers in Plant Science 11: 583275
- DOI: https://doi.org/10.3389/fpls.2020.583275 （確認日 2026-11-05）
- 図書室の id: `2020-meents-volatile-damps-communication`（全文 XML、Europe PMC PMC7593327）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 傷の分子パターン（DAMP）は、細胞壁の成分、ペプチド、核酸の断片、細胞外 ATP などで、組織の損傷や攻撃で現れる。ある種の揮発性有機化合物も DAMP と考えられ、同じ植物の中だけでなく植物の間でも働くはず。傷で誘導される揮発性物質（DIV）の起源、性質、植物間の伝達での働きをまとめ、農薬を避けるために空気中の DAMP を自然の防御を刺激する物として使う可能性を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 間接に関わる（農薬を避けるための利用の可能性）。

#### G11. Volatile Signaling in Plant-Plant Interactions: "Talking Trees" in the Genomics Era
- 著者・年: Baldwin I.T., Halitschke R., Paschold A., von Dahl C.C., Preston C.A.（2006）
- 誌名: Science 311(5762): 812–815
- DOI: https://doi.org/10.1126/science.1118446 （確認日 2026-11-05）
- 図書室の id: `2006-baldwin-talking-trees-genomics`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は、植食者に攻撃された隣の植物が出す揮発性物質を「盗み聞き」して、攻撃される前に防御を動かしうる。揮発性物質に曝された植物の転写と信号の解析から、植物は直接・間接の防御をプライミングし、競争の力を磨くために盗み聞きするらしい。特定の揮発性物質に「耳の聞こえない」植物や「口のきけない」植物を作れるようになり、自然の群集で適応度に効くかを確かめられる、と書く。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G12. Effective distance of volatile cues for plant–plant communication in beech
- 著者・年: Hagiwara T., Ishihara M.I., Takabayashi J., Hiura T., Shiojiri K.（2021）
- 誌名: Ecology and Evolution 11(18): 12445–12452
- DOI: https://doi.org/10.1002/ece3.7990 （確認日 2026-11-05）
- 図書室の id: `2021-hagiwara-beech-communication-distance`（全文 XML、Europe PMC PMC8462143）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（植林地の野外実験 2 年）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 2 つの試験植林地のブナで、春に一本の木の葉の約 20% を半分に切り、90 日後に周りの傷つけていない木の食害を調べた。2 年とも、切った木に近いほど食害が少なかった。切った葉では（Z）-3-ヘキセニルアセテートが多かった。切った木から出る緑の葉の揮発性物質などが半径 5 m 以内の隣の木の防御を誘導した、と示す。
- 前提: ブナの試験植林地（国は要旨からは分からない）、2018・2019 年。
- 無肥料・無農薬に関わるか: 関わらない（樹木）。人の手で切った傷が周りの木の防御を上げる例。

#### G13. Plant–plant communication and community of herbivores on tall goldenrod
- 著者・年: Shiojiri K., Ishizaki S., Ando Y.（2021）
- 誌名: Ecology and Evolution 11(12): 7439–7447
- DOI: https://doi.org/10.1002/ece3.7575 （確認日 2026-11-05）
- 図書室の id: `2021-shiojiri-goldenrod-communication-genotype`（全文 XML、Europe PMC PMC8216902）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（野外と実験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: セイタカアワダチソウの 4 つの遺伝子型で、節足動物の群集は遺伝子型で違った。揮発性物質への応答は、出した植物に遺伝的に近い植物で強かった。揮発性物質の成分は遺伝子型で違った。似た節足動物が付く、遺伝的に近い植物の匂いに応じる、という仮説を支持する。
- 前提: セイタカアワダチソウ（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わらない（野生植物）。作者の畑の周りの草と同じ種。

#### G14. Plant–plant communication in Camellia japonica and C. rusticana via volatiles
- 著者・年: Sakurai Y., Ishizaki S.（2024）
- 誌名: Scientific Reports 14(1): 6284
- DOI: https://doi.org/10.1038/s41598-024-56268-y （確認日 2026-11-05）
- 図書室の id: `2024-sakurai-camellia-communication`（全文 XML、Europe PMC PMC10943193）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（自然条件の野外実験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ヤブツバキとユキツバキで、人工的に傷つけた植物の揮発性物質に、同じ株の枝や隣の株の傷のない枝を曝すと、傷のない葉の揮発性物質に曝した枝より葉の食害が減った。傷ついた枝の上の空気を傷のない枝に移すだけでも食害が減り、効果は 3 か月続いた。自然条件での植物間の伝達の観察。
- 前提: ヤブツバキ・ユキツバキ（日本）、自然条件。
- 無肥料・無農薬に関わるか: 関わらない（樹木）。

#### G15. Harnessing plant-to-plant signalling via common mycorrhizal networks for enhanced community-level resistance in crops
- 著者・年: Lee S.J., Wang L., Orlovskis Z.（2026）
- 誌名: Journal of Experimental Botany 77(15): 4812–4828
- DOI: https://doi.org/10.1093/jxb/erag159 （確認日 2026-11-05）
- 図書室の id: `2026-lee-cmn-community-resistance`（全文 XML、Europe PMC PMC13462799）
- 権利: open（CC BY-NC 4.0、本文の記載）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物間の信号は、揮発性物質や滲出物のほか、寄生植物や菌根菌が作る共通菌根網（CMN）を通っても伝わる。CMN を通る信号の分子の機構（小さな RNA の移動などの候補）と、病原体への防御での意味をまとめる。作物を互いにつながった植物の系として考える枠組みの大事さを強調し、CMN で危険の信号を伝える持続的な農業生態系の設計の課題を論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 要旨からは分からない。

#### G16. Plant Communication
- 著者・年: Karban R.（2021）
- 誌名: Annual Review of Ecology, Evolution, and Systematics 52(1): 1–24
- DOI: https://doi.org/10.1146/annurev-ecolsys-010421-020045 （確認日 2026-11-05）
- 図書室の id: `2021-karban-plant-communication-karban`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 植物は光、水、養分、接触、植食者、病原体、菌根、窒素固定菌の情報を感じ、他の植物、有用微生物、植食者、その敵、送粉者、種子散布者が感じる手がかりを出す。光の手がかりへの応答は適応度を上げたが、植食者や病原体の手がかりへの応答の利益の証拠は限られる。出す側の利益、特に植物どうしの伝達は、さらにはっきりしない。植物は過去の手がかりを覚え、非生物ストレスの危険を日陰より、日陰を食べられることより重く扱う。自他と血縁を区別できる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。植食者の手がかりへの応答の利益の証拠が限られる、という慎重な書き方は合わせて読む物。

#### G17. Explaining evolution of plant communication by airborne signals
- 著者・年: Heil M., Karban R.（2010）
- 誌名: Trends in Ecology & Evolution 25(3): 137–144
- DOI: https://doi.org/10.1016/j.tree.2009.09.010 （確認日 2026-11-05）
- 図書室の id: `2010-heil-airborne-signals-evolution`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説（意見）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 隣の植物からの揮発性物質による抵抗性の発現は今ではよく示されている。空気の信号はふつう受け手の抵抗性を上げるが、出し手に明らかな利益が無く、進化の説明が難しい。直接の防御、植物の中の信号、他の防御との相乗、血縁の間の手がかり、の 4 つの説明を論じる。出し手・受け手の適応度への影響の知識が欠けている。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わらない。

#### G18. Underground signals carried through common mycelial networks warn neighbouring plants of aphid attack
- 著者・年: Babikova Z., Gilbert L., Bruce T.J., Birkett M., Caulfield J.C., Woodcock C., Pickett J.A., Johnson D.（2013）
- 誌名: Ecology Letters 16(7): 835–843
- DOI: https://doi.org/10.1111/ele.12115 （確認日 2026-11-05）
- 図書室の id: `2013-babikova-cmn-aphid-warning`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ソラマメで、アブラムシの食害がサリチル酸メチルなどの揮発性物質を全身で変え、アブラムシを遠ざけ寄生蜂を引き寄せる。アブラムシのいない植物でも、アブラムシの付いた植物と共通の菌根の菌糸網でつながっている時だけ同じ効果が出た。地下の菌根網が食害の早期警報の系として働く。
- 前提: ソラマメ、室内（菌根網の有無を操作）。
- 無肥料・無農薬に関わるか: 関わらない。

#### G19. Interplant Communication of Tomato Plants through Underground Common Mycorrhizal Networks
- 著者・年: Song Y.Y., Zeng R.S., Xu J.F., Li J., Shen X., Yihdego W.G.（2010）
- 誌名: PLoS ONE 5(10): e13324
- DOI: https://doi.org/10.1371/journal.pone.0013324 （確認日 2026-11-05）
- 図書室の id: `2010-song-tomato-cmn-communication`（全文 XML、Europe PMC PMC2954164）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内・ポット）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: トマトの間に菌根菌 Glomus mosseae で共通菌根網を作った後、「与え手」の株に夏疫病菌（Alternaria solani）を接種すると、健康な隣の「受け手」の株の病害抵抗性と、ペルオキシダーゼ、キチナーゼなどの防御酵素の活性が上がり、6 つの防御の遺伝子が動いた。菌根網が地下の植物間の伝達の道として、病気への抵抗性と防御の信号を伝えうる。
- 前提: トマト、ポット（国は要旨からは分からない）。
- 無肥料・無農薬に関わるか: 関わらない。

## (H) 低投入・有機・不耕起の系での防御

有機・自然農法・保全農業（不耕起）の系と慣行の系で、病害虫・天敵・防御物質・土の病気の抑止を比べた資料。**無肥料・無農薬の畑で防御を比べた資料は、ここにも無い**（各項の前提を見ること）。

#### H1. Plant disease management in organic farming systems
- 著者・年: van Bruggen A.H., Gamliel A., Finckh M.R.（2016）
- 誌名: Pest Management Science 72(1): 30–44
- DOI: https://doi.org/10.1002/ps.4145 （確認日 2026-11-05）
- 図書室の id: `2016-vanbruggen-organic-disease-management`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 総説
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 有機農業の病害管理は、窒素固定作物や被覆作物を含む釣り合った輪作、間作、厩肥と堆肥の投入、耕起の削減による、生物多様性と土の健康の維持が基本。土の病気の多くは自然に抑えられるが、葉の病気が問題になることがある。厳しい流行が予想される時だけ、有機で認められた農薬を使う。耕種的・生物的防除を詳しくまとめ、熱帯の有機農業の残る問題などを論じる。
- 前提: 総説。
- 無肥料・無農薬に関わるか: 関わる（有機の系の病害管理。無肥料ではなく厩肥・堆肥を入れる系）。

#### H2. Organic farming at local and landscape scales fosters biological pest control in vineyards
- 著者・年: Muneret L., Auriol A., Thiéry D., Rusch A.（2019）
- 誌名: Ecological Applications 29(1): e01818
- DOI: https://doi.org/10.1002/eap.1818 （確認日 2026-11-05）
- 図書室の id: `2019-muneret-organic-vineyards-biocontrol`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（42 のブドウ園）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: フランス南西部の 42 のブドウ園で、有機農業と半自然の生息地の、畑と景観の規模での効果を、雑草と虫の 3 つの害虫の生物的防除で調べた。畑と景観の両方の有機農業が防除の平均と時間の安定を高め、景観の半自然の生息地の割合は防除の力を下げた。ガの卵の除去は有機の畑で高く、雑草の種子の除去は景観の有機の割合とともに上がった。農薬の使用は防除の力を下げる傾向があった。
- 前提: フランス南西部のブドウ園 42、有機と慣行。
- 無肥料・無農薬に関わるか: 関わる（有機の畑で生物的防除が高く安定。農薬の使用は防除を下げる傾向）。施肥は要旨からは分からない。

#### H3. Deployment of organic farming at a landscape scale maintains low pest infestation and high crop productivity levels in vineyards
- 著者・年: Muneret L., Thiéry D., Joubard B., Rusch A.（2018）
- 誌名: Journal of Applied Ecology 55(3): 1516–1525
- DOI: https://doi.org/10.1111/1365-2664.13034 （確認日 2026-11-05）
- 図書室の id: `2018-muneret-organic-vineyards-landscape`（書誌と要旨だけ）
- 権利: quote（Wiley の利用規約・TDM の license。CC の記載は見ていない）
- 種類: 一次（42 のブドウ園）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 42 のブドウ園で、二つの病原体と五つの節足動物の害虫の発生、農薬の使用の強さ、生産性を量った。畑の規模では、病害虫の群集は有機と慣行で違わなかった。景観の有機の面積が増えても害虫の発生は増えなかった。有機のブドウ園は処理の強さがずっと低く、害虫の防除の程度と生産性は同じだった。
- 前提: フランスのブドウ園 42、有機と慣行。
- 無肥料・無農薬に関わるか: 関わる（有機でも病害虫は増えず、生産性も同じ）。有機の農薬（硫黄・銅など）を使う系で、無農薬ではない。

#### H4. Organic Farming and Cover-Crop Management Reduce Pest Predation in Austrian Vineyards
- 著者・年: Reiff J.M., Kolb S., Entling M.H., Herndl T., Möth S., Walzer A., Kropf M., Hoffmann C. ほか（2021）
- 誌名: Insects 12(3): 220
- DOI: https://doi.org/10.3390/insects12030220 （確認日 2026-11-05）
- 図書室の id: `2021-reiff-organic-vineyards-austria`（全文 XML、Europe PMC PMC7999927）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（ブドウ園）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: オーストリアのブドウ園で、有機と総合管理、畝間の被覆作物の多様さ、景観で、ブドウの害虫（ホソハマキの一種 Lobesia botrana）の卵と蛹の捕食を比べた。蛹の捕食は有機と種の少ない被覆作物で約 10% 低かった。卵の捕食は差が無かった。有機の負の効果は、頻繁な硫黄と銅の散布の非標的の影響らしい。環境に優しい農業の効き目は作物と地域ごとに確かめる必要がある、と書く。
- 前提: オーストリアのブドウ園、有機（硫黄・銅を頻繁に散布）と総合管理。
- 無肥料・無農薬に関わるか: 関わる（有機でも硫黄・銅の散布が天敵を減らしうる、という例）。無農薬ではない。

#### H5. Organic Farming Practices and Shade Trees Reduce Pest Infestations in Robusta Coffee Systems in Amazonia
- 著者・年: Piato K., Subía C., Pico J., Calderón D., Norgrove L., Lefort F.（2021）
- 誌名: Life 11(5): 413
- DOI: https://doi.org/10.3390/life11050413 （確認日 2026-11-05）
- 図書室の id: `2021-piato-coffee-organic-shade`（全文 XML、Europe PMC PMC8147205）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（圃場、分割区）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: エクアドルのアマゾンの 3 年生のロブスタコーヒーで、日向と 4 種の日陰樹、慣行（中程度・集約の投入）と有機（低・集約の投入）を分割区で比べた。集約の有機では集約の慣行より、コーヒーノミキクイムシと小枝の甲虫の被害が 7% 低かった。小枝の甲虫は日向で Inga edulis の日陰より多かった。投入の集約化が害虫を増やし収量を失わせうることを初めて示した、と書く。
- 前提: エクアドルのアマゾン、ロブスタコーヒー、日陰樹と施肥（有機・無機）の試験。
- 無肥料・無農薬に関わるか: 関わる（無機の集約的な投入で害虫が多い）。無肥料の区は無い（要旨）。

#### H6. Organic farming induces changes in bacterial community and disease suppressiveness against fungal phytopathogens
- 著者・年: Khatri S., Dubey S., Shivay Y.S., Sharma S., Jelsbak L.（2023）
- 誌名: Applied Soil Ecology 181: 104658
- DOI: https://doi.org/10.1016/j.apsoil.2022.104658 （確認日 2026-11-05）
- 図書室の id: `2023-khatri-organic-suppressiveness-microbiome`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（18 年の長期圃場と鉢の検定）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 18 年間の有機と慣行の長期圃場試験の土で、有機の畑には生物防除に関わる属が多く、細菌の多様性が有意に高かった。有機の畑の微生物叢を与えた植物は、Rhizoctonia solani とフザリウムによる病気が慣行より軽かった。Flavobacterium、Bacillus、Pseudomonas などが抑止に関わる候補。
- 前提: 長期圃場試験（国は要旨からは分からない）、有機と慣行。病気の検定は植物で。
- 無肥料・無農薬に関わるか: 関わる（有機の土が病気を抑える力が高い）。無肥料ではない。

#### H7. Plant disease severity in high-input compared to reduced-input and organic farming systems
- 著者・年: Van Bruggen A.H.C.（1995）
- 誌名: Plant disease 79(10): 976–984
- DOI: https://doi.org/ （確認日 2026-11-05）
- 図書室の id: `1995-vanbruggen-high-input-organic-disease`（書誌だけ（要旨は記録に無い））
- 権利: unknown（license の記載を見つけなかった）
- 種類: 一次（題名だけ）
- 読了: Claude none、本人 none
- 書いてあること: 記録に要旨が無い。題名は「高投入の系と、低投入・有機の系での植物の病気の重さの比較」。中身は読んでいない。
- 前提: 要旨からは分からない（要旨が無い）。
- 無肥料・無農薬に関わるか: 題名からは関わりそうだが、中身は読んでいない。

#### H8. Impact of Long-Term Cover Cropped Organic Farming Practices on the Development of Disease Suppressive Soils
- 著者・年: Ghile N.T., Bardhan S., Eivazi F., Lin C.（2025）
- 誌名: bioRxiv (Cold Spring Harbor Laboratory)
- DOI: https://doi.org/10.1101/2025.07.28.667314 （確認日 2026-11-05）
- 図書室の id: `2025-ghile-cover-crop-organic-suppressive`（書誌と要旨だけ。CC BY-NC-ND 4.0 だが全文は取れなかった）
- 権利: open（CC BY-NC-ND 4.0、Crossref）
- 種類: 一次（長期圃場の土の代謝物。プレプリント）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 長期の有機認証の畑で被覆作物の刈り方（フレイル、ロータリー）を変えた区と慣行の区の根圏の土の化学成分を、非標的のメタボロミクスで比べた。2500 以上の化合物が見つかり、長期の被覆作物は土の化学的な環境を大きく変え、生理活性のある化学物質が多く多様だった。それが発病抑止土壌の形成を支える、と書く。
- 前提: 長期の有機の畑（国は要旨からは分からない）。bioRxiv のプレプリント（査読前）。病気そのものは測っていない（要旨）。
- 無肥料・無農薬に関わるか: 関わる（長期の有機・被覆作物の土）。無肥料かは要旨からは分からない。

#### H9. Diversity and No-Till: Keys for Pest Management in the U.S. Great Plains
- 著者・年: Anderson R.L.（2008）
- 誌名: Weed Science 56(1): 141–145
- DOI: https://doi.org/10.1614/ws-07-007.1 （確認日 2026-11-05）
- 図書室の id: `2008-anderson-no-till-diversity-great-plains`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 総説（現地の経験と試験のまとめ）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 米国グレートプレーンズで、冬コムギと休閑の輪作から、暖季作物を入れた多様な輪作と不耕起に変わった。寒季作物 2 つと暖季作物 2 つを続ける 4 年輪作と不耕起で、雑草の管理の費用が半分になり、病気の重さも小さくなって収量の見込みが上がり、純収益が上がった。
- 前提: 米国グレートプレーンズの乾燥地の畑作。除草剤の使用は要旨からは分からない。
- 無肥料・無農薬に関わるか: 間接に関わる（輪作と不耕起で雑草と病気を減らす）。

#### H10. Conservation agriculture cropping systems reduce blast disease in upland rice by affecting plant nitrogen nutrition
- 著者・年: Dusserre J., Raveloson H., Michellon R., Gozé E., Auzoux S., Sester M.（2017）
- 誌名: Field Crops Research 204: 208–221
- DOI: https://doi.org/10.1016/j.fcr.2017.01.024 （確認日 2026-11-05）
- 図書室の id: `2017-dusserre-conservation-agriculture-blast`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（圃場 3 作期・2 か所）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: マダガスカル中央高地で、保全農業（不耕起と被覆）の陸稲は慣行の耕起よりいもち病が軽いことが知られていた。2 か所・3 作期で、無機窒素の施肥ありと無し、保全農業と耕起、いもち病への感受性の違う 2 品種を組み合わせた。いもち病が多い時、保全農業と窒素無施肥で病気が軽かった。初期の葉の窒素は耕起の方が高く、葉面積指数は保全農業の方が低かった。葉の窒素と葉面積指数が、作付け体系と施肥の効果を説明した（覆い隠した）。収量は保全農業で高くないか低かった。
- 前提: マダガスカル中央高地（高地・中標高）の陸稲、3 作期。**窒素無施肥の区がある**。農薬は要旨からは分からない。
- 無肥料・無農薬に関わるか: 関わる（窒素無施肥でいもち病が軽く、それは葉の窒素と茂り方で説明された）。収量は保全農業で同じか低かった点も合わせて読む物。

#### H11. Natural farming improves crop yield in SE India when compared to conventional or organic systems by enhancing soil quality
- 著者・年: Duddigan S., Shaw L.J., Sizmur T., Gogu D., Hussain Z., Jirra K., Kaliki H., Sanka R. ほか（2023）
- 誌名: Agronomy for Sustainable Development 43(2): 31
- DOI: https://doi.org/10.1007/s13593-023-00884-x （確認日 2026-11-05）
- 図書室の id: `2023-duddigan-zbnf-yield-india`（全文 XML、Europe PMC PMC10035491）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（28 農場の圃場試験）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: インドのアーンドラ・プラデーシュ州の 6 県・28 農場で 3 作期、ゼロ予算自然農法（ZBNF: 合成農薬・肥料なし、自家製の在来牛の糞と尿の資材とマルチ）を、慣行（合成肥料・農薬）と有機（合成なし、マルチなし、購入した厩肥・ミミズ堆肥）と比べた。どれも不耕起。全体では ZBNF の収量が有意に高かったが、県と作物で違った。ZBNF の利益はマルチによる涼しく湿った土とミミズの多さによるらしい。大部分の養分は ZBNF と慣行で差が無かった。
- 前提: インド南東部の 28 農場、3 作期。全区不耕起。ZBNF は合成の肥料・農薬なし（牛糞・牛尿の資材あり）。害虫・病気は測っていない（要旨）。
- 無肥料・無農薬に関わるか: 関わる（合成の肥料・農薬を使わない系と慣行の比較）。ただし防御・病害虫の比較ではなく収量と土。

#### H12. India’s agroecology programme, ‘Zero Budget Natural Farming’, delivers biodiversity and economic benefits without lowering yields
- 著者・年: Berger I., Kamble A., Morton O., Raj V., Nair S.R., Edwards D.P., Wauchope H.S., Joshi V. ほか（2025）
- 誌名: Nature Ecology & Evolution 9(11): 2057–2068
- DOI: https://doi.org/10.1038/s41559-025-02849-7 （確認日 2026-11-05）
- 図書室の id: `2025-berger-zbnf-biodiversity`（全文 XML、Europe PMC PMC12592218）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（大規模な評価）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: インドの 64,000 km² の政府が後押しする ZBNF の計画で、社会経済と生物多様性を一緒に分析した。ZBNF は農家の利益を 2 倍以上にし、収量は同じだった。害虫の防除や種子の散布に関わる鳥の種と機能群の密度が増えた。森林に特化した種には自然林が欠かせない。鳥の密度と収量・利益の取引は、ZBNF の方が慣行よりずっと小さかった。
- 前提: インドの ZBNF の地域（州は要旨からは分からない）、慣行と比較。
- 無肥料・無農薬に関わるか: 関わる（農薬・化学肥料に頼らない系で、害虫を食べる鳥が増えた）。05 鳥獣害に、鳥を害ではなく天敵として見る資料として関わる。

#### H13. Microbial Diversity in the Phyllosphere and Rhizosphere of an Apple Orchard Managed under Prolonged “Natural Farming” Practices
- 著者・年: He Y.H., Adkar-Purushothama C.R., Ito T., Shirakawa A., Yamamoto H., Kashiwagi A., Tatewaki A., Fujibayashi M. ほか（2021）
- 誌名: Microorganisms 9(10): 2056
- DOI: https://doi.org/10.3390/microorganisms9102056 （確認日 2026-11-05）
- 図書室の id: `2021-he-natural-farming-apple`（全文 XML、Europe PMC PMC8540600）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（果樹園の微生物の比較）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 30 年以上「自然農法」で育てたリンゴ園の微生物の多様性を慣行の園と比べた。主なリンゴの病気は、長期の自然農法の園では慣行の園より重かったが、短期の自然農法の園よりは軽かった。葉の菌類では Cladosporium tenuissimum が優占し、Aureobasidium pullulans などは少なかった。多様性そのものより、適した優占種の下で釣り合った菌の組み合わせが保たれることが大事らしい。葉の細菌では、防御を誘導しうる Pseudomonas graminis が 8 月に優占した。根圏では、虫や線虫に感染する菌の属（Cordyceps、Arthrobotrys）が長期の自然農法の園だけで見つかった。
- 前提: 30 年以上の自然農法のリンゴ園（場所は要旨には書かれていない）、慣行の園、短期の自然農法の園。
- 無肥料・無農薬に関わるか: 関わる（無肥料・無農薬の自然農法の果樹園の病気と微生物。**病気は慣行より重かった**）。

#### H14. Korean Natural Farming practices are dominated by a limited number of microbes and decrease fungal diversity
- 著者・年: Thompson C., Mozeika S., Paredes E., Lee U.（2026）
- 誌名: Sustainable Microbiology 3(3): qvag033
- DOI: https://doi.org/10.1093/sumbio/qvag033 （確認日 2026-11-05）
- 図書室の id: `2026-thompson-korean-natural-farming-imo`（全文 XML、Europe PMC PMC13487899）
- 権利: open（CC BY 4.0、本文の記載）
- 種類: 一次（室内の培養）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 韓国自然農法（KNF）の「土着微生物（IMO）」の培養を、塩性湿地・落葉樹林・都市の緑地の土（と殺菌した対照）で 2 段階行い、塩基配列で調べた。培養は限られた細菌（腸内細菌目、シュードモナス目、バシラス目）と菌類（Rhizopus oryzae など）に支配された。細菌の多様性は保たれるか増えたが、菌類の多様性は下がり続けた。その土地に固有の菌類中心の微生物叢を増やす、という KNF の主張とは大きく違った。
- 前提: 室内の培養。畑での効果は測っていない。
- 無肥料・無農薬に関わるか: 関わる（自然農法の資材の作り方の検証）。防御の話ではない。

#### H15. Influence of conventional and organic agricultural practices on the phenolic content in eggplant pulp: Plant-to-plant variation
- 著者・年: Luthria D., Singh A.P., Wilson T., Vorsa N., Banuelos G.S., Vinyard B.T.（2010）
- 誌名: Food Chemistry 121(2): 406–411
- DOI: https://doi.org/10.1016/j.foodchem.2009.12.055 （確認日 2026-11-05）
- 図書室の id: `2010-luthria-eggplant-organic-phenolics`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（圃場の試料の分析）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: ナス 2 品種（Blackbell、Millionaire）を慣行と有機で同じような気候で育て、果肉のフェノール含量を比べた。同じ品種・同じ条件の 8 株の間で、主なフェノール酸（5-カフェオイルキナ酸）は大きくばらついた（相対標準偏差 22〜48%）。Millionaire は Blackbell より総フェノールが多かった。有機と慣行で一貫した差は見られなかった。栽培条件の効果を言うには、何株も何季節も何か所も繰り返し分析すべきだ、と結ぶ。
- 前提: 国は要旨からは分からない。有機と慣行の圃場の果実の分析。
- 無肥料・無農薬に関わるか: 関わる（有機と慣行で防御物質とされるフェノールに一貫した差が無かった）。無肥料ではない。

#### H16. Effects of Organic and Conventional Growth Systems on the Content of Flavonoids in Onions and Phenolic Acids in Carrots and Potatoes
- 著者・年: Søltoft M., Nielsen J., Holst Laursen K., Husted S., Halekoh U., Knuthsen P.（2010）
- 誌名: Journal of Agricultural and Food Chemistry 58(19): 10323–10329
- DOI: https://doi.org/10.1021/jf101091c （確認日 2026-11-05）
- 図書室の id: `2010-sltoft-organic-polyphenols-vegetables`（書誌と要旨だけ）
- 権利: unknown（license の記載を見つけなかった）
- 種類: 一次（2 年・3 か所の圃場）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: タマネギ、ニンジン、ジャガイモを、3 か所で 2 年、慣行 1 と有機 2 の系で育て、フラボノイドとフェノール酸を測った。タマネギとニンジンでは、どの多価フェノールも系の間に有意な差が無かった。有機の方が健康に良い二次代謝物を一般に多く含むとは言えない、と結ぶ。
- 前提: 3 か所の 2 年の圃場試験（国は要旨からは分からない）、慣行 1・有機 2。
- 無肥料・無農薬に関わるか: 関わる（有機と慣行で多価フェノールに差が無かった）。無肥料ではない。

#### H17. Soil fertility management and insect pests: harmonizing soil and plant health in agroecosystems
- 著者・年: Altieri M.A., Nicholls C.I.（2003）
- 誌名: Soil and Tillage Research 72(2): 203–211
- DOI: https://doi.org/10.1016/S0167-1987(03)00089-8 （確認日 2026-11-05）
- 図書室の id: `2003-altieri-soil-fertility-insect-pests`（書誌だけ（要旨は記録に無い））
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 総説（題名だけ）
- 読了: Claude none、本人 none
- 書いてあること: 記録に要旨が無い。題名は「土の肥沃度の管理と害虫: 農業生態系での土と植物の健康の調和」。中身は読んでいない。
- 前提: 要旨からは分からない（要旨が無い）。
- 無肥料・無農薬に関わるか: 題名からは関わりそうだが、中身は読んでいない。

#### H18. The effects of farming system and fertilisers on pests and natural enemies: A synthesis of current research
- 著者・年: Garratt M.P.D., Wright D.J., Leather S.R.（2011）
- 誌名: Agriculture, Ecosystems & Environment 141(3-4): 261–270
- DOI: https://doi.org/10.1016/j.agee.2011.03.014 （確認日 2026-11-05）
- 図書室の id: `2011-garratt-farming-system-fertiliser-meta`（書誌と要旨だけ）
- 権利: quote（Elsevier の user license（TDM）。CC の記載は見ていない）
- 種類: 一次（メタ解析と票数え）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 有機と慣行の農業、および肥料の種類が節足動物の害虫と天敵に与える効果のメタ解析と票数え。害虫は概して有機の手法で増え、特に小さな規模の試験で明らか。肥料の種類への害虫の応答は分かれ、植物の堆肥は害虫を増やし、厩肥は逆だった。天敵の多くは有機で増え（甲虫を除く）、農場の規模の研究で特に正だった。有機肥料への天敵の応答は正だった。
- 前提: メタ解析。
- 無肥料・無農薬に関わるか: 関わる（有機の手法で害虫が増える傾向、肥料の種類で向きが変わる）。無肥料の区を含むかは要旨からは分からない。

#### H19. Evidence that organic farming promotes pest control
- 著者・年: Muneret L., Mitchell M., Seufert V., Aviron S., Djoudi E.A., Pétillon J., Plantegenest M., Thiéry D. ほか（2018）
- 誌名: Nature Sustainability 1(7): 361–368
- DOI: https://doi.org/10.1038/s41893-018-0102-4 （確認日 2026-11-05）
- 図書室の id: `2018-muneret-organic-pest-control-evidence`（書誌だけ（要旨は記録に無い））
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（題名だけ）
- 読了: Claude none、本人 none
- 書いてあること: 記録に要旨が無い。題名は「有機農業が害虫の防除を促す証拠」。中身は読んでいない。
- 前提: 要旨からは分からない（要旨が無い）。
- 無肥料・無農薬に関わるか: 題名からは関わりそうだが、中身は読んでいない。

#### H20. Organic management promotes natural pest control through altered plant resistance to insects
- 著者・年: Blundell R., Schmidt J.E., Igwe A., Cheung A.L., Vannette R.L., Gaudin A.C.M., Casteel C.L.（2020）
- 誌名: Nature Plants 6(5): 483–491
- DOI: https://doi.org/10.1038/s41477-020-0656-9 （確認日 2026-11-05）
- 図書室の id: `2020-blundell-organic-tomato-resistance`（書誌と要旨だけ）
- 権利: quote（Springer Nature の TDM の license。CC の記載は見ていない）
- 種類: 一次（圃場の土と室内）
- 読了: Claude abstract、本人 none
- 書いてあること（要旨）: 長期の有機の農場で害虫が少ないのは、天敵の多様性と数、植物の養分の変化によるとされてきたが、植物の抵抗性の役割は無視されてきた。有機で育てたトマトには慣行よりヨコバイ（Circulifer tenellus）が少なく定着した。根圏の微生物叢の塩基配列、化学分析、遺伝子組換えの手法で、この差は植物のサリチル酸の蓄積に依存し、根圏の微生物群集が仲立ちすることを示した。有機の土と微生物が植物の抵抗性を上げて害虫を引き寄せにくくする、という見過ごされた役割を示唆する。
- 前提: 有機と慣行の土のトマト（国は要旨からは分からない）。圃場と室内の組み合わせ。
- 無肥料・無農薬に関わるか: 関わる（有機の土の微生物で植物の抵抗性が上がった）。無肥料ではない。作者の見立てに最も近い一次資料の一つ。

---

## ほかの候補（開いていない、または有料で要旨も読んでいない）

前回ここに挙げた 9 件は、書誌と要旨（または抄録）を取って上の節に移した: Pieterse ら 2014 → A3、Conrath ら 2015 → A8、Mauch-Mani ら 2017 → A9、Turlings & Erb 2018 → C12、Letourneau ら 2011 → E22、Iverson ら 2014 → E23、Khan ら 2016 → E24、Dordas 2008 → D16（要旨は記録に無く、題名だけ）、西條・山田 2015 → F16。どれも全文は読んでいない。

| 題 | 著者・年 | DOI・URL | 開いていない理由 |
|---|---|---|---|
| （学位論文。題は確かめていない） | 赤池一彦 2015（東京農業大学、検索の結果の文では混作・間作による野菜の有機栽培） | https://nodai.repo.nii.ac.jp/record/641/files/2015-725.pdf | 検索に出ただけで開いていない。F3、F9、F10 の著者 |
