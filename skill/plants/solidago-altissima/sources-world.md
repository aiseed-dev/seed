# セイタカアワダチソウ Solidago altissima — 世界の論文（2026-11-02）

作者の「日本だけでなく世界の論文を調べろ」から。Claude の調べ手（別のセッション）が集め、この手引きを書いた Claude が
形を整えた。**本人はどれも読んでいない。** 読みの行の根拠にするときは `basis` に「plants/solidago-altissima W16」
のように書き、確からしさは 0.6 を超えない。本人が開いて確かめた物は根本の `sources.md` に移す。

**列の読み方。** 「種」= 論文が扱う種（alt = S. altissima セイタカアワダチソウ、can = S. canadensis、gig = S. gigantea オオアワダチソウ。
後の二つは欧州と中国の侵入種で、同じ属の別種）。「読了」= 調べ手が読んだ範囲（全文／要旨／抜粋 = 検索の断片や二次資料だけ）。
DOI は調べ手が Crossref か J-STAGE で確かめた物。確かめられなかった物は書いてある。全文の写しは本人のフォルダー
`~/farm/seed/notes/sources/` にある（公開しない）。

問いは一つ。セイタカアワダチソウが 2 m で面を占めている所は、土の何を語るか。放棄田・氾濫原・硬盤層のある畑で読むときの
手掛かりになるように集めた。**ここに書くのは植物一般のこと。** ある畑でそれが何を意味するかは、その人の手引きの 06 章
「資料から立てた仮説」「草が語ること（本人）」に書き、共通の手引きには書かない。

## 先に、要点（Claude の要約。表の番号で引く）

- **地下茎は浅い。** 大部分が地表下 5〜7 cm（W25）。欧州の近縁種も芽は 10 cm より浅く（W27）、20 cm に埋めると出ない（W26）。
  「在来の植生より深く根を張らない」（W28、W29）。→ **この草は表層で完結している。その大きさは、硬盤層の下を語らない**
- **乾いた側の草。** 新潟の放棄水田で、セイタカアワダチソウとススキは「乾燥型」、マコモとヨシは「湿潤型」で、同じ区画の
  中で地下水位に応じて分かれる（W3）。茨城の氾濫原で 5〜10 日の冠水の後、オギは変わらずセイタカアワダチソウは大きく
  減って枯れた（W4）。→ **セイタカアワダチソウが面を占めている所は、長く水に浸からない所**
- **排水の悪い粘土でも 2 m になる。** 淀川の高水敷（砂礫まじりの粘土質、排水不良、雨期に滞水）で草丈 1.5〜2 m の群落（W2）。
  ポーランドでは出現区の土壌に差が無く、土は予測因子にならない（W6）。pH は休耕田の 5.2 から路傍の 8.1 まで（W1）。
  → **2 m という大きさは、土の肥えや土性を選んで語らない。「普通の放棄地」の大きさ**
- **草丈と養分。** ポーランドで S. altissima の草丈は Ca と K に正の相関（W6）。北米の放棄畑で養分を足すと Solidago の優占が
  強まる（W14）。日本の利根川氾濫原の自然群落で、現存量 400〜1,950 g/m²、窒素 7〜14.7 g N/m²（W16）。→ 大きいほど
  養分が多い傾向はあるが、土の窒素と草丈を直接結んだ日本の論文は無い
- **刈り方。** 済州島: 年 2 回（5・9 月）で開花 0%、年 3 回で地下茎の現存量が対照の 54%（W20）。淀川: 年 1 回では優占は崩れず、
  年 2 回で崩れることもあり、年 3 回以上で退行（W21）。ハンガリー: 年 2 回、特に 9 月の刈りが効く（W22）。→ **刈る回数と
  時期が、この草への応えを決める。年 1 回は効かない**
- **自家中毒は実証されていない。** 土の中の阻害物質（DME）は自然群落では活性が小さい（W34）。群落が年を経て退く記録は
  北海道（15 年。置き換えたのはササ、W38）と「1980 年頃から遷移でススキやクズへ」の記述（藤井 1990 を引く W38）。
  → **「古くなると自家中毒で衰える」は説で、測った研究は無い**
- **土を肥やす草ではない。** 日本の放棄水田 37 対で、セイタカアワダチソウ区と在来植生区の炭素の蓄積に差なし、リターの炭素は
  むしろ少ない（W41）。近縁種で土の N 可給性が下がる例（W47）と上がる例（W42、W44）があり、方向は土による（W48）。
- **菌根菌。** 近縁の S. canadensis は菌根菌で成長が増え、りん酸の乏しい土で定着率 80% 超（W30、W31）。
  → セイタカアワダチソウの面は、**菌根菌の宿主が絶えない面**でもあるかもしれない（別種の結果。低い確からしさ）

## A. 立地・土壌条件（土性・水分・pH・養分）

| # | 文献 | 種 | 国/場所 | 内容（数値は原文より） | 読了 |
|---|---|---|---|---|---|
| W1 | Itani T, Hijimoto S (1978) Studies on ecological characteristics of *Solidago altissima* L. III. Effects of soil reaction on the growth. 雑草研究 23(4):165–169. doi:10.3719/weed.23.165 | alt | 日本（広島） | 水耕: NH4-N 系では pH 7–8、NO3-N 系では pH 4–9 でよく生育。土耕: 無耕地砂土では pH 上昇で生育低下、**水田埴壌土では pH 上昇でやや増加**。野外の自生地土壌 pH は**休耕田 5.2〜路傍 8.1**。「土壌反応への適応性が最も高い植物の一つ」 | 要旨 |
| W2 | 服部保・赤松弘治・浅見佳世・武田義明 (1993) 河川草地群落の生態学的研究 I. セイタカアワダチソウ群落の発達および種類組成におよぼす刈り取りの影響. 人と自然 2:105–118. https://www.jstage.jst.go.jp/article/hitotoshizen/2/0/2_105/_article/-char/ja | alt | 日本・淀川右岸高水敷（大阪、標高約 4 m） | 立地は「**砂礫まじりの粘土質土壌で、排水は不良であり、雨期には滞水する時もある**」。そこで秋に**草丈 1.5–2 m** のよく発達した群落（被度 45% 以上）。刈り取りは W21 | 全文 |
| W3 | 石原佳紘・吉川夏樹・正垣良健・宮津進 (2024) 耕作放棄水田の土壌水分判別手法の検討. 農業農村工学会大会講演会講演要旨集 [8-39(P)]；同 (2025) 耕作放棄水田の乾湿判別および予測手法の検討. 同 [2-19] | alt | 日本（新潟・新発田、佐渡、福井・池田） | 放棄水田の植生を湿潤型／乾燥型に分類。**セイタカアワダチソウとススキは乾燥型**で 60 分積算浸透量 35 mm 以上；湿潤型のマコモ・ヨシは 0 mm、アキノウナギツカミ・ミゾソバは 10 mm 以下。同一区画内に両型が混在し「**地下水位の影響を受けて生育に適した植生が出現**」。乾燥型の平均浸透能: 新発田 52 mm、佐渡 120 mm | 全文（講演要旨） |
| W4 | 西平貴一・澤田みつ子・鈴木康平・小幡和男・上條隆志 (2017) 茨城県菅生沼における豪雨による冠水攪乱が植物の生育に与える影響. 茨城県自然博物館研究報告 20:1–6 | alt | 日本・茨城（氾濫原湿地） | 2015 年 9 月豪雨で 5〜10 日間冠水。**オギとカサスゲは出現頻度に変化なし**。**セイタカアワダチソウ（とオオブタクサ）は冠水後に出現頻度が大きく減少**し、先端まで枯死した個体が多数。同所のオギは草丈が低くても枯死しなかった | 全文 |
| W5 | Rahman M, Asaeda T, Fukahori K, Rashid MH, Kawashima H, Akimoto J, Anta RT (2025) A rapid method for identifying plant oxidative stress and implications for riparian vegetation management. Environments 12:247. doi:10.3390/environments12070247 | alt | 日本・荒川太郎右衛門地区（氾濫原） | 葉の H2O2（ストレス指標）は **S. altissima では土壌水分が高いほど上昇**（ヨモギ・アレチウリは逆）。TN・TP・光は有意でなく、土壌水分のみ有意 | 要旨＋本文抜粋 |
| W6 | Szymura M, Szymura TH (2013) Soil preferences and morphological diversity of goldenrods (*Solidago* L.) from south-western Poland. Acta Soc Bot Pol 82(2):107–115. doi:10.5586/asbp.2013.005 | alt, can, gig | ポーランド・シレジア（放棄畑 36 区、草地 35 区） | 0–20 cm の土性・pH・OM・全 N・NO3・P・K・Ca を測定。**各 Solidago 種の出現区の土壌条件に有意差なし**（土壌は出現種の予測因子にならない）。**S. gigantea は湿草地種と、S. altissima/canadensis はルデラル種と共存**。**S. altissima の草丈は Ca・K と正相関、S. gigantea の草丈は OM・NO3 と正相関**。原産地では S. gigantea は湿った土、S. altissima は中程度の水分の土で密度が高いという引用 | 全文 |
| W7 | Czortek P, Królak E, Borkowska L, Bielecka A (2020) Impacts of soil properties and functional diversity on the performance of invasive plant species *Solidago canadensis* L. on post-agricultural wastelands. Sci Total Environ 729:139077. doi:10.1016/j.scitotenv.2020.139077 | can | ポーランド（農業跡地） | **粘土・シルト（loamy）画分が多いほど S. canadensis の被度が大きい** | 抜粋 |
| W8 | Zubek S, Majewska ML, Kapusta P, Stefanowicz A, Błaszkowski J, Rożek K, Stanek M, Karpowicz F, Zalewska-Gałosz J (2020) *Solidago canadensis* invasion in abandoned arable fields induces minor changes in soil properties and does not affect the performance of subsequent crops. Land Degrad Dev 31:334–345. doi:10.1002/ldr.3452 | can | ポーランド（放棄畑） | 在来植生を強く置換するが土壌への影響は小さい。**侵入区は土壌水分が低く、菌根のパラメータとウレアーゼ活性が高い**。後作のヒマワリ・トウモロコシへの影響は小さい | 要旨 |
| W9 | Kowalska A ほか (2026) A multi-faceted assessment of the condition of ecosystems affected by the invasion of North American goldenrods. ARPHA Conf Abstr 9:e198311. doi:10.3897/aca.9.e198311 | 属 | ポーランド・マゾフシェ（放棄畑 20 区） | 侵入区と非侵入区で**実水分・毛管孔隙・気相率が有意に異なる**；OM、CO2 フラックス、化学性の多くは差なし | 要旨（学会要旨） |
| W10 | Güsewell S, Zuberbühler N, Clerc C (2005) Distribution and functional traits of *Solidago gigantea* in a Swiss lakeshore wetland. Bot Helv 115:63–75. doi:10.1007/s00035-005-0721-z | gig | スイス・湖岸湿地 600 ha | 水位は冬に地表以上、夏に地表下 20–100 cm。分布は**低養分ではなく高い水位によって制限** | 抜粋 |
| W11 | Weber E, Jakobs G (2005) Biological flora of central Europe: *Solidago gigantea* Aiton. Flora 200:109–118. doi:10.1016/j.flora.2004.09.001 | gig | 中欧 | 要旨は有料で未確認。二次資料では「水分・光・養分・温度・pH への耐性は広いが**窒素に富む湿〜中湿の土を好む**」「**地下茎は上層 10–20 cm**」 | 抜粋（二次資料） |
| W12 | Jakobs G, Weber E, Edwards PJ (2004) Introduced plants of the invasive *Solidago gigantea* are larger and grow denser than conspecifics in the native range. Divers Distrib 10:11–19. doi:10.1111/j.1472-4642.2004.00052.x | gig | 北米 46 vs 欧州 45 個体群 | 欧州個体群はサイズ・密度・総バイオマスが大きい | 要旨 |
| W13 | 郭水良・方芳 (2003) 入侵植物加拿大一枝黄花对环境的生理适应性研究. 植物生态学报 27(1):47–52. doi:10.17521/cjpe.2003.0007 | can | 中国 | 検索要約: **偏酸性・低塩の土に適応、砂壌土・壌土が粘土より生育に有利**。要旨本文は未読 | 抜粋 |
| W14 | Carson WP, Pickett STA (1990) Role of resources and disturbance in the organization of an old-field plant community. Ecology 71:226–238 | *Solidago* spp. | 米国ニュージャージー（放棄畑） | 2 年の要因実験。**養分添加は Solidago の優占を強めた**；小規模攪乱の役割は資源に比べ小 | 要旨 |
| W15 | 鹿児島県 (2017) 鹿児島県侵略的外来種カルテ: セイタカアワダチソウ | alt | 日本 | 「粒径の細かい**シルトから粘土質の土壌に繁茂する。耐乾性がある**」。出典明示なしの行政資料 | 全文（行政資料） |

## B. 草丈・現存量と窒素（施肥・刈り取り実験）

| # | 文献 | 種 | 国/場所 | 内容 | 読了 |
|---|---|---|---|---|---|
| W16 | Hirose T (1971) Nitrogen turnover and dry-matter production of a *Solidago altissima* population. 日本生態学会誌 21(1–2):18–32. doi:10.18960/seitai.21.1-2_18 | alt | 日本・**利根川氾濫原（取手市付近）**の自然群落 | 乾物現存量 **400〜1,950 g DM/m²**、年間 2,290 g/m² が流れる。窒素現存量 **7（12 月）〜14.7 g N/m²（10 月）**。窒素の回転率は乾物より大幅に低く、体内再利用による。土壌 N の記載なし | 全文（OCR） |
| W17 | Iwaki H, Takada K, Monsi M (1969) Studies on the dry matter production of *Solidago altissima* community I. Bot Mag Tokyo 82:215–225. doi:10.15281/jplantres1887.82.215 | alt | 日本・取手（1964） | 地上部現存量ピーク **1,230 g/m²（10 月下旬）**、LAI 最大 4.8、年純生産 ≈1,780 g/m²、地下部純生産 ≈290 g/m² | 要旨 |
| W18 | Stoll P, Egli P, Schmid B (1998) Plant foraging and rhizome growth patterns of *Solidago altissima* in response to mowing and fertilizer application. J Ecol 86:341–354 | alt | スイス（刈取 6 年＋施肥 2 年） | **施肥は地下茎の乾物重を増やしたが、数と長さはほぼ増やさない**。刈り取りで生き残る地下茎は短く少なく、乾物重は無刈区の 50% 未満 | 要旨 |
| W19 | Egli P, Schmid B (2000) Seasonal dynamics of biomass and nitrogen in canopies of *Solidago altissima* and effects of a yearly mowing treatment. Acta Oecol 21:63–77. doi:10.1016/S1146-609X(00)00111-9；Egli P, Schmid B (1999) Acta Oecol 20(5) | alt | スイス | 年 1 回刈りで全器官の最終バイオマス低下；組織 N 濃度は地下茎以外変化なし。1999: **施肥区では N 制限でなかった** | 要旨 |

## C. 刈り取り頻度への応え

| # | 文献 | 種 | 国/場所 | 内容 | 読了 |
|---|---|---|---|---|---|
| W20 | Rim H, Lee M, Song U (2023) Mowing inhibits the invasion of the alien species *Solidago altissima* and is an effective management strategy. Manag Biol Invasions 14(1):63–79. doi:10.3391/mbi.2023.14.1.03 | alt | 韓国・済州島（放棄草地、年降水 1,770–1,840 mm） | 年 1 回（7 月）、2 回（5・9 月）、3 回（5・7・9 月）、2 年。1 年目は被度に差なし。**地下茎の現存量（2 年後）: 対照 987.7、1 回 933.6、2 回 732.0、3 回 535.3 g/m²**。開花率: 1 回区 100%、**2 回区 0%、3 回区 20%** | 全文 |
| W21 | 服部ほか (1993)（W2） | alt | 日本・淀川 | 年 0〜4 回刈りの 6 区、2 年。地上部現存量: **年 4 回 6.6、3 回 5.0・3.8、2 回 28.4、1 回 124.7、無刈 413.2 g/m²**。年 3 回以上で群落は退行し一年草が 50% 以上。**年 1 回では翌年の草丈・被度は変わらず優占を破れない** | 全文 |
| W22 | Szépligeti M, Kőrösi Á, Szentirmai I, Házi J, Bartha D, Bartha S (2018) Evaluating alternative mowing regimes for conservation management of Central European mesic hay meadows. Plant Biosyst 152:90–97. doi:10.1080/11263504.2016.1255268 | gig | ハンガリー西部（7 年） | **年 2 回刈りが拡大を抑えた唯一の処理**；9 月刈りは 5 月刈りより効く | 抜粋 |
| W23 | Szymura M, Świerszcz S, Szymura TH (2022) Restoration of ecologically valuable grassland on sites degraded by invasive *Solidago*: lessons from a six-year experiment. Land Degrad Dev. doi:10.1002/ldr.4278 | can/gig | ポーランド | **年 2 回刈りで 6 年後に被度は当初（100%）の 25%**。除草剤は長期的に有効でない | 抜粋 |
| W24 | Nagy DU, Rauschert ESJ, Henn T, Cianfaglione K, Stranczinger S, Pal RW (2020) The more we do, the less we gain? Weed Res 60:232–240. doi:10.1111/wre.12417；Nagy DU ほか (2021) Restor Ecol 30:e13483. doi:10.1111/rec.13483 | gig | ハンガリー | 放牧・刈り取り・周期的冠水すべてが密度を下げる。刈り取りで密度 **80–98%** 低下、**1 年放置で対照の 2 倍** | 要旨 |

## D. 地下部（地下茎の深さ・根・菌根菌）

| # | 文献 | 種 | 国/場所 | 内容 | 読了 |
|---|---|---|---|---|---|
| W25 | 行永寿二郎・井手欽也・伊藤幹二・嶋田資久 (1975) セイタカアワダチソウの生態に関する 2, 3 の観察と asulam による防除. 雑草研究 19:46–50. doi:10.3719/weed.1975.46 | alt | 日本 | **大部分の地下茎は地表下 5–7 cm**；切断地下茎は**深さ 30 cm までは出芽可能**。1 年間の地下茎伸長: 株当たり総長 4.1 m、本数 9.9、1 本平均 42.0 cm | 要旨 |
| W26 | Weber E (2011) Strong regeneration ability from rhizome fragments in two invasive clonal plants (*Solidago canadensis* and *S. gigantea*). Biol Invasions 13:2947–2955. doi:10.1007/s10530-011-9977-y | can, gig | スイス | 埋設深 0/5/10/20 cm。**S. canadensis は 20 cm 埋設から出芽ゼロ**；S. gigantea は全深度から出芽 | 抜粋 |
| W27 | Pladias（チェコ植物データベース）*Solidago gigantea* 芽バンク https://pladias.cz/en/factsheet/default/4504 | gig | チェコ | 地下芽バンク深さ約 4 cm、0–10 cm 層に 15 芽/シュート、**10 cm 以深の芽は 0** | 抜粋（DB） |
| W28 | Herr C, Chapuis-Lardy L, Dassonville N, Vanderhoeven S, Meerts P (2007) Seasonal effect of the exotic invasive plant *Solidago gigantea* on soil pH and P fractions. J Plant Nutr Soil Sci 170:729–738. doi:10.1002/jpln.200625190 | gig | ベルギー（**放棄畑、シルト質ローム**） | 0–10 cm: pH 6.5→5.9、**容積重 1.21→1.13 g/cm³**、全 C 1.48→1.80%（ns）。易動性 P +20–30%。「**在来植生より深く根を張らない**」 | 全文 |
| W29 | Vanderhoeven S, Dassonville N, Chapuis-Lardy L, Hayez M, Meerts P (2006) Impact of the invasive alien plant *Solidago gigantea* on primary productivity, plant nutrient content and soil mineral nutrient concentrations. Plant Soil 286:259–268. doi:10.1007/s11104-006-9042-2 | gig | ベルギー 5 地点 | 侵入区の地上部生産は **2–3 倍**。表土の化学性への影響は小（P は 4 地点で高い）。深層養分の汲み上げは有意でない | 全文（部分） |
| W30 | Dong L-J, Ma L-N, He W-M (2021) Arbuscular mycorrhizal fungi help explain invasion success of *Solidago canadensis*. Appl Soil Ecol 157:103763. doi:10.1016/j.apsoil.2020.103763 | can | 中国 | 菌根菌は S. canadensis の成長と隣接在来種の抑制能を高めた | 抜粋 |
| W31 | Qi S ほか (2022) Arbuscular mycorrhizal fungi contribute to phosphorous uptake and allocation strategies of *Solidago canadensis* in a phosphorous-deficient environment. Front Plant Sci 13:831654. doi:10.3389/fpls.2022.831654 | can | 中国（滅菌砂） | 難溶性 P で菌根菌の定着率 >80%（可給 P で 17%）、地上部成長 ≈+50%、全 P +107% | 全文（抜粋） |
| W32 | Walck JL, Baskin JM, Baskin CC (1999) Am J Bot 86:820–828 | alt | 米国（温室 23 週） | root:shoot 0.58、(root+rhizome):shoot 0.63；栄養繁殖への配分 3.2% | 抜粋 |

## E. アレロパシー・自家中毒・群落の衰退・遷移

| # | 文献 | 種 | 国/場所 | 内容 | 読了 |
|---|---|---|---|---|---|
| W33 | Kobayashi A, Morimoto S, Shibata Y, Yamashita K, Numata M (1980) C10-polyacetylenes as allelopathic substances in dominants in early stages of secondary succession. J Chem Ecol 6:119–131. doi:10.1007/BF00987532 | alt | 日本 | cis-/trans-DME が**群落の縁の土壌から阻害的な濃度で検出** | 抜粋 |
| W34 | Ito I, Kobayashi K, Yoneyama T (1998) Fate of dehydromatricaria ester added to soil and its implications for the allelopathic effect of *Solidago altissima* L. Ann Bot 82:625–630. doi:10.1006/anbo.1998.0722 | alt | 日本 | 土壌中 DME の 50% 阻害濃度は寒天の 10–20 倍。DME は土粒子に強く吸着、約 10 日で分解。**自然群落土壌の DME 最大 4.5 µg/g、土壌水からは検出されず**→「自然群落では DME のアレロパシー活性は小さい」 | 要旨 |
| W35 | 中村直紀・根本正之 (1997) セイタカアワダチソウの cis-dehydromatricaria ester 含有量および放出量. 雑草研究 41(4):359–361. doi:10.3719/weed.41.359 | alt | 日本 | 部位別含有量と溶脱液への放出量。数値は未読 | 書誌のみ |
| W36 | Kato-Noguchi H, Kato M (2022) Allelopathy and allelochemicals of *Solidago canadensis* L. and *S. altissima* L. for their naturalization. Plants 11:3235. doi:10.3390/plants11233235 | alt, can | 総説 | 根滲出液・抽出物・根圏土壌が他種の発芽・成長・菌根菌の定着を抑える。**自家中毒や群落衰退の記述は要旨になし** | 要旨 |
| W37 | Dong L-J, Sun Z-K, Gao Y, He W-M (2015) J Plant Ecol 8:617–622. doi:10.1093/jpe/rtv003；Dong L-J ほか (2017) Ecol Evol 7:2307–2315. doi:10.1002/ece3.2743 | can | 中国 | 2015: 2 年育った土は**自身と在来 5 種の後続成長を低下**（負の植物–土壌フィードバック）。2017: 81 対の野外土壌では群落レベルで**中立** | 要旨 |
| W38 | 西川洋子・島村崇志・宮木雅美 (2021) 野幌森林公園の農地跡に成立した草原の変遷―外来草本とササの関係―. 北海道立総合研究機構 エネルギー・環境・地質研究所報告 1:75–81 https://www.hro.or.jp/upload/29506/eegrpt01p075-081.pdf | alt, gig | 北海道・江別（放棄農地、15 年 2000–2014） | 生育区画数は **2004 年まで増加後に減少**、**優占区画は 2011 年に 0**。置き換えたのはクマイザサ。両アワダチソウは **10 cm 以下の短い地下茎**。藤井 (1990, 化学と生物 28:471–478) を引き「1980 年頃から植生遷移の進行に伴いススキやクズが優占する群落に変化しつつある」。自家中毒の実測はなし | 全文 |
| W39 | Ito T, Nakayama Y, Yamaguchi H (1999) Floral composition and successional process of vegetation on the levees of traditional and reconstructed paddy fields in Sakai, Japan. 雑草研究 44(4):329–340. doi:10.3719/weed.44.329 | alt | 日本・堺 | 圃場整備 6 年・10 年後の畦畔で優占化；伝統畦畔は在来多年草が優占 | 要旨 |
| W40 | 濱田洋平 (2008) ススキ株の空間構造とその季節変化. 筑波大学陸域環境研究センター報告 9:29–34 | alt→ススキ | 日本・つくば | 「第 III 草本ステージ（セイタカアワダチソウ群落）から第 IV 草本ステージ（ススキ群落）への移行期」。衰退の仕組みの記述なし | 抜粋 |

## F. 侵入による土の C・N・微生物の変化

| # | 文献 | 種 | 国/場所 | 内容 | 読了 |
|---|---|---|---|---|---|
| W41 | Shimoda S, Wagai R (2020) Ecosystem dynamics after abandonment of rice paddy fields: does alien plant invasion enhance carbon storage? Ecosystems 23(3):617–629. doi:10.1007/s10021-019-00426-1 | alt | 日本（放棄水田 37 対、放棄 2–37 年） | 放棄後**最初の約 15 年は生態系 C が減少**、その後増加し約 30 年で最大 +10 Mg C/ha。**セイタカアワダチソウ区と在来植生区で C 蓄積に差なし、リター C は有意に低い** | 要旨 |
| W42 | 陸建忠・裘伟・陈家宽・李博 (2005) 入侵种加拿大一枝黄花对土壤特性的影响. 生物多样性 13(4):347–. doi:10.1360/biodiv.050071 | can | 中国・上海 | 侵入土壌の pH 約 8.2；全 C・N 増；NH4-N・NO3-N プールは減少、**正味無機化速度は野外で約 3 倍** | 要旨 |
| W43 | Zhang C-B, Wang J, Qian B-Y, Li W-H (2009) Effects of the invader *Solidago canadensis* on soil properties. Appl Soil Ecol 43:163–169. doi:10.1016/j.apsoil.2009.07.001 | can | 中国・浙江 | 侵入区で**全 N・全 P・NO3-N・可給 P・団粒安定性が低下、有機 C・NH4-N・pH・容積重が上昇** | 抜粋 |
| W44 | Ye X-Q, Yan Y-N, Wu M, Yu F-H (2019) High capacity of nutrient accumulation by invasive *Solidago canadensis* in a coastal grassland. Front Plant Sci 10:575. doi:10.3389/fpls.2019.00575 | can | 中国・杭州湾（**沿岸シルト質粘土、pH>8**） | 草丈 1.53 m、被度 85%。表土の全 N・P・K は不変、NH4・NO3 は増加。**土壌 pH と含水率は S. canadensis 下で最低** | 全文（抜粋） |
| W45 | Hu Z ほか (2021) Effects of Canada goldenrod invasion on soil extracellular enzyme activities and ecoenzymatic stoichiometry. Sustainability 13:3768. doi:10.3390/su13073768 | can | 中国 | 酵素活性の**低下**（W44 とは逆方向） | 要旨 |
| W46 | Ren G ほか (2020) Effects of *Solidago canadensis* invasion and climate warming on soil net N mineralization. Pol J Environ Stud 29(5):3285–3294. doi:10.15244/pjoes/114237 | can | 中国（ポット） | 無機化・硝化・アンモニア化が低下 | 要旨 |
| W47 | Scharfy D, Eggenschwiler H, Olde Venterink H, Edwards PJ, Güsewell S (2009) The invasive alien plant species *Solidago gigantea* alters ecosystem properties across habitats with differing fertility. J Veg Sci 20:1072–1085. doi:10.1111/j.1654-1103.2009.01105.x | gig | スイス低地 14 地点 | 地上部生産と土壌 C は増、**土壌 N 可給性は減**；保守的養分利用。効果は P に富む地点で強い | 要旨 |
| W48 | Goossens E, Mertens W, Olde Venterink H (2024) *Solidago gigantea* invasion homogenizes soil properties and native plant communities. Biol Invasions 26:3315–3327. doi:10.1007/s10530-024-03374-7 | gig | ベルギー | 抽出態 N と pH の変化の**方向と大きさは初期土壌条件に依存** | 抜粋 |
| W49 | Vanderhoeven S, Dassonville N, Meerts P (2005) Increased topsoil mineral nutrient concentrations under exotic invasive plants in Belgium. Plant Soil 275:169–179 | gig 他 | ベルギー 8 地点 | 侵入植物下で交換性養分が高く、K +32%、Mn +34% | 要旨 |

## 探したが見つからなかった物

1. **自家中毒 → 群落衰退 → ススキに置き換わる、を実験で確かめた一次論文**。あるのは、土の DME は自然群落では活性が小さい（W34）、遷移で後退する記述（W38、W40）、近縁種の培養土での自己抑制（W37。野外では中立）だけ
2. **セイタカアワダチソウと硬盤層・圧密の直接の研究**。間接情報は地下茎の深さ（5–7 cm、W25；近縁種の芽は 10 cm より浅い、W27；20 cm 埋設で出芽ゼロ、W26）と「在来植生より深く根を張らない」（W28、W29）。**根（地下茎でなく）の深さの分布を土層別に測った論文は無い**
3. **日本で草丈・現存量を複数の立地の土壌 N と対比した論文**。あるのは単一立地の N 現存量（W16）と北米の養分添加（W14）。S. altissima への窒素添加実験は無し（中国の N 添加は全て S. canadensis）
4. **放棄水田でセイタカアワダチソウとオギの優占を土壌水分・地下水位で比べた研究**。近いのは新潟の乾湿判別（W3）、菅生沼の冠水（W4）、荒川の水分ストレス（W5）
5. Egli & Schmid の「栄養の不均一の下でのクローン成長」論文、韓国の侵入地の土壌の研究、Weber & Jakobs 2005 の要旨、中村・根本 1997 の数値、郭・方 2003 の要旨本文、Shimoda & Wagai 2020 の土壌 N の結果
6. 行永ら 1975 の地下茎の深さは、石川県の報告の要約（4–8 cm）と J-STAGE の要旨（5–7 cm）で数字が違う。要旨を採った
