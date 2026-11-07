# SPDX-License-Identifier: AGPL-3.0-or-later
"""上限（設計書 §7.3）。1 日の回数（token、IP、全体）と、usage から概算した 1 日の費用。
もう一つ、門で間違えた回数（番地ごと、分の単位。Tries）。

メモリ上の辞書だけで持ち、日付が変われば消す（Tries は時が過ぎれば消す。再起動でも消える）。token はハッシュ（sha256 の先頭 16 桁）で持つ。
写真と座標は、ここには一切入らない。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import threading
import time
from collections import Counter, OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field

# 写真（1 回に送れる枚数、1 枚、合計の大きさ）
PHOTOS_MAX = 6
PHOTO_MAX = 2 * 1024 * 1024
PHOTOS_TOTAL_MAX = 8 * 1024 * 1024
CONNECT_PER_IP = 5  # token 無しの一言
# 門で間違えた回数（Tries）の既定。SEED_GATE_TRIES、SEED_GATE_WINDOW、SEED_GATE_BLOCK（秒）で変えられる
GATE_TRIES = 10  # GATE_WINDOW 秒の中でこの回数を間違えた番地を止める
GATE_WINDOW = 600
GATE_BLOCK = 600  # 止める長さ。止めている間は正しいコードでも断る
GATE_KEEP = 10_000  # 覚えておく番地の数。超えたら古い物から捨てる（メモリが大きくならないように）
# 100 万トークンあたりの US$。Opus 5.5 の値（設計書 §7.3）。ほかのモデルでも上限の目安としてこれを使う
PRICE_PER_M = {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def cost_usd(usage: dict) -> float:
    """usage（input_tokens など）から費用を概算する。"""
    return (
        (usage.get("input_tokens") or 0) * PRICE_PER_M["input"]
        + (usage.get("output_tokens") or 0) * PRICE_PER_M["output"]
        + (usage.get("cache_read_input_tokens") or 0) * PRICE_PER_M["cache_read"]
        + (usage.get("cache_creation_input_tokens") or 0) * PRICE_PER_M["cache_write"]
    ) / 1_000_000


class LimitReached(Exception):
    """今日はここまで。理由の種類（token / ip / daily / budget）を持つ。"""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


@dataclass
class Limits:
    daily_reads: int
    per_token_reads: int
    per_ip_reads: int
    daily_usd: float
    daily_talks: int = 0  # 話す（/api/talk）の 1 日の回数。0 ならこの口は閉じる
    per_token_talks: int = 0  # 話すの、相手（招待コードか token）ごとの 1 日の回数
    day: str = ""
    by_token: Counter = field(default_factory=Counter)
    by_ip: Counter = field(default_factory=Counter)
    lookups_by_ip: Counter = field(default_factory=Counter)
    connects_by_ip: Counter = field(default_factory=Counter)
    talks_by: Counter = field(default_factory=Counter)
    reads: int = 0
    talks: int = 0
    spent_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @staticmethod
    def today() -> str:
        return dt.date.today().isoformat()

    def _roll(self) -> None:
        d = self.today()
        if d != self.day:
            self.day = d
            self.by_token.clear()
            self.by_ip.clear()
            self.lookups_by_ip.clear()
            self.connects_by_ip.clear()
            self.talks_by.clear()
            self.reads = 0
            self.talks = 0
            self.spent_usd = 0.0

    def take(self, token: str, ip: str) -> None:
        """一回の読みを数える。上限なら LimitReached。数えるのは呼ぶ前（失敗しても一回）。"""
        h = token_hash(token)
        with self._lock:
            self._roll()
            if self.reads >= self.daily_reads:
                raise LimitReached("daily")
            if self.spent_usd >= self.daily_usd:
                raise LimitReached("budget")
            if self.by_token[h] >= self.per_token_reads:
                raise LimitReached("token")
            if self.by_ip[ip] >= self.per_ip_reads:
                raise LimitReached("ip")
            self.by_token[h] += 1
            self.by_ip[ip] += 1
            self.reads += 1

    def take_talk(self, who: str) -> None:
        """話すの一回（Claude を一回呼ぶ。道具の一往復も一回）を数える。費用の上限は読みと共通。

        who は相手（招待コードか token。ハッシュにして持つ）。0 ならこの口は閉じている（closed）。
        """
        h = token_hash(who)
        with self._lock:
            self._roll()
            if self.daily_talks <= 0:
                raise LimitReached("closed")
            if self.talks >= self.daily_talks:
                raise LimitReached("daily")
            if self.spent_usd >= self.daily_usd:
                raise LimitReached("budget")
            if self.talks_by[h] >= self.per_token_talks:
                raise LimitReached("token")
            self.talks_by[h] += 1
            self.talks += 1

    def take_lookup(self, ip: str) -> None:
        """照会（/api/lookup）の回数。外のサービスに出るので IP ごとに読みの 3 倍まで。"""
        with self._lock:
            self._roll()
            if self.lookups_by_ip[ip] >= self.per_ip_reads * 3:
                raise LimitReached("ip")
            self.lookups_by_ip[ip] += 1

    def take_connect(self, ip: str) -> None:
        """token 無し（Web の閲覧ページ）の「一言を送る」の回数。IP ごとに 1 日 CONNECT_PER_IP 回。"""
        with self._lock:
            self._roll()
            if self.connects_by_ip[ip] >= CONNECT_PER_IP:
                raise LimitReached("ip")
            self.connects_by_ip[ip] += 1

    def spend(self, usage: dict) -> float:
        cost = cost_usd(usage)
        with self._lock:
            self._roll()
            self.spent_usd += cost
        return cost

    def remaining(self) -> dict:
        with self._lock:
            self._roll()
            return {
                "reads": max(0, self.daily_reads - self.reads),
                "talks": max(0, self.daily_talks - self.talks),
                "usd": round(max(0.0, self.daily_usd - self.spent_usd), 2),
            }


class Tries:
    """門で断った回数を、相手の番地ごとに数える。window 秒に tries 回を数えたら、その番地を block 秒止める。

    家のサーバーの招待コードは手で打つ 6 桁（百万通り）なので、家の網の中の別の機械から総当たりで試されないように。
    通した要求でも数は戻さない（同じ番地に正しい人と試す者がいる時に、試し続けられないように）。
    clock は差し替えられる（テスト）。
    """

    def __init__(
        self,
        tries: int = GATE_TRIES,
        window: float = GATE_WINDOW,
        block: float = GATE_BLOCK,
        keep: int = GATE_KEEP,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.tries = max(1, tries)
        self.window = max(1.0, float(window))
        self.block = max(1.0, float(block))
        self.keep = max(1, keep)
        self.clock = clock
        self._fails: OrderedDict[str, deque[float]] = OrderedDict()  # 古く間違えた番地が前
        self._until: dict[str, float] = {}  # 止めている番地 → 止め終える時
        self._lock = threading.Lock()

    def blocked(self, ip: str) -> float:
        """止めていれば残りの秒（0 より大きい）。止めていなければ 0。"""
        with self._lock:
            until = self._until.get(ip)
            if until is None:
                return 0.0
            left = until - self.clock()
            if left > 0:
                return left
            del self._until[ip]
            return 0.0

    def fail(self, ip: str) -> bool:
        """間違えた一回を数える。これで止め始めたら True。"""
        now = self.clock()
        with self._lock:
            q = self._fails.pop(ip, None) or deque()
            while q and q[0] <= now - self.window:
                q.popleft()
            q.append(now)
            started = len(q) >= self.tries
            if started:
                self._until[ip] = now + self.block
            else:
                self._fails[ip] = q  # 後ろに置き直す（新しく間違えた番地が後ろ）
            self._trim(now)
            return started

    def _trim(self, now: float) -> None:
        while len(self._fails) > self.keep:
            self._fails.popitem(last=False)
        if len(self._until) > self.keep:
            for ip in [ip for ip, u in self._until.items() if u <= now]:
                del self._until[ip]
            while len(self._until) > self.keep:  # まだ多ければ、早く止め終える物から捨てる
                del self._until[min(self._until, key=self._until.__getitem__)]
