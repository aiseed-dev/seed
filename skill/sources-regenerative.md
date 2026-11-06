# 一次資料の候補 — リジェネラティブ農業と混植

**ここにある物は候補。作者が読んで `sources.md` に移すまで、手引きの根拠にしない。**

`sources.md` に移すのは、作者が自分で読んだ物だけです。移すときは、題名・著者・年・URL・確認日を付け、番号を振ります。この一覧の「読了」欄は、すべて未読です。

## この一覧について

- 作ったのは Claude です（2026-11-02）。書誌（題名・著者・年・誌名・DOI）は、OpenAlex、Crossref、Europe PMC の記録で照合しました。本文は読んでいません。
- 「何が書いてあるか」は、**要旨（または資料の冒頭・表）から読める範囲**だけです。要旨が開けない物は「要旨を取れなかった」と書き、題名より先は書いていません。
- 年は出版年です（オンライン先行の年のことがあります）。巻・頁は省きました。DOI から開いて確かめてください。
- 「前提」は、施肥・耕起・単作か混植か・地域・規模のうち、要旨や資料から読めた物です。**書いていない物は「記載なし」**です。記載なしは「無い」の意味ではありません。
- 世界の混植の研究は、中国・アフリカ・欧州の、施肥した畑のものが多い。無施肥・不耕起・日本の気候の畑に、そのまま当てはまるとは限りません。メタ解析は、試験ごとの前提がばらばらの平均です。
- 日本の公の研究データ（農研機構、農水省、都道府県）は、施肥・耕起・単作・農薬を前提に取られています。(D) に置き、前提を一行で書きました。
- 種苗会社・販売会社・ブログ・まとめサイトは入れていません。
- 既読として入れていない物: aiai の「出典」（Tuck 2014、Tamburini 2020、Abdalla 2019、Ponisio 2015、Knapp 2018、Pittelkow 2015、Cooper 2016、Berger 2025、Duddigan 2023、Bowles 2017、Sattari 2012、Treseder 2004、Jiang 2021 ほか）と、Light Farming の全訳。
- 一次か二次か: 「一次」は、その研究者自身が試験・調査を行った論文。「一次（メタ解析）」は、多数の一次論文を統計的にまとめた論文。「二次」は、総説・本・講演資料。

## 見つからなかった物（正直に）

- **福岡正信の混播（クローバー・麦・稲を一度にまく）を圃場で試験した査読論文**は、OpenAlex と Web 検索では見つかりませんでした。福岡正信を扱う論文は、思想・民族誌・政治生態学が中心でした。混播の効果を数字で見るなら、(A) の混植の論文と、(D) の日本のリビングマルチの資料から、作者が組み立てることになります。
- **日本の伝統的な混作・間作の記録**（江戸の農書など）は、原本を確かめられませんでした。ここには入れていません。King 1911（A-31）は、日本も含む東アジアの観察記録ですが、混作の記述があるかは読んでいません。
- **無施肥・不耕起の畑での混植**を、長期に比べた試験は見つかりませんでした。
- 書誌を確かめられなかった物（題名と出所は知っているが、API で出なかった）。読むなら、図書館や出版社のページで確かめてください:
  - Mead R, Willey RW, "The concept of a 'land equivalent ratio' and advantages in yields from intercropping", Experimental Agriculture, 1980（LER の定義の元の論文）
  - Andow DA, "Vegetational diversity and arthropod population response", Annual Review of Entomology, 1991

---

## (A) 混植

### 混植 1: 収量・土地の節約（メタ解析と総説）

#### A-1. Syndromes of production in intercropping impact yield gains
- 著者・年・どこに: Chunjie Li ほか（8名）、2020、Nature Plants
- DOI: https://doi.org/10.1038/s41477-020-0680-9
- 書いてあること: 世界のメタ解析。単作に対する絶対的な増収は、トウモロコシと、時期のずれる小粒の穀類かマメ科（要旨の語は short-grain cereals）を、養分を多く入れて、複数条のストリップで植えたときに最大。もう一つの低投入型（背の低い作物の混播、養分は少〜中）は、増収が約四分の一。
- 前提: 中国で一般的な高投入ストリップ型と、中国以外で一般的な低投入型を比べる。試験ごとの施肥・耕起は記載なし。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-2. Intercrop overyielding weakened by high inputs: Global meta-analysis with experimental validation
- 著者・年・どこに: Shuang-Guo Zhu ほか（11名）、2023（オンライン 2022）、Agriculture, Ecosystems & Environment
- DOI: https://doi.org/10.1016/j.agee.2022.108239
- 書いてあること: LER の平均は収量 1.49、バイオマス 1.25、N 吸収 1.35、P 吸収 1.66。施肥が多いと、相対的な優位が下がる。P・N・水の傾度を変えた三つの試験（トウモロコシ–グラスピー、トウモロコシ–コムギ・–ダイズ、コムギ–ダイズ）で確かめた。
- 前提: 施肥の傾度が主題。試験地は要旨に記載なし。
- 種類: 一次（メタ解析と圃場試験）
- 読了: 未読

#### A-3. Temporal niche differentiation increases the land equivalent ratio of annual intercrops: A meta-analysis
- 著者・年・どこに: Yang Yu、T.J. Stomph、David Makowski、Wopke van der Werf、2015、Field Crops Research
- DOI: https://doi.org/10.1016/j.fcr.2015.09.010
- 書いてあること: LER の平均 1.22±0.02。C3 と C4 の組み合わせでは、生育時期のずれ（時間的ニッチの分化）が高い LER に寄与した。植え方（パターン）、相対密度、窒素施肥量の効果も見ている。要旨の後半（C3 同士の結果など）は、ここで読んでいない。
- 前提: メタ解析。窒素施肥は説明変数の一つ。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-4. The new Green Revolution: Sustainable intensification of agriculture by intercropping
- 著者・年・どこに: Marc-Olivier Martin-Guay、Alain Paquette、Jérôme Dupras、David Rivest、2018（オンライン 2017）、Science of the Total Environment
- DOI: https://doi.org/10.1016/j.scitotenv.2017.10.024
- 書いてあること: 126 研究・939 観察のメタ解析。同面積の単作に比べて、粗エネルギー +38%、粗収入 +33%、土地 23% 減（LER 1.30）。灌漑や乾燥度は LER に影響しなかった。
- 前提: 施肥・耕起は要旨に記載なし。収入の比較は価格に依る。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-5. The productive performance of intercropping
- 著者・年・どこに: Chunjie Li、T.J. Stomph、David Makowski ほか、2023、PNAS
- DOI: https://doi.org/10.1073/pnas.2201886120
- 書いてあること: 世界のメタ解析。最も収量の高い単作と比べると、混作は平均で穀物・カロリーが約 4% 少ない。タンパク質は同等以上（特にトウモロコシ/マメ科を中程度の N で）。多様な作物を同じ土地で得る目的では、混作が優る。「土地が節約できる」が、必ずしも「一番の単作より多く採れる」ではない、という見方。
- 前提: メタ解析。施肥の水準は説明変数。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-6. Does intercropping enhance yield stability in arable crop production? A meta-analysis
- 著者・年・どこに: Md Raseduzzaman、Erik Steen Jensen、2017、European Journal of Agronomy
- DOI: https://doi.org/10.1016/j.eja.2017.09.009
- 書いてあること: 33 論文。穀類–マメ科の混作の収量変動係数（CV）は 22.1 で、マメ科の単作（31.7）より安定。非穀類の組み合わせより、穀類–マメ科の方が安定。
- 前提: メタ解析。気候帯（熱帯・亜熱帯・温帯）と設計（追加・置換）で分けている。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-7. Yield and fertilizer benefits of maize/grain legume intercropping in China and Africa: A meta-analysis
- 著者・年・どこに: Shingirai Mudare ほか、2022、Agronomy for Sustainable Development
- DOI: https://doi.org/10.1007/s13593-022-00816-1
- 書いてあること: 73 論文。トウモロコシと 6 種のマメ科。LER も N・P の肥料等価比も 1 より大きい（中国・アフリカとも）。増収は中国 2.3 t/ha、アフリカ 0.90 t/ha。中国はリレー・ストリップが最大、アフリカはインゲンとの組み合わせが最大。N・P の施肥を増やすと、効果が下がる方向（要旨の文が切れており、どの指標かは読んでいない）。
- 前提: 中国とアフリカの試験。施肥量は変数。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-8. Intercropping maize and soybean increases efficiency of land and fertilizer nitrogen use; A meta-analysis
- 著者・年・どこに: Zhan Xu、Chunjie Li、Chaochun Zhang、Yang Yu ほか（6名）、2020（オンライン 2019）、Field Crops Research
- DOI: https://doi.org/10.1016/j.fcr.2019.107661
- 書いてあること: 英語 47・中国語 43 の研究。トウモロコシ/ダイズの LER は 1.32±0.02。一方を早く播く・収穫する（リレー）など、時間のずれが大きいほど増える。肥料窒素等価比は 1.44±0.03。
- 前提: 中国語の論文も含む。肥料窒素の節約は、主にトウモロコシの相対収量が高いことと、混作の窒素投入が少ないことによる、と要旨にある。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-9. Improving intercropping: a synthesis of research in agronomy, plant physiology and ecology
- 著者・年・どこに: Rob W. Brooker ほか（22名）、2015（オンライン 2014）、New Phytologist
- DOI: https://doi.org/10.1111/nph.13132
- 書いてあること: 農学・植物生理・生態学の知見を合わせて、混作の設計を良くする方法を論じる総説。低投入・資源の乏しい農業で大事な慣行だとしている。
- 前提: 総説。個々の試験の前提は要旨に記載なし。
- 種類: 二次（総説）
- 読了: 未読

#### A-10. Ecological principles underlying the increase of productivity achieved by cereal-grain legume intercrops in organic farming. A review
- 著者・年・どこに: Laurent Bedoussac、Etienne-Pascal Journet、Henrik Hauggaard-Nielsen ほか（8名）、2015、Agronomy for Sustainable Development
- DOI: https://doi.org/10.1007/s13593-014-0277-7
- 書いてあること: 要旨を取れなかった。題名は、有機農業での穀類–マメ科の混作が生産性を上げる生態学的な原理の総説。
- 前提: 有機農業（題名）。それ以上は記載なし。
- 種類: 二次（総説）
- 読了: 未読

### 混植 2: 窒素・りん・マメ科（組み合わせの原理）

#### A-11. Diversity enhances agricultural productivity via rhizosphere phosphorus facilitation on phosphorus-deficient soils
- 著者・年・どこに: Long Li、Shumin Li、Jianhao Sun ほか、2007、PNAS
- DOI: https://doi.org/10.1073/pnas.0704591104
- 書いてあること: トウモロコシとソラマメの交互条。低りん・高窒素の土壌で、4 年の圃場試験で、トウモロコシ +43%、ソラマメ +26%。根の隔壁を使った試験で、トウモロコシの増収は、ソラマメの根が根圏を酸性化して可動化したりんを取ったことによる。りん肥料が少ない（P2O5 で 75 kg/ha 未満）とき効果があり、多い（112.5 kg/ha 超）と有意でない。
- 前提: 圃場。りん肥料の水準を変えた試験。試験地・耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

#### A-12. Intercropping legumes and cereals increases phosphorus use efficiency; a meta-analysis
- 著者・年・どこに: Tang X、Zhang C、Yu Y、Shen J ほか（6名）、2020、Plant and Soil
- DOI: https://doi.org/10.1007/s11104-020-04768-x
- 書いてあること: 穀類/マメ科の混作で、りん吸収の LER は平均 1.24。同じ収量を得るのに必要なりん肥料は、単作より 21% 少ない。吸収したりんの収量への変換効率は、混作で変わらなかった。
- 前提: メタ解析。投入水準が主題。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-13. Intercropping of grain legumes and cereals improves the use of soil N resources and reduces the requirement for synthetic fertilizer N: A global-scale analysis
- 著者・年・どこに: Erik Steen Jensen、Georg Carlsson、Henrik Hauggaard-Nielsen、2020、Agronomy for Sustainable Development
- DOI: https://doi.org/10.1007/s13593-020-0607-x
- 書いてあること: 単作のマメ科が土壌から取る窒素を世界で約 14.2 Tg N/年と見積もり、世界の合成窒素肥料（109 Tg N/年）の約三分の一に当たる、と置いたうえで、穀類との混作が土壌窒素の使い方を良くする可能性を論じる。結論の数字は要旨の後半にあり、読んでいない。
- 前提: 世界規模の推計（積み上げ計算）。
- 種類: 二次（推計と総説）
- 読了: 未読

#### A-14. Pea–barley intercropping for efficient symbiotic N2-fixation, soil N acquisition and use of other nutrients in European organic cropping systems
- 著者・年・どこに: Henrik Hauggaard-Nielsen、Mike J. Gooding、Per Ambus ほか、2009、Field Crops Research
- DOI: https://doi.org/10.1016/j.fcr.2009.04.009
- 書いてあること: 西欧 5 か国（デンマーク、英国、フランス、ドイツ、イタリア）の有機圃場で 3 作期。エンドウとオオムギを単作・置換・追加の設計で比べ、LER は開花期 1.4、成熟期 1.3。
- 前提: 有機圃場、西欧の温帯。施肥の中身・耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

### 混植 3: 病害虫・雑草

#### A-15. Annual intercropping suppresses weeds: A meta-analysis
- 著者・年・どこに: Chunfeng Gu、L. Bastiaans、Niels P.R. Anten、David Makowski ほか（5名）、2021、Agriculture, Ecosystems & Environment
- DOI: https://doi.org/10.1016/j.agee.2021.107658
- 書いてあること: 39 論文・76 試験・339 記録。混作の雑草量は、雑草を抑えにくい方の単作より 58% 少ない（Rweak=0.42）。抑えやすい方の単作とは有意差なし。
- 前提: 一年生作物の混作。除草や施肥は試験ごとに違う（要旨に記載なし）。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-16. Does plant diversity benefit agroecosystems? A synthetic review
- 著者・年・どこに: Deborah K. Letourneau、Inge Armbrecht、Beatriz Salguero Rivera ほか、2011（オンライン 2010）、Ecological Applications
- DOI: https://doi.org/10.1890/09-2026.1
- 書いてあること: 45 論文・552 実験のメタ解析。植物を多様化した作物では、草食昆虫が減り、天敵が増え、作物の被害が減った。一方、作物の収量には小さな負の効果があった（主作物の密度が、混植で下がるため、と著者）。
- 前提: 多様化の方式（混作、周辺植生など）は混在。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-17. Associational resistance through intercropping reduces yield losses to soil-borne pests and diseases
- 著者・年・どこに: Victoria G.A. Chadfield、Susan E. Hartley、Kelly R. Redeker、2022、New Phytologist
- DOI: https://doi.org/10.1111/nph.18302
- 書いてあること: 混作で、主作物の線虫被害が 40%、土壌病害の発生が 55% 減った。効果は、圃場の施肥状況、混作相手の科、ポットか圃場かで変わる。線虫の抑制は、混作相手の存在による減収を補うのに足りた。
- 前提: メタ解析。施肥状況が変数。
- 種類: 一次（メタ解析）
- 読了: 未読

#### A-18. Organization of a Plant-Arthropod Association in Simple and Diverse Habitats: The Fauna of Collards (Brassica oleracea)
- 著者・年・どこに: Richard B. Root、1973、Ecological Monographs
- DOI: https://doi.org/10.2307/1942161
- 書いてあること: ニューヨーク州イサカで、コラード（アブラナ科）を純粋区と、周囲を多様な草地植生で囲んだ一条植えで育て、3 年、20 回の調査で節足動物を比べた。要旨の結果部分は、ここで読んでいない。
- 前提: 米国温帯の圃場。多様な植生は作物ではなく周囲の草地（混植そのものではない）。
- 種類: 一次
- 読了: 未読

#### A-19. Push–pull technology: a conservation agriculture approach for integrated management of insect pests, weeds and soil health in Africa
- 著者・年・どこに: Zeyaur Rahman Khan、Charles A.O. Midega、Jimmy O. Pittchar ほか、2011、International Journal of Agricultural Sustainability
- DOI: https://doi.org/10.3763/ijas.2010.0558
- 書いてあること: トウモロコシにマメ科のデスモディウムを間作（害虫を遠ざける）し、周囲にナピアグラス（誘引）を植える。デスモディウムの根の分泌物がストライガ（寄生雑草）の発芽を抑える。トウモロコシ収量が 1 t/ha 未満から 3.5 t/ha に増えたとする。東アフリカで 3 万を超える農家が採用。
- 前提: 東アフリカの小規模な穀類–家畜の混合農業。開発した研究者自身による総説。温帯日本の畑に当てはまるかは別。
- 種類: 二次（開発者による総説）
- 読了: 未読

#### A-20. Genetic diversity and disease control in rice
- 著者・年・どこに: Youyong Zhu、Hairu Chen、Jinghua Fan ほか、2000、Nature
- DOI: https://doi.org/10.1038/35021046
- 書いてあること: 中国雲南省で、遺伝的に違う稲品種を混ぜて植えた。1998 年に 5 郷、1999 年に 10 郷の全水田。単作の対照区との差で、病害の程度への効果を見た。結果の数字は要旨の後半で、ここで読んでいない。
- 前提: 同じ作物の品種の混植（種をまたぐ混作ではない）。大規模な農家参加の試験。施肥は記載なし。
- 種類: 一次
- 読了: 未読

### 混植 4: 土壌（炭素・窒素）と生態系サービス

#### A-21. Intercropping enhances soil carbon and nitrogen
- 著者・年・どこに: Wen-Feng Cong、Ellis Hoffland、Long Li、Johan Six ほか（8名）、2015（オンライン 2014）、Global Change Biology
- DOI: https://doi.org/10.1111/gcb.12738
- 書いてあること: ストリップ混作と通常の輪作を 7 年間比べた圃場試験。表層 20 cm の土壌有機炭素が混作で 4%±1%、土壌窒素が 11%±1% 多い。根の量は平均 23% 多い。
- 前提: 圃場 7 年。試験地・施肥・耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

#### A-22. Positive but variable effects of crop diversification on biodiversity and ecosystem services
- 著者・年・どこに: Damien Beillouin、Tamara Ben Ari、Éric Malézieux、Verena Seufert ほか（5名）、2021、Global Change Biology
- DOI: https://doi.org/10.1111/gcb.15747
- 書いてあること: 95 のメタ解析（5156 実験）をまとめた。作物の多様化の効果は、全体に良い方向だが、多様化の種類によってばらつく。混作は多様化の一つ。
- 前提: メタ解析のメタ解析。施肥・耕起は試験ごと。
- 種類: 二次（メタ解析の統合）
- 読了: 未読

### 混植 5: 配置・間隔・順

#### A-23. Yield Response to Different Planting Geometries in Maize–Soybean Relay Strip Intercropping Systems
- 著者・年・どこに: Feng Yang、Xiaochun Wang、Dunping Liao ほか、2014、Agronomy Journal
- DOI: https://doi.org/10.2134/agronj14.0263
- 書いてあること: トウモロコシ 2 条・ダイズ 2 条のリレー・ストリップ。2012〜2013 年の二つの圃場試験で、帯の幅、条間、株間、トウモロコシ列とダイズ列の距離を変えた。LER は 1.3 超。トウモロコシの狭い条間 40 cm、帯幅 200 cm が最適だった。
- 前提: 圃場。試験地・施肥・耕起は要旨に記載なし。リレー（ダイズを後から播く）で、同時播きではない。
- 種類: 一次
- 読了: 未読

#### A-24. Effects of strip width on yields in relay-strip intercropping: A simulation study
- 著者・年・どこに: P.A.J. van Oort、Fang Gou、T.J. Stomph ほか、2020（オンライン 2019）、European Journal of Agronomy
- DOI: https://doi.org/10.1016/j.eja.2019.125936
- 書いてあること: コムギ–トウモロコシのリレー・ストリップで、帯幅の影響をモデルで計算した。最適な帯幅は 1 m 未満、という結果。
- 前提: **シミュレーション**（圃場の実測ではない）。
- 種類: 一次（モデル）
- 読了: 未読

#### A-25. Complementarity in root architecture for nutrient uptake in ancient maize/bean and maize/bean/squash polycultures
- 著者・年・どこに: Johannes Auke Postma、Jonathan Paul Lynch、2012、Annals of Botany
- DOI: https://doi.org/10.1093/aob/mcs082
- 書いてあること: 根の構造のモデル（SimRoot）で、トウモロコシ・インゲン・カボチャを単作と混作で最初の 40 日を計算。低窒素・低りん・低カリの土壌で、根の構造の違いが養分獲得を補い合う。カボチャは低肥沃に最も弱く、インゲンは最も強い。
- 前提: **シミュレーション**。低肥沃な土壌を想定。
- 種類: 一次（モデル）
- 読了: 未読

#### A-26. Root foraging elicits niche complementarity-dependent yield advantage in the ancient 'three sisters' (maize/bean/squash) polyculture
- 著者・年・どこに: Chaochun Zhang、Johannes Auke Postma、Larry M. York ほか、2014、Annals of Botany
- DOI: https://doi.org/10.1093/aob/mcu191
- 書いてあること: 窒素・りんの利用可能性が違う圃場区で、2 作期、三姉妹・トウモロコシ/インゲン・各単作を比較。DNA で根を種別に判別。三姉妹とトウモロコシ/インゲンは、土地当量で単作より収量・バイオマスが多く、選択効果でなく補完効果が主因。トウモロコシは浅く、インゲンは満遍なく、カボチャの根の置き方はりんの量に依る。
- 前提: 圃場、窒素・りんの水準を変えた区。試験地は要旨に記載なし。
- 種類: 一次
- 読了: 未読

### 混植 6: 伝統的な混植

#### A-27. Estimating Productivity of Traditional Iroquoian Cropping Systems from Field Experiments and Historical Literature
- 著者・年・どこに: Jane Mt. Pleasant、Robert F. Burt、2010、Journal of Ethnobiology
- DOI: https://doi.org/10.2993/0278-0771-30.1.52
- 書いてあること: ニューヨーク州の圃場試験で、イロコイの三姉妹（トウモロコシ・豆・カボチャの混植）の収量水準を見積もる。在来の白い粉トウモロコシで 22〜76 bu/acre（1155〜4127 kg/ha）。植栽密度が高く間隔が近いほど収量が高い。歴史文献の見積もりより高い、と主張。
- 前提: 肥沃な土壌と、土壌有機物・栽培方法が収量を決める、という著者の説明。施肥・耕起の詳細は要旨に記載なし。
- 種類: 一次（圃場試験と歴史資料）
- 読了: 未読

#### A-28. Yield, growth, and labor demands of growing maize, beans, and squash in monoculture versus the Three Sisters
- 著者・年・どこに: Ty Cryan、Olivia Musselman、Aaron W. Baumgardner ほか、2024、Plants, People, Planet
- DOI: https://doi.org/10.1002/ppp3.10576
- 書いてあること: カトーバ・インディアン・ネーションと共同で、三姉妹と単作の収量と労働量を比べた。目的（収量を最大にする、土地・種・労力を節約する）によって植え方を選べる、という趣旨。結果の数字は要旨の後半で、ここで読んでいない。
- 前提: 米国（カトーバ・ネーション）の圃場。施肥・耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

#### A-29. Maize intercropping in the milpa system. Diversity, extent and importance for nutritional security in the Western Highlands of Guatemala
- 著者・年・どこに: Santiago López-Ridaura、Luis Barba Escoto、Cristian A. Reyna-Ramírez ほか、2021、Scientific Reports
- DOI: https://doi.org/10.1038/s41598-021-82784-2
- 書いてあること: グアテマラ西部高地の小規模農家 989 世帯の調査。milpa（トウモロコシに、豆、ソラマメ、カボチャ、ジャガイモなどを混ぜる）が、1205 区画の三分の二超。収量が分かる 357 区画で、milpa は単作トウモロコシより総エネルギー収量が高く、必要栄養の充足も良い。
- 前提: **農家の調査**（対照を置いた実験ではない）。高地の小規模農家。施肥・耕起は要旨に記載なし。
- 種類: 一次（調査）
- 読了: 未読

#### A-30. The Ecology of Intercropping
- 著者・年・どこに: John H. Vandermeer、1989、Cambridge University Press（本）
- DOI: https://doi.org/10.1017/cbo9780511623523
- 書いてあること: 要旨を取れなかった。題名のとおり、混作の生態学を扱う本。
- 前提: 本。施肥・耕起は章ごと。
- 種類: 二次（本）
- 読了: 未読

#### A-31. Farmers of Forty Centuries; or, Permanent Agriculture in China, Korea and Japan
- 著者・年・どこに: Franklin Hiram King、1911
- URL: https://doi.org/10.5962/bhl.title.20418（Biodiversity Heritage Library の走査本）
- 書いてあること: 要旨を取れなかった。題名のとおり、中国・朝鮮・日本の農業の記録。混作・間作の記述がどこにあるかは読んでいない。
- 前提: 1911 年刊。施肥・耕起・混作の扱いは記載なし（本文を読んでいない）。
- 種類: 一次（観察記録）
- 読了: 未読

---

## (B) 菌根菌と混植・多様性

混植と菌根菌をつなぐ研究は、温室・ポット・メッシュ室の実験が多く、**圃場で菌ネットワーク経由のりんの移動を測った研究は、ここでは見つけていません**。賛否が分かれる題材なので、批判の側（B-7、B-8、B-9）も入れました。

#### B-1. Mycorrhizal fungal diversity determines plant biodiversity, ecosystem variability and productivity
- 著者・年・どこに: Marcel G.A. van der Heijden、John N. Klironomos、Margot Ursic ほか、1998、Nature
- DOI: https://doi.org/10.1038/23932
- 書いてあること: 要旨を取れなかった。題名は、菌根菌の多様性が、植物の多様性・生態系の変動・生産性を決める、という主張。
- 前提: 記載なし（要旨を読んでいない）。
- 種類: 一次
- 読了: 未読

#### B-2. A meta-analysis of context-dependency in plant response to inoculation with mycorrhizal fungi
- 著者・年・どこに: Jason D. Hoeksema、V. Bala Chaudhary、Catherine A. Gehring ほか、2010、Ecology Letters
- DOI: https://doi.org/10.1111/j.1461-0248.2009.01430.x
- 書いてあること: 菌根菌を接種したときの植物の反応を決める要因（宿主の種類、菌の種類、土壌肥沃度、土壌の生物的な複雑さ、実験室か圃場か）を比べた。多くの場合、宿主の機能群と窒素施肥が、他の要因より予測に効いた。窒素を固定しない草本・木本と C4 のイネ科は、窒素固定菌と共生する植物や C3 のイネ科より、よく反応した。
- 前提: メタ解析。**宿主の組み合わせを考える手がかり**になる。作物の混植を直接扱うものではない。
- 種類: 一次（メタ解析）
- 読了: 未読

#### B-3. Socialism in soil? The importance of mycorrhizal fungal networks for facilitation in natural ecosystems
- 著者・年・どこに: Marcel G.A. van der Heijden、Thomas R. Horton、2009、Journal of Ecology
- DOI: https://doi.org/10.1111/j.1365-2745.2009.01570.x
- 書いてあること: 多くの菌根菌は宿主特異性が低く、一つの菌が多くの植物を繋ぐ。この菌ネットワークが、植物の成長を助け、資源を分け合うかどうかを論じる。
- 前提: **自然生態系**が対象（作物ではない）。
- 種類: 二次（総説）
- 読了: 未読

#### B-4. Mycorrhizal Networks: Common Goods of Plants Shared under Unequal Terms of Trade
- 著者・年・どこに: Florian Walder、Helge Niemann、Natarajan Mathimaran ほか、2012、Plant Physiology
- DOI: https://doi.org/10.1104/pp.112.195727
- 書いてあること: 亜麻（C3）とソルガム（C4）を、菌根菌のネットワークで繋いだ鉢（Glomus intraradices または G. mosseae）で、植物と菌の間の「取引の条件」を見る。題名は、条件が不均等だという趣旨。結果の数字は、ここで読んでいない。
- 前提: 温室のマイクロコズム（鉢）。**宿主の組み合わせ（C3/C4）**の例。
- 種類: 一次
- 読了: 未読

#### B-5. Rate of hyphal spread of arbuscular mycorrhizal fungi from pigeon pea to finger millet and their contribution to plant growth and nutrient uptake in experimental microcosms
- 著者・年・どこに: Lukas Schütz、Krishna Saharan、Paul M. Mäder ほか、2021、Applied Soil Ecology
- DOI: https://doi.org/10.1016/j.apsoil.2021.104156
- 書いてあること: キマメ（マメ科）からシコクビエ（雑穀）へ、菌糸が 5 cm または 12 cm の土の橋を伝わる速さを、3 種の菌根菌で比べた。三種とも、近い距離の鉢ではキマメのバイオマスを 2 倍超にした。菌の種で速さが違う、という仮説の検証。
- 前提: 温室のマイクロコズム。混作の畑ではない。
- 種類: 一次
- 読了: 未読

#### B-6. Phosphorus solubilizing bacteria rather than arbuscular mycorrhizal fungi drive maize/faba bean intercropping advantages
- 著者・年・どこに: Yalin Liu、Chenyu Ma、Prakash Lakshmanan ほか、2024、Plant and Soil
- DOI: https://doi.org/10.1007/s11104-024-07018-6
- 書いてあること: 長期の低りん・高りん施肥の圃場の土壌微生物と、二つのメソコズム実験（トウモロコシ単作、トウモロコシ/ソラマメ混作。AMF を一方の区画に接種）。題名は、混作の利点を生むのは、AMF でなくりん可溶化細菌、という結論。**菌ネットワーク説に対する反対側の例**として挙げる。結論の中身は、要旨の後半で、ここで読んでいない。
- 前提: 長期のりん施肥区（低 P・高 P）の圃場土壌を使う。メソコズムは実験。
- 種類: 一次
- 読了: 未読

#### B-7. Positive citation bias and overinterpreted results lead to misinformation on common mycorrhizal networks in forests
- 著者・年・どこに: Justine Karst、Melanie D. Jones、Jason D. Hoeksema、2023、Nature Ecology & Evolution
- DOI: https://doi.org/10.1038/s41559-023-01986-1
- 書いてあること: 森林の共通菌根ネットワーク（CMN）についての主張を検証し、CMN が森林に広く存在する、資源が移って実生が良くなる、という主張の根拠は不十分で、肯定的な結果が偏って引用されている、と指摘する。
- 前提: **森林**が対象（作物ではない）。ただし、「ネットワークがある」と言うときの証拠の水準を知る材料。
- 種類: 二次（批判的総説）
- 読了: 未読

#### B-8. Little evidence that farmers should consider abundance or diversity of arbuscular mycorrhizal fungi when managing crops
- 著者・年・どこに: Megan H. Ryan、James H. Graham、2018、New Phytologist
- DOI: https://doi.org/10.1111/nph.15308
- 書いてあること: 土着の AMF の定着を操作して収量を報告した圃場試験と、AMF の群集構造・多様性を調べた試験を対象に、文献は AMF の利益を楽観的に見すぎている、とする。
- 前提: 批判的総説。後続の Rillig らの応答（B-9）が、コムギ中心の議論だと指摘している。
- 種類: 二次（批判的総説）
- 読了: 未読

#### B-9. Why farmers should manage the arbuscular mycorrhizal symbiosis
- 著者・年・どこに: Matthias C. Rillig、Carlos A. Aguilar-Trigueros、Tessa Camenzind ほか、2019、New Phytologist
- DOI: https://doi.org/10.1111/nph.15602
- 書いてあること: B-8 への応答の短い論考。B-8 は大規模な工業的農業、特にコムギに焦点を当てた、批判的な見方だと述べ、いくつかの点には同意している。
- 前提: 論考（実験ではない）。B-8 とセットで読む。
- 種類: 二次（論考）
- 読了: 未読

#### B-10. In situ mycorrhizal function – knowledge gaps and future directions
- 著者・年・どこに: Ylva Lekberg、Thorunn Helgason、2018、New Phytologist
- DOI: https://doi.org/10.1111/nph.15064
- 書いてあること: 過去 30 年の New Phytologist の菌根機能の論文を調べ、機能の研究の多くが制御条件の下で、圃場での実際の働きはほとんど分かっていない、とする。
- 前提: 文献調査と論考。
- 種類: 二次（論考）
- 読了: 未読

---

## (C) リジェネラティブ農業の総説と長期試験

リジェネラティブ農業には、法的な定義も、広く認められた定義もありません（C-1）。批判的な総説（C-2）を先に読むと、後の論文の位置が分かります。

#### C-1. What Is Regenerative Agriculture? A Review of Scholar and Practitioner Definitions Based on Processes and Outcomes
- 著者・年・どこに: Peter Newton、Nicole Civita、Lee Frankel-Goldwater ほか、2020、Frontiers in Sustainable Food Systems
- DOI: https://doi.org/10.3389/fsufs.2020.577723
- 書いてあること: リジェネラティブ農業の法的・規制上の定義も、広く認められた定義も無い、と述べ、学者と実践者の定義を、手法と成果で整理する。
- 前提: 定義の文献調査。
- 種類: 二次（総説）
- 読了: 未読

#### C-2. Regenerative Agriculture: An agronomic perspective
- 著者・年・どこに: K.E. Giller、Renske Hijbeek、Jens Andersson ほか、2021、Outlook on Agriculture
- DOI: https://doi.org/10.1177/0030727021998063
- 書いてあること: 農学の立場からの批判的な検討。残渣の保持、カバークロップ、不耕起は「よい農業慣行」の中心にあるが、パーマカルチャーや計画放牧などは争いがあり、いずれも文脈を考えずに推奨されている、と問題にする。
- 前提: 論考。**この手引きの立ち位置への反論として読む価値がある**資料。
- 種類: 二次（批判的論考）
- 読了: 未読

#### C-3. Regenerative Agriculture — A Literature Review on the Practices and Mechanisms Used to Improve Soil Health
- 著者・年・どこに: Ravjit K. Khangura、David Ferris、Cameron Wagg ほか、2023、Sustainability
- DOI: https://doi.org/10.3390/su15032338
- 書いてあること: 最小耕起、残渣保持、カバークロップなどが、土壌炭素・収量・土壌の健全さを、ある気候帯と土壌では良くする、と文献は示す。実践の採用が進まない理由として、利益の実証が足りないことを挙げる。
- 前提: 文献調査。気候帯・土壌による。
- 種類: 二次（総説）
- 読了: 未読

#### C-4. Soil health and nutrient density: preliminary comparison of regenerative and conventional farming
- 著者・年・どこに: David R. Montgomery、Anne Biklé、Ray Archuleta ほか、2022、PeerJ
- DOI: https://doi.org/10.7717/peerj.12848
- 書いてあること: 米国の対になる農場（5〜10 年）で、慣行（合成肥料と除草剤）とリジェネラティブ（不耕起、カバークロップ、多様な輪作）を比べた。リジェネラティブの畑で、土壌有機物、土壌の健全さの点数、一部のビタミン・ミネラル・植物成分が高い。
- 前提: 対になった農場の比較で、題名と要旨は「予備的」と書く。米国。農場ごとの条件の違いは要旨に記載なし。
- 種類: 一次（観察的な比較）
- 読了: 未読

#### C-5. Limited potential of no-till agriculture for climate change mitigation
- 著者・年・どこに: D.S. Powlson、Clare Maeve Stirling、Mangi Lal Jat ほか、2014、Nature Climate Change
- DOI: https://doi.org/10.1038/nclimate2292
- 書いてあること: 要旨を取れなかった。題名は、不耕起による気候変動の緩和の可能性は限られる、という主張。
- 前提: 論考。
- 種類: 二次（論考）
- 読了: 未読

#### C-6. Increasing Cropping System Diversity Balances Productivity, Profitability and Environmental Health
- 著者・年・どこに: Adam Samuel Davis、Jason Hill、Craig A. Chase ほか、2012、PLoS ONE
- DOI: https://doi.org/10.1371/journal.pone.0047149
- 書いてあること: アイオワ州で 2003〜2011 年の圃場試験。慣行の 2 年輪作（トウモロコシ–ダイズ、施肥・除草剤は近隣農家並み）と、3 年・4 年の多様な輪作（小麦類＋赤クローバー、アルファルファ）を比べる。後者は合成窒素と除草剤を減らし、牛糞を時々入れた。結果の数字は要旨の後半で、ここで読んでいない。
- 前提: 輪作の多様化（**混植ではない**）。施肥・除草剤は減らしたが、ゼロではない。米国中西部。
- 種類: 一次（長期試験）
- 読了: 未読

#### C-7. Soil Fertility and Biodiversity in Organic Farming
- 著者・年・どこに: Paul Mäder、Andreas Fließbach、David Dubois ほか、2002、Science
- DOI: https://doi.org/10.1126/science.1071148
- 書いてあること: 中央ヨーロッパで 21 年間、生物動態、バイオ有機、慣行の農法を比べた試験。有機は収量が 20% 低いが、肥料とエネルギーの投入が 34〜53%、農薬が 97% 少ない。有機の区で土壌肥沃度と生物多様性が高い。
- 前提: 中央ヨーロッパの 21 年。要旨は混植の試験とは書いていない（農法の比較）。施肥・耕起の中身は要旨に記載なし。
- 種類: 一次（長期試験）
- 読了: 未読

---

## (D) 日本語の資料と、日本で取られた資料（批判的に読む）

どれも、**施肥・耕起・単作や慣行の栽培を前提**にした試験の中での、混植・間作・リビングマルチです。無施肥・不耕起・混植の畑に、そのまま当てはまるとは限りません。値（%減、収量）を `data` 行に写すときは、その前提を一行添えます。

#### D-1. 混作や間作を利用したキャベツ、ブロッコリーの有機栽培
- 著者・年・どこに: 赤池一彦、山梨県総合農業技術センター 成果情報（研究期間 2007〜2009 年度。刊行年は資料から読めなかった）
- URL: https://www.pref.yamanashi.jp/documents/31524/konsakukansakuyuukisaibai_1.pdf
- 書いてあること: 平坦地で春キャベツ・秋ブロッコリーを有機栽培するとき、畦間を白クローバや雑草で間作すると、チョウ目害虫やアブラムシの被害が減り、可販株率が上がる（2008 年の春キャベツで白クローバ 66.7%、裸地 0%）。ネギ類やレタスと混作するとさらに減る。レタスとは株ごとの交互植えが、畦ごとより虫害が少ない。
- 前提: 有機栽培。畦幅 120 cm・株間 40 cm の 2 条植え、ネギ類は株間 15 cm の 4 条植え。白クローバは畦間に 5 g/10 m を散播し、刈り込む。補完として BT 水和剤を散布した区がある。「可販株率」は虫害が無い株の割合で、販売の基準そのものではない。施肥・耕起は読んだ範囲で記載なし。1〜2 年の試験。
- 種類: 一次（公的機関の成果情報。査読はない）
- 読了: 未読

#### D-2. Insect Pests Damage Reduction on Organic Farming of Cabbage using Mixed Cropping, Intercropping, and Weed Sod-Culture: Field Studies and Empirical Research in Yamanashi Prefecture, Japan
- 著者・年・どこに: Kazuhiko Akaike、2018、日本応用動物昆虫学会誌（Japanese Journal of Applied Entomology and Zoology）
- DOI: https://doi.org/10.1303/jjaez.2018.149
- 書いてあること: 題名のとおり、山梨県の有機キャベツの混作・間作・草生栽培による害虫被害の軽減（圃場試験と実地の調べ）。要旨は日本語で、「畦間の雑草草生やシロクローバの間作」の試験の説明から始まる。これ以上は読んでいない。D-1 の論文版かどうかは確かめていない。
- 前提: 有機栽培、山梨県。施肥・耕起は記載なし。
- 種類: 一次（査読誌）
- 読了: 未読

#### D-3. リビングマルチによる害虫防除（露地野菜）の研究成果
- 著者・年・どこに: 上杉龍士、農研機構 東北農業研究センター、2024-03-01（令和 5 年度東北地域みどりの食料システム戦略推進 Web セミナーの講演資料）
- URL: https://www.maff.go.jp/tohoku/seisan/midori_seminar/attach/pdf/240301-61.pdf
- 書いてあること: 露地野菜（キャベツ・ブロッコリー・ネギ・タマネギ）の畝間にオオムギ（＋ソバの混播）を間作して、天敵を増やし、害虫を減らす。図で、害虫数が間作なしより少ないことが示される（数値は図の読み取りになるので、ここには書かない）。畝間のオオムギは無施肥でも害虫抑制効果は変わらない。オオムギの播種量は 5 kg/10 a で効果が最大、1 kg/10 a でも効果あり。
- 前提: 慣行の露地野菜の畝への施肥は畝内に局所施用。ビニール（生分解）マルチを使う例がある。図に「化学農薬（散布回数減）」「有機 JAS」の語があるが、何と何を比べた図かは読み切れていない。市販のオオムギ種子には種子処理剤が付いているので、有機栽培では注意、とある。北日本。耕起は読んだ範囲で記載なし。講演スライド（元の試験は日独の共同研究）。
- 種類: 二次（講演資料）
- 読了: 未読

#### D-4. Effects of wheat undersowing and sweet alyssum intercropping on aphid and flea beetle infestation in white cabbage in Germany and Japan
- 著者・年・どこに: Anna Köneke、Ryuji Uesugi、Annette Herz ほか、2023、Journal of Plant Diseases and Protection
- DOI: https://doi.org/10.1007/s41348-023-00730-y
- 書いてあること: キャベツにコムギを後から播く（undersowing）と、モモアカアブラムシは減ったが、ニセダイコンアブラムシ（Brevicoryne brassicae）は減らなかった。天敵の発生は、いずれの併植でも有意に変わらなかった。スイートアリッサムの併植は、ドイツでヒラタアブの成虫を増やしたが、日本の試験地では増えず、ノミハムシの被害は有意に増やした。
- 前提: ドイツと日本の圃場。施肥・耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

#### D-5. トウモロコシとダイズの混作が乾燥ストレス軽減と生産性向上に寄与する
- 著者・年・どこに: 国際農林水産業研究センター（JIRCAS）、平成 26 年（2014）研究成果情報 A5
- URL: https://www.jircas.go.jp/sites/default/files/seika/2014/2014_A05_A4_ja.pdf
- 書いてあること: モザンビーク北部の天水畑作地域で、トウモロコシ 2 畝（畝幅 80 cm、株間 20 cm）とダイズ 3 畝（畝幅 40 cm、株間 20 cm）を交互に配置。単作に対する LER は 1.15〜1.49。乾燥ストレスがあるとき、またはトウモロコシへの窒素施肥が少ないときに効果が大きい。
- 前提: **モザンビーク**（日本ではない）。試験地 3 か所（標高 372〜1397 m）、n=4。トウモロコシに尿素を 0・3・8 g N/m² 側条施肥、ダイズは無施肥。耕起は記載なし。窒素を増やすとダイズの相対収量と LER が下がる傾向（湿潤な 2 か所）。
- 種類: 一次（公的機関の成果情報。査読はない）
- 読了: 未読

#### D-6. リビングマルチを利用した畑作物生産に関する栽培学的研究
- 著者・年・どこに: Shigenori Miura（漢字は確かめていない）、農研機構の機関リポジトリ（年は記載なし。学位論文に相当すると思われるが未確認）
- DOI: https://doi.org/10.24514/00001230
- 書いてあること: 日本の畑作でリビングマルチ（作物と一緒に、または前に播く被覆作物）が実用になるかを調べた。スイートコーン–白クローバと、ダイズ–冬オオムギで、除草剤なしでも雑草抑制効果が高く、主作物の生産への影響は大きくない。主作物とリビングマルチの窒素の競合が小さいことが一因。
- 前提: 日本の畑作。施肥量・耕起の有無は要旨に記載なし。
- 種類: 一次（学位論文相当と思われる）
- 読了: 未読

#### D-7. Suppression of spinach Fusarium wilt by intercropping with Allium plants（ネギおよびニラの混植によるホウレンソウ萎凋病の抑制）
- 著者・年・どこに: Chikako Igarashi、Yuji Asano、Tomoki Nishioka ほか、2017、日本植物病理学会報
- DOI: https://doi.org/10.3186/jjphytopath.83.87
- 書いてあること: 夏ホウレンソウの萎凋病を、ネギ・ニラの混植で抑えられるかを調べた。プラントボックス試験で、両方に高い効果。コンテナ試験で、ネギの混植は株間によらず、ニラは株間 10 cm のときだけ有意に発病を抑えた。ネギの混植の方が効果が高かった。現地圃場（土壌くん蒸後の雨よけハウス、畝肩に 10 cm 間隔）でも検証した。著者らは、ネギの混植の方が実用性が高いと考えた。
- 前提: ポット・コンテナ・雨よけハウス。**現地圃場は土壌くん蒸消毒後**で、無農薬・無消毒の畑とは前提が違う。施肥は記載なし。
- 種類: 一次（査読誌）
- 読了: 未読

#### D-8. Microbial basis of Fusarium wilt suppression by Allium cultivation
- 著者・年・どこに: Tomoki Nishioka、Malek Marian、Issei Kobayashi ほか、2019、Scientific Reports
- DOI: https://doi.org/10.1038/s41598-018-37559-7
- 書いてあること: ネギ・タマネギを作った土は、キュウリ萎凋病菌の増殖を抑える。この効果は 60 °C の加熱で消え、抗菌剤の添加でも消えた。ネギの根圏にフラボバクテリウム属が集まり、キュウリ萎凋病を抑えた。ネギの根の抽出物の効果は 40 °C で消えた。
- 前提: 土壌と植物の室内・ポット試験。試験地・所属は要旨に記載なし（著者が D-7 と重なる）。混植でなく、ネギを作った後の土（輪作の効果）が主。
- 種類: 一次
- 読了: 未読

#### D-9. Maintenance of soybean yield with reduced phosphorus application by previous cropping with mycorrhizal plants
- 著者・年・どこに: Norikuni Oka、唐澤敏彦（Karasawa T）、Keiki Okazaki ほか、2010、Soil Science and Plant Nutrition
- DOI: https://doi.org/10.1111/j.1747-0765.2010.00518.x
- 書いてあること: 三つの圃場試験。前作が菌根菌の宿主植物（コムギ、ヒマワリ、ベッチ、トウモロコシ、アズキ）だと、非宿主（ダイコン、シロガラシ、テンサイ、ソバ）や休閑の後より、ダイズの菌根定着、りん吸収、生育、収量が増える。宿主の後は、りん施肥を北海道の推奨（150 kg P2O5/ha）から 50 kg に減らしても、ダイズ収量が落ちなかった。
- 前提: **りん肥料を 0〜200 kg P2O5/ha の水準で入れる試験**で、無施肥の畑ではない。北海道。前作の組み合わせ（輪作）で、同じ畑での混植ではない。耕起は要旨に記載なし。
- 種類: 一次
- 読了: 未読

#### D-10. Can phosphorus application and cover cropping alter arbuscular mycorrhizal fungal communities and soybean performance after a five-year phosphorus-unfertilized crop rotational system?
- 著者・年・どこに: Masao Higo、Ryohei Sato、Ayu Serizawa ほか、2018、PeerJ
- DOI: https://doi.org/10.7717/peerj.4606
- 書いてあること: 5 年間りん無施肥の輪作を続けた畑で、りん施肥とカバークロップが、ダイズの AMF 定着・群集・生育に与える影響を見た。りん施肥で根の定着の増加は小さく、カバークロップはダイズの地上部とりん吸収に影響せず、りん施肥は 2015 年にダイズのりん吸収・バイオマス・収量を増やした。
- 前提: **りん無施肥を 5 年続けた圃場**に、りん施肥の有無を重ねる設計。試験地は要旨に記載なし。耕起は記載なし。
- 種類: 一次
- 読了: 未読

#### D-11. Cover cropping can be a stronger determinant than host crop identity for arbuscular mycorrhizal fungal communities colonizing maize and soybean
- 著者・年・どこに: Masao Higo、Yuya Tatewaki、Kento Gunji ほか、2019、PeerJ
- DOI: https://doi.org/10.7717/peerj.6403
- 書いてあること: イタリアンライグラス、ヘアリーベッチ、カラシナのカバークロップ、または裸地休閑の後に、トウモロコシとダイズを植え、根の AMF 群集がカバークロップと後作の宿主のどちらで決まるかを見た。題名は、カバークロップの方が強い決定要因になり得る、という結論。
- 前提: 圃場。試験地・施肥・耕起は要旨に記載なし。混植ではなく、カバークロップ→後作の関係。
- 種類: 一次
- 読了: 未読


## (E) 元田んぼの硬盤層（鋤床層・耕盤）と排水、深い根の緑肥 — 候補、全部未読

2026-11-02 に Web 検索で見つけた物。URL は検索結果のまま。本人が開いて、題名・著者・年を確かめ、読んだ物だけ
`sources.md` に移す。どれも大豆・麦の転換畑のための資料で、耕起と施肥を前提にしている（02、09 の注意）。

| # | 題名（検索結果の見出し） | 出所 | URL | 読了 |
|---|---|---|---|---|
| E1 | 大豆セミナー資料: 排水対策から播種まで（中日本農業研究センター 転換畑研究領域、大野智史） | 関東農政局 / 農研機構 | https://www.maff.go.jp/kanto/seisan/nousan/daizu/seminar/attach/pdf/220218-3.pdf | 未読 |
| E2 | 「カットシリーズ」の営農排水技術（心土破砕・弾丸暗渠の限界と、70 cm 深までの通水空洞） | 東北農政局 大豆研究会 | https://www.maff.go.jp/tohoku/seisan/daizu/kyougikai/symposium/attach/pdf/R802-5.pdf | 未読 |
| E3 | 耕盤破砕の亀裂に頼らず、明確な水の通り道を作る考え方 | 関東農政局 大豆セミナー | https://www.maff.go.jp/kanto/seisan/nousan/daizu/seminar/attach/pdf/221208-2.pdf | 未読 |
| E4 | 湿害対策の手引書（水田転換畑の排水不良の原因、対策の手順、地下排水） | 長野県 諏訪地域 | https://www.pref.nagano.lg.jp/suwachi/nosei-aec/gijyutsu/documents/r7shitsugai_all.pdf | 未読 |
| E5 | 総合的な排水対策（飽和透水係数に応じた表面排水・作土・下層土の改良） | 北海道立総合研究機構 | https://www.hro.or.jp/upload/13676/1-4.pdf | 未読 |
| E6 | 水田転換畑の鋤床層と排水不良。サブソイラは耕盤を壊して後作水稲の漏水を招くことがある | 福岡県農林業総合試験場 研究報告 | https://www.farc.pref.fukuoka.jp/farc/kenpo/nourinkenpo-3/03-02.pdf | 未読 |
| E7 | 水田転換畑での緑肥混播の実証（ソルガム、クロタラリア） | 福岡県（JATAFF 稲作） | https://www.jataff.or.jp/project/inasaku/pdf/27_3-5_R7.pdf | 未読 |
| E8 | 深根性緑肥（セスバニア、クロタラリア）と硬盤層の破砕（プラソイラ）の比較。修士論文要旨 2009 | 北海道大学 農学院 | https://www.agr.hokudai.ac.jp/gs/master/2009/09034303.pdf | 未読 |
| E9 | 天水田の硬盤層と根の貫通能力（深根性の形質）。学位論文要旨 | 名古屋大学 | https://nagoya.repo.nii.ac.jp/record/25400/files/k12196_summary.pdf | 未読 |

見つからなかった物: シルト質埴土の硬盤層を緑肥の根だけで割れたかを、貫入抵抗の数字で示した資料。サブソイラの
作業受託の料金の公の資料（本人が JA と近所で聞く）。

## (F) 協生農法（Synecoculture。舩橋真俊、ソニーCSL）— 候補、全部未読

2026-11-04 に作者の問い「協生農法の理論は入れていますか」から。入れていなかった。Claude が Web 検索で見つけ、書誌は NDL と出版社のページで照合した（本文は読んでいない）。
協生農法は、無耕起・無施肥・無農薬で、多様な有用植物を密生して混植し、生態系の自己組織化で生産する農法で、提唱者は福岡正信の自然農法を出発点の一つに置いている（Claude の知識）。
seed の手引きは「混植の案は、混植の一次資料が `sources.md` に入るまで書かない」（04 章）。協生農法の資料は、その**混植の一次資料の候補**に当たる。
読むときの注意: マニュアルは実践の手引きで、収量の数字や比較試験は別の論文にある。アフリカ（ブルキナファソ）の試験は気候も土も徳島と違う。日本の元田んぼの粘土質で試した記録があるかは、読んで確かめる。

| # | 題名 | 著者・出所 | 年 | URL | 一次か | 読了 |
|---|---|---|---|---|---|---|
| F1 | 協生農法実践マニュアル 2016 年度版（53 p。家庭菜園・地産地消の規模の栽培法。英語版 Synecoculture Manual、仏語版もある） | 舩橋真俊 編著、大塚隆 監修、ソニーコンピュータサイエンス研究所（NDL の書誌 R100000002-I028135003） | 2016 | https://sonycsl.co.jp/news/3802/ （PDF は https://www.sonycsl.co.jp/wp-content/uploads/2020/08/6d65e3a58b7ae6bf608240baf2f1abbb.pdf 。2016 年度版と同じかは本人が確かめる） | 二次（手引き） | 未読 |
| F2 | Human augmentation of ecosystems: objectives for food production and science by 2045（展望論文。食料生産の仕組みの作り直しと、生態系の人為的な拡張の目標） | Funabashi M. npj Science of Food 2(16) | 2018 | https://www.nature.com/articles/s41538-018-0026-4 | 二次（展望） | 未読 |
| F3 | Synecoculture experiments: Human augmentation of ecosystems and Planetary Health（日本とサハラ以南アフリカの圃場試験。著者らの要約では、自己組織化した一次生産が慣行の単作より良い点があったとする） | Funabashi M. ほか. Science Talks | 2025 | https://www.sonycsl.co.jp/?p=23928 （本文の誌面の URL は本人が確かめる） | 一次（試験） | 未読 |

**見つからなかった物。** 協生農法を日本の水田転換畑（粘土質、硬盤層）で試した報告。第三者（提唱者と別の研究者）による収量・土壌の比較。

## (G) パーマカルチャー — 候補、全部未読

2026-11-04 に作者「パーマカルチャーも重要ですね」から。入れていなかった。パーマカルチャーは、農法というより**設計の考え方**（土地の中で、水・光・物・人の動きを見て、要素を配置する。帯（ゾーン）、重ね、縁、循環）で、
seed では 07 章（周りの物）、09 章（計画の配置）、「その次」（暮らしと仕事の設計）に関わる。提唱者のモリソンは福岡正信を影響の一つに挙げている（Claude の知識）。
注意: 学術の側の総説は、パーマカルチャーの研究は肯定的な報告に偏り、厳密な比較試験が少ないと指摘している（G4、G5）。原理の本と、試験の論文を分けて読む。

| # | 題名 | 著者・出所 | 年 | URL | 一次か | 読了 |
|---|---|---|---|---|---|---|
| G1 | Permaculture One: A Perennial Agriculture for Human Settlements（最初の本） | Mollison B., Holmgren D. Transworld / Tagari | 1978 | 書誌は Claude の記憶。本人が図書館の目録で確かめる | 二次（原理） | 未読 |
| G2 | Permaculture: A Designers' Manual（設計の本。日本語訳『パーマカルチャー 農的暮らしの永久デザイン』農山漁村文化協会 1993 と Claude は記憶しているが、**検索では確かめられなかった**。NDL で確かめる） | Mollison B. Tagari | 1988 | 書誌は本人が確かめる | 二次（原理） | 未読 |
| G3 | Permaculture: Principles and Pathways Beyond Sustainability（12 の原理）。日本語の要約 PDF「要約 パーマカルチャー」（坪井真一 訳、改訂版）がある | Holmgren D. Holmgren Design Services | 2002（要約の改訂版は 19 年後） | https://files.permacultureprinciples.com/downloads/Essence_of_Pc_JP.pdf | 二次（原理） | 未読 |
| G4 | Permaculture for agroecology: design, movement, practice, and worldview. A review（科学の文献の計量と主題の検討。パーマカルチャーは注目の割に研究から孤立し、実践の記述は難しさとリスクを過小に書く、と） | Ferguson R.S., Lovell S.T. Agronomy for Sustainable Development 34(2): 251–274. DOI 10.1007/s13593-013-0181-6 | 2014 | https://doi.org/10.1007/s13593-013-0181-6 | 二次（総説） | 未読 |
| G5 | Permaculture—Scientific Evidence of Principles for the Agroecological Design of Farming Systems（ホルムグレンの 12 原理それぞれに科学の裏付けを当てた総説） | Krebs J., Bach S. Sustainability 10(9): 3218. DOI 10.3390/su10093218 | 2018 | https://doi.org/10.3390/su10093218 | 二次（総説） | 未読 |

**見つからなかった物。** 日本の水田転換畑でパーマカルチャーの設計を試して収量や土を測った報告。G1・G2 の日本語訳の正確な書誌。

