# 履歴の中の本物の座標を消す（11-06）

最初のコミットから、畑の本物の座標が履歴に入っている（11-05 に tracked の文書は見本 34.0512, 134.2534 に置き換え済み。履歴と GitHub の origin/main には残る）。ここの三つで履歴を書き換える。背景は `docs/deb2 の配備.md` §0-0「履歴の中の本物の座標」。

**本物の値は作者だけが `~/座標の置き換え.txt` を開いて見る。** 三つの道具は値を標準出力に出さない（件数と、ファイルの道と、桁の数だけ）。表は repo の外、権限 600。Claude には値を書かせない、読ませない。

## 作者が打つ順（debpc、dev のアカウントで。全部 `cd /home/dev/dev/seed` から）

0. git-filter-repo を入れる（網が要る）

   ```bash
   .venv/bin/pip install git-filter-repo
   ```

   作業中の worktree（`.claude/worktrees/*`）は古いハッシュを指すので、先に消しておく（必要なら 4 の後に作り直す）:

   ```bash
   git worktree list && git worktree remove --force .claude/worktrees/<名前>
   ```

1. 表を作る（値は `~/座標の置き換え.txt` にだけ。出力は件数）

   ```bash
   .venv/bin/python scripts/座標の履歴/1-表を作る.py
   ```

   - 範囲: 緯度 33.9〜34.3、経度 134.0〜134.6、小数 2 桁以上。見本（34.0512・134.2534）と渕名の点（34.0193・134.1248、公の地質図）とそれらを短くした形は除く。
   - 今の HEAD の木にもある値は既定で表に入れない（11-05 の置き換えの後に残る値は見本の周りの点）。このため HEAD の中身は変わらず、テストもそのまま通る。HEAD に本物が残っていないかは作者が `--include-head` で比べる。
   - 候補が 20 種以上なら止まる。どこから出ているかは `--where`（道と、種の数と、小数の桁だけ）。
   - 作者は表を開いて、本物でない行を消してよい。緯度は緯度の見本へ、経度は経度の見本へ置き換える形（`regex:(?<![\d.])値(?![\d]|\.\d)==>見本`。前後に数字が続く物は巻き込まない）。

2. 書き換える

   ```bash
   scripts/座標の履歴/2-書き換える.sh
   ```

   - 書き換える前の履歴を `~/seed-書き換え前.bundle` に取る（本物を含む。確かめた後に作者が消す）。`backup-before-filter` の枝も作るが、filter-repo は**この枝も一緒に書き換える**ので、控えになるのは bundle の方（偽の repo で確かめた）。
   - `git-filter-repo --replace-text 表 --replace-message 表 --force`（中身とコミットのメッセージの両方）。
   - filter-repo が外す `origin` を `git@github.com:aiseed-dev/seed.git` で戻す。
   - 表の左辺ごとに、まだ値が出てくるコミットの数を出す（値は出さない）。全部 0 でなければ止まる。

3. 文書の中の古いコミット番号を直す

   ```bash
   .venv/bin/python scripts/座標の履歴/3-ハッシュを直す.py          # 先に --dry-run で見てもよい
   ```

   `.git/filter-repo/commit-map` を読み、README・docs・skill・scripts・tests・deploy の中の 7 桁以上の 16 進で旧ハッシュの頭と一致する物を、新ハッシュの同じ桁数に書き換える（台本の `git show --stat …`、配備 §0-0 の最初のコミット、引き継ぎのコミット番号の類）。書き換えた箇所（ファイル:行、旧 → 新）を出す。作業木を書き換えるだけなので、見てからコミットする。

4. 全部のテスト

   ```bash
   .venv/bin/python -m pytest -q
   ```

5. GitHub に出す（全部のコミットの番号が変わる。ほかに clone は無い前提）

   ```bash
   git push --force-with-lease origin main
   ```

   filter-repo の後は origin/main の追跡も消えているので、`--force-with-lease` が「期待する値が無い」と断る時は `git fetch origin` の後にもう一度（fetch で古い履歴が手元に戻るが、push で上書きされる）。

6. GitHub に古いコミットが残りうる（PR、fork、キャッシュ、古いハッシュの直のリンク）。GitHub Support に「sensitive data removal」の依頼を出す（https://support.github.com/ 、repo の名前と、消した事を書く。値は書かない）。公開前なら fork は無い。

7. 片付け: 確かめた後に `~/座標の置き換え.txt` と `~/seed-書き換え前.bundle` と `backup-before-filter` の枝を消す。worktree は今の main から作り直す。deb2 などに clone がある時は、古い clone を捨てて clone し直す（pull すると古い履歴と混ざる）。

## 試験

偽の repo（偽の座標 35.1234・135.5678 を 3 コミットに入れ、文書に `git show --stat <hash>` を書いた物）で 1〜3 を通した。1 は `--repo PATH --out PATH --lat-range 35.0 35.3 --lon-range 135.4 135.7` で、2 は `2-書き換える.sh REPO 表 控え` と `FILTER_PY=… ORIGIN_URL=…` で本物の home に触らずに走る。
