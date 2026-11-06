"""機械の表（machines.toml）と、機械の写し（facts）を突き合わせる。設計書 §3.4。

Linux の機械を「見る」側。入れる側は install.py。K-05、K-07、K-11、K-12、K-13、K-14。

- 機械の表は人が書く: 機械、役、入れてよい人、管理者、入れてよい鍵（公開鍵の指紋）、機械の鍵の指紋。
- 写しは、読むだけの決まった sh の文（SCRIPT）を機械で走らせた出力。何も変えず、秘密の値を出さない。
  人が走らせてファイルで渡すか、`collect` が人の ssh で走らせる（鍵でだけ、機械の鍵は確かめ済みの物だけ）。
- kagi は機械を変えない。直す手は sh の文として出すだけで、走らせるのは人（sudo は人の手）。
- 鍵は公開鍵と指紋だけを読む。秘密鍵のファイルは読まずに拒む。
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from kagi import ports
from kagi.inventory import Refused

FILENAME = "machines.toml"
FACTS_DIR = "facts"
HEAD = "# kagi-facts 1"
OLD_FACTS_DAYS = 7
OLD_LISTS_DAYS = 7
DISK_FULL = 85  # %
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")  # 機械の名、ssh の名（先頭に - を許さない）
USER = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
FP = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
KEY_TYPES = (
    "ssh-ed25519",
    "ssh-rsa",
    "ssh-dss",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
)
FORBIDDEN_FIELDS = ("value", "private", "password", "passphrase")  # 表に書かせない欄（K-13）

# 機械で走らせる文。読むだけ。POSIX sh。root でなくても走り、root なら見える物が増える。
SCRIPT = r"""#!/bin/sh
# kagi の機械の写し（docs/kagi 設計書.md §3.4）。読むだけで、何も変えない。秘密の値は出さない。
LC_ALL=C
export LC_ALL
sec() { printf '\n## kagi %s\n' "$1"; }
printf '# kagi-facts 1\n'

sec collected
date +%Y-%m-%dT%H:%M:%S%z
echo "uid=$(id -u)"

sec os
grep -E '^(ID|VERSION_ID|VERSION_CODENAME|PRETTY_NAME)=' /etc/os-release 2>/dev/null
echo "KERNEL=$(uname -r)"
echo "HOSTNAME=$(hostname)"

sec reboot
if [ -f /var/run/reboot-required ]; then echo required; else echo no; fi

sec updates
if command -v apt >/dev/null 2>&1; then
  echo "manager=apt"
  echo "now=$(date +%s)"
  for f in /var/lib/apt/periodic/update-success-stamp /var/lib/apt/lists; do
    if [ -e "$f" ]; then echo "lists=$(stat -c %Y "$f")"; break; fi
  done
  apt list --upgradable 2>/dev/null | awk -F'[/ ]' '/\// {print "pkg", $1, $2}'
else
  echo "manager=none"
fi

sec auto
dpkg-query -W -f='status=${Status}\n' unattended-upgrades 2>/dev/null
grep -hE '^[[:space:]]*APT::Periodic::(Update-Package-Lists|Unattended-Upgrade)' /etc/apt/apt.conf.d/* 2>/dev/null

sec sshd
KEYS='passwordauthentication|permitrootlogin|pubkeyauthentication|kbdinteractiveauthentication|allowusers|allowgroups|authenticationmethods'
if [ "$(id -u)" = 0 ] && sshd -T >/dev/null 2>&1; then
  echo "effective=1"
  sshd -T 2>/dev/null | grep -Ei "^($KEYS) "
else
  echo "effective=0"
  for f in /etc/ssh/sshd_config.d/*.conf /etc/ssh/sshd_config; do
    [ -e "$f" ] || continue
    if [ -r "$f" ]; then grep -Ei "^[[:space:]]*($KEYS)[[:space:]]" "$f"; else echo "unreadable $f"; fi
  done
fi

sec hostkeys
for f in /etc/ssh/ssh_host_*_key.pub; do
  [ -r "$f" ] && ssh-keygen -lf "$f" 2>/dev/null | awk '{print $1, $2, $NF}'
done

sec authorized
getent passwd | awk -F: '($3>=1000 && $3<65534) || $3==0 {print $1, $6}' | while read -r u h; do
  for f in "$h/.ssh/authorized_keys" "$h/.ssh/authorized_keys2"; do
    [ -r "$f" ] && ssh-keygen -lf "$f" 2>/dev/null | awk -v u="$u" '{print u, $1, $2, $NF}'
  done
done

sec users
getent passwd | awk -F: '$3>=1000 && $3<65534 {print $1, $7}'

sec admins
getent group sudo wheel admin 2>/dev/null | awk -F: '{print $1, $4}'

sec accounts
if [ "$(id -u)" = 0 ]; then passwd -S -a 2>/dev/null | awk '{print $1, $2}'; fi

sec sudoers
if [ "$(id -u)" = 0 ]; then
  echo "nopasswd=$(cat /etc/sudoers /etc/sudoers.d/* 2>/dev/null | grep -v '^[[:space:]]*#' | grep -c NOPASSWD)"
fi

sec firewall
for s in ufw nftables firewalld; do echo "$s=$(systemctl is-active "$s" 2>/dev/null)"; done
[ -r /etc/ufw/ufw.conf ] && grep -E '^ENABLED=' /etc/ufw/ufw.conf

sec listen
ss -ltnp 2>/dev/null

sec time
timedatectl show -p NTP -p NTPSynchronized -p Timezone 2>/dev/null

sec failed
systemctl --failed --no-legend --plain 2>/dev/null | awk '{print $1}'

sec disk
df -P -x tmpfs -x devtmpfs -x overlay -x squashfs -x efivarfs 2>/dev/null | awk 'NR>1 {print $6, $5}'

sec crypt
echo "crypt=$(lsblk -rno TYPE 2>/dev/null | grep -c crypt)"
"""


# ---- 鍵（公開鍵と指紋だけ） ----


@dataclass(frozen=True)
class KeyInfo:
    type: str
    fingerprint: str
    bits: int | None  # RSA だけ


def _string(buf: bytes, off: int) -> tuple[bytes, int]:
    n = int.from_bytes(buf[off : off + 4], "big")
    return buf[off + 4 : off + 4 + n], off + 4 + n


def key_info(line: str) -> KeyInfo:
    """公開鍵の一行（`ssh-ed25519 AAAA… comment`。authorized_keys の前置きの options も可）→ 種類と指紋。"""
    if "PRIVATE KEY" in line:
        raise Refused("秘密鍵は読まない（K-13）。公開鍵（.pub）を渡す")
    parts = line.split()
    for i, t in enumerate(parts[:-1]):
        if t in KEY_TYPES:
            try:
                blob = base64.b64decode(parts[i + 1], validate=True)
            except (binascii.Error, ValueError):
                break
            name, off = _string(blob, 0)
            if name.decode("ascii", "replace") != t:
                break
            bits = None
            if t == "ssh-rsa":
                _e, off = _string(blob, off)
                n, off = _string(blob, off)
                bits = int.from_bytes(n, "big").bit_length()
            fp = "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
            return KeyInfo(t, fp, bits)
    raise Refused("公開鍵として読めない")


def read_pub(path: Path) -> list[tuple[str, KeyInfo]]:
    """公開鍵のファイル（.pub）→ （行、種類と指紋）。.pub でない物と秘密鍵は読まずに拒む。"""
    path = Path(path).expanduser()
    if path.suffix != ".pub":
        raise Refused(f"公開鍵のファイル（.pub）だけを読む: {path.name}")
    try:
        text = path.read_text("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Refused(f"公開鍵を読めない: {path} ({type(e).__name__})") from None
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append((line, key_info(line)))
    if not out:
        raise Refused(f"公開鍵が無い: {path}")
    return out


# ---- 機械の表 ----


@dataclass
class Table:
    machines: list[dict] = field(default_factory=list)
    keys: list[dict] = field(default_factory=list)

    def machine(self, host: str) -> dict:
        for m in self.machines:
            if m["host"] == host:
                return m
        raise Refused(f"機械の表に {host} が無い（{FILENAME} の [[machine]]）")

    def key(self, kid: str) -> dict | None:
        return next((k for k in self.keys if k.get("id") == kid), None)

    def hosts(self) -> list[str]:
        return [m["host"] for m in self.machines]

    def machines_of(self, kid: str) -> list[str]:
        return [m["host"] for m in self.machines if kid in m.get("keys", [])]


def _names(row: dict, key: str, what: str) -> list[str]:
    v = row.get(key, [])
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise Refused(f"機械の表の {what} の {key} は名の並びで書く")
    return v


def parse_table(text: str, where: str = FILENAME) -> Table:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        m = re.search(r"line \d+, column \d+", str(e))
        raise Refused(f"機械の表が TOML として読めない: {where} ({m.group(0) if m else 'TOML'})") from None
    machines, keys = data.get("machine", []), data.get("key", [])
    for rows, name in ((machines, "machine"), (keys, "key")):
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise Refused(f"機械の表の {name} は [[{name}]] の並びで書く")
        for r in rows:
            bad = [k for k in r if str(k).lower() in FORBIDDEN_FIELDS]
            if bad:
                raise Refused(f"機械の表に {bad[0]} の欄がある。値は書かない（K-13）。欄を消してから走らせる")
    seen: set[str] = set()
    for i, m in enumerate(machines, 1):
        host = m.get("host")
        if not isinstance(host, str) or not NAME.match(host):
            raise Refused(f"機械の表の {i} 件目の host が名として読めない（英数字と . _ -）")
        if host in seen:
            raise Refused(f"機械の表の host が重複: {host}")
        seen.add(host)
        if not NAME.match(str(m.get("ssh", host))):
            raise Refused(f"機械の表の {host} の ssh が名として読めない（~/.ssh/config の名を書く）")
        for k in ("users", "admins"):
            for u in _names(m, k, host):
                if not USER.match(u):
                    raise Refused(f"機械の表の {host} の {k} に、アカウントの名として読めない物がある")
        _names(m, "keys", host)
        if "hostkey" in m and not (isinstance(m["hostkey"], str) and FP.match(m["hostkey"])):
            raise Refused(f"機械の表の {host} の hostkey は指紋（SHA256:…）で書く")
    seen = set()
    for i, k in enumerate(keys, 1):
        kid = k.get("id")
        if not isinstance(kid, str) or not kid:
            raise Refused(f"機械の表の鍵の {i} 件目に id が無い")
        if kid in seen:
            raise Refused(f"機械の表の鍵の id が重複: {kid}")
        seen.add(kid)
        if "fingerprint" in k and not (isinstance(k["fingerprint"], str) and FP.match(k["fingerprint"])):
            raise Refused(f"機械の表の鍵 {kid} の fingerprint は指紋（SHA256:…）で書く")
        if "fingerprint" not in k and "pub" not in k:
            raise Refused(f"機械の表の鍵 {kid} に fingerprint も pub（公開鍵のファイル）も無い")
    return Table(machines, keys)


def load(path: Path) -> Table:
    try:
        text = Path(path).read_text("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Refused(f"機械の表を読めない: {path} ({type(e).__name__})。無ければ kagi init") from None
    return parse_table(text, str(path))


def key_fingerprints(table: Table) -> tuple[dict[str, str], list[str]]:
    """鍵の id → 指紋。pub があればそこから計算し、fingerprint と違えば problems に。"""
    fps: dict[str, str] = {}
    problems: list[str] = []
    for k in table.keys:
        kid, fp = k["id"], k.get("fingerprint")
        if "pub" in k:
            try:
                infos = read_pub(Path(str(k["pub"])))
            except Refused as e:
                if fp is None:
                    problems.append(f"{kid}: {e}")
            else:
                got = infos[0][1].fingerprint
                if fp is not None and fp != got:
                    problems.append(f"{kid}: 表の fingerprint と pub のファイルの指紋が違う")
                fp = fp or got
        if fp:
            fps[kid] = fp
    return fps, problems


# ---- 写し ----


@dataclass
class Facts:
    sections: dict[str, list[str]] = field(default_factory=dict)

    def lines(self, name: str) -> list[str]:
        return self.sections.get(name, [])

    def pairs(self, name: str) -> dict[str, str]:
        """`KEY=value` の行。値の前後の " は外す。"""
        out = {}
        for line in self.lines(name):
            k, sep, v = line.partition("=")
            if sep:
                out[k.strip()] = v.strip().strip('"')
        return out

    @property
    def root(self) -> bool:
        return self.pairs("collected").get("uid") == "0"

    @property
    def collected(self) -> dt.datetime | None:
        for line in self.lines("collected"):
            try:
                return dt.datetime.strptime(line.strip(), "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                continue
        return None


def parse_facts(text: str) -> Facts:
    if not text.lstrip().startswith(HEAD):
        raise Refused("機械の写しとして読めない（kagi machine script の出力を渡す）")
    facts = Facts()
    cur: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## kagi "):
            cur = facts.sections.setdefault(line[len("## kagi ") :].strip(), [])
        elif cur is not None and line.strip():
            cur.append(line.rstrip())
    return facts


def load_facts(path: Path) -> Facts:
    try:
        return parse_facts(Path(path).read_text("utf-8", errors="replace"))
    except OSError as e:
        raise Refused(f"機械の写しを読めない: {path} ({type(e).__name__})") from None


def latest_facts(d: Path, host: str) -> Path | None:
    files = sorted((Path(d) / FACTS_DIR).glob(f"{host}-*.txt"))
    return files[-1] if files else None


def ssh_command(alias: str) -> list[str]:
    """人の ssh で、鍵でだけ、確かめ済みの機械にだけ入る。尋ねられる形（パスワード、初めての機械）は全部落ちる。"""
    if not NAME.match(alias):
        raise Refused("ssh の名として読めない")
    return [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "PasswordAuthentication=no",
        "-o", "KbdInteractiveAuthentication=no",
        "-o", "ConnectTimeout=10",
        "--", alias, "sh", "-s",
    ]  # fmt: skip


def collect(alias: str | None, runner=None, timeout: int = 90) -> str:
    """写しを取る。alias が None ならこの機械で。機械には SCRIPT を標準入力で渡すだけ（置かない、変えない）。"""
    cmd = ["sh", "-s"] if alias is None else ssh_command(alias)
    try:
        r = (runner or subprocess.run)(cmd, input=SCRIPT, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise Refused(f"{cmd[0]} が無い") from None
    except subprocess.TimeoutExpired:
        raise Refused(f"{timeout} 秒で返らなかった") from None
    if not r.stdout.lstrip().startswith(HEAD):
        why = (r.stderr or "").strip().splitlines()[-1:] or ["出力が無い"]
        hint = (
            "。鍵で入れる事と、機械の鍵を自分で確かめて known_hosts に入れた事を見る（手引き §4c）"
            if alias is not None
            else ""
        )
        raise Refused(f"写しが取れなかった（{why[0][:200]}）{hint}")
    return r.stdout


def save_facts(d: Path, host: str, text: str, now: dt.datetime | None = None) -> Path:
    now = now or dt.datetime.now()
    out = Path(d) / FACTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{host}-{now.strftime('%Y%m%d-%H%M%S')}.txt"
    p.write_text(text, "utf-8")
    p.chmod(0o600)  # アカウントの名と口が入る
    return p


# ---- 突き合わせ ----


@dataclass
class Finding:
    fix: bool  # 直す物か、見るだけか
    what: str
    result: str
    how: list[str] = field(default_factory=list)  # 直す手（sh の行。kagi は走らせない）


SSHD_DROPIN = "/etc/ssh/sshd_config.d/10-kagi.conf"
HOW_SSHD = [
    "# 先に、別の窓から鍵で入れる事を確かめる（入れなくなるのを防ぐ）",
    (
        "printf '%s\\n' 'PasswordAuthentication no' 'KbdInteractiveAuthentication no' 'PermitRootLogin no' "
        f"'PubkeyAuthentication yes' | sudo tee {SSHD_DROPIN} >/dev/null"
    ),
    "sudo sshd -t && sudo systemctl reload ssh",
]
NOLOGIN = ("nologin", "/false", "/sync")


def _sshd(facts: Facts) -> tuple[dict[str, str], bool, list[str]]:
    """sshd の設定（最初に出た値が効く）。root の写しなら実際に効いている値。"""
    vals: dict[str, str] = {}
    effective, unreadable = False, []
    for line in facts.lines("sshd"):
        s = line.strip()
        if s == "effective=1":
            effective = True
        elif s.startswith("unreadable "):
            unreadable.append(s.split(" ", 1)[1])
        elif not s.startswith("effective="):
            k, _, v = s.partition(" ")
            vals.setdefault(k.lower(), v.strip().lower())
    return vals, effective, unreadable


def _check_sshd(facts: Facts, allowed: set[str], out: list[Finding]) -> None:
    vals, effective, unreadable = _sshd(facts)
    if not facts.lines("sshd"):
        out.append(Finding(False, "認証（ssh）", "sshd の設定が写しに無い"))
        return
    src = "実際に効いている値" if effective else "設定のファイルから（Match の中は見ていない）"
    for f in unreadable:
        out.append(Finding(False, "認証（ssh）", f"読めなかった設定: {f}（root の写しで見る）"))
    pa = vals.get("passwordauthentication")
    if pa != "no":
        out.append(
            Finding(
                True,
                "認証（ssh）",
                f"パスワードで入れる（PasswordAuthentication {pa or '書いていない。既定は yes'}）。{src}",
                HOW_SSHD,
            )
        )
    kbd = vals.get("kbdinteractiveauthentication")
    if kbd == "yes":
        out.append(
            Finding(
                True, "認証（ssh）", "尋ねて答える形で入れる（KbdInteractiveAuthentication yes）", HOW_SSHD
            )
        )
    elif kbd is None:
        out.append(
            Finding(
                False,
                "認証（ssh）",
                "KbdInteractiveAuthentication を書いていない（root の写しで効いている値を見る）",
            )
        )
    prl = vals.get("permitrootlogin")
    if prl == "yes":
        out.append(Finding(True, "認証（ssh）", "root がパスワードで入れる（PermitRootLogin yes）", HOW_SSHD))
    elif prl != "no":
        out.append(
            Finding(
                False,
                "認証（ssh）",
                f"root が鍵で入れる（PermitRootLogin {prl or '書いていない。既定は prohibit-password'}）",
            )
        )
    if vals.get("pubkeyauthentication") == "no":
        out.append(Finding(True, "認証（ssh）", "鍵で入れない（PubkeyAuthentication no）", HOW_SSHD))
    au = vals.get("allowusers")
    if au is None and vals.get("allowgroups") is None:
        out.append(
            Finding(False, "認証（ssh）", "入れる人を絞っていない（AllowUsers も AllowGroups も無い）")
        )
    elif au is not None and allowed:
        extra = sorted({u.split("@")[0] for u in au.split()} - allowed)
        if extra:
            out.append(Finding(True, "認証（ssh）", f"AllowUsers に表に無い人: {', '.join(extra)}"))
    if pa == "no" and kbd in ("no", None) and prl in ("no", None, "prohibit-password", "without-password"):
        out.append(Finding(False, "認証（ssh）", f"鍵でだけ入る形。{src}"))


def _check_keys(
    table: Table, m: dict, facts: Facts, inventory_ids: set[str] | None, out: list[Finding]
) -> None:
    host = m["host"]
    fps, problems = key_fingerprints(table)
    for p in problems:
        out.append(Finding(True, "鍵の表", p))
    want: dict[str, str] = {}  # 指紋 → id
    for kid in m.get("keys", []):
        if table.key(kid) is None:
            out.append(Finding(True, "鍵の表", f"機械の keys の {kid} が [[key]] に無い"))
        elif kid in fps:
            want[fps[kid]] = kid
        if inventory_ids is not None and kid not in inventory_ids:
            out.append(
                Finding(
                    True,
                    "鍵の表",
                    f"鍵 {kid} が在庫表に無い（K-14。inventory.toml に同じ id で一件）",
                    [
                        f'# inventory.toml に [[secret]] を一件: id = "{kid}"、kind = "key"、where、holder、role、expires、rotate_days'
                    ],
                )
            )

    # 機械の鍵（この機械が本物かを確かめる指紋）
    ed = [ln.split() for ln in facts.lines("hostkeys") if "ED25519" in ln.upper()]
    got = ed[0][1] if ed and len(ed[0]) >= 2 else None
    if got is None:
        out.append(Finding(False, "機械の鍵", "ed25519 の機械の鍵が写しに無い"))
    elif "hostkey" not in m:
        out.append(
            Finding(False, "機械の鍵", f'表に指紋が無い。機械の画面で確かめてから書く: hostkey = "{got}"')
        )
    elif m["hostkey"] != got:
        out.append(
            Finding(
                True,
                "機械の鍵",
                f"表と違う（表 {m['hostkey']}、機械 {got}）。入れ直したのでなければ、別の機械か、間に誰か居る",
                [
                    f"# {host} の画面で: ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub  を見て、表か機械のどちらが正しいか決める"
                ],
            )
        )

    # 入っている鍵
    seen: set[str] = set()
    for line in facts.lines("authorized"):
        cols = line.split()
        if len(cols) < 4:
            continue
        user, bits, fp, typ = cols[0], cols[1], cols[2], cols[3].strip("()").upper()
        seen.add(fp)
        if fp not in want:
            out.append(
                Finding(
                    True,
                    "入っている鍵",
                    f"表に無い鍵が {user} に入っている（{typ} {fp}）",
                    [
                        f"# {user} の ~/.ssh/authorized_keys から、指紋 {fp} の行を消す（表に足すなら [[key]] と keys に）",
                        f"#   指紋の見方: ssh-keygen -lf ~{user}/.ssh/authorized_keys",
                    ],
                )
            )
        if typ == "DSA" or (typ == "RSA" and bits.isdigit() and int(bits) < 2048):
            out.append(
                Finding(True, "入っている鍵", f"弱い鍵が {user} に入っている（{typ} {bits} bit {fp}）")
            )
        elif typ == "RSA" and bits.isdigit() and int(bits) < 3072:
            out.append(
                Finding(
                    False, "入っている鍵", f"{user} に RSA {bits} bit（ed25519 に替える日を決める。{fp}）"
                )
            )
    for fp, kid in want.items():
        if fp not in seen:
            who = "" if facts.root else "（root でない写しなので、他の人の分は見えていない）"
            out.append(Finding(False, "入っている鍵", f"表の鍵 {kid} が機械に見当たらない{who}"))
    if not facts.root:
        out.append(
            Finding(False, "入っている鍵", "root でない写し。見えたのは写しを取った人の authorized_keys だけ")
        )


def _check_people(m: dict, facts: Facts, out: list[Finding]) -> None:
    users, admins = set(m.get("users", [])), set(m.get("admins", []))
    allowed = users | admins
    login = [
        c[0]
        for c in (ln.split() for ln in facts.lines("users"))
        if c and not (len(c) > 1 and c[1].endswith(NOLOGIN))
    ]
    if not allowed:
        if login:
            out.append(
                Finding(
                    False,
                    "アカウント",
                    f"表に users も admins も無いので比べていない（入れる人 {len(login)}: {', '.join(login)}）",
                )
            )
    else:
        for u in sorted(set(login) - allowed):
            out.append(
                Finding(
                    True,
                    "アカウント",
                    f"表に無いアカウント: {u}",
                    [f"sudo usermod -L -e 1 {u}   # 止める（消すのは中身を見てから: sudo deluser {u}）"],
                )
            )
        for u in sorted(allowed - set(login)):
            out.append(Finding(False, "アカウント", f"表にあって機械に無い: {u}"))
    members: set[str] = set()
    for line in facts.lines("admins"):
        cols = line.split()
        if len(cols) > 1:
            members |= {x for x in cols[1].split(",") if x}
    if admins or not members:
        for u in sorted(members - admins):
            out.append(
                Finding(True, "管理者", f"表に無い管理者（sudo の組）: {u}", [f"sudo gpasswd -d {u} sudo"])
            )
    else:
        out.append(
            Finding(
                False,
                "管理者",
                f"表に admins が無いので比べていない（sudo の組 {len(members)}: {', '.join(sorted(members))}）",
            )
        )
    for line in facts.lines("accounts"):
        cols = line.split()
        if len(cols) == 2 and cols[1] == "NP" and cols[0] in login:
            out.append(
                Finding(True, "アカウント", f"パスワードが空: {cols[0]}", [f"sudo passwd -l {cols[0]}"])
            )
    np = facts.pairs("sudoers").get("nopasswd")
    if np and np.isdigit() and int(np) > 0:
        out.append(Finding(True, "管理者", f"パスワード無しの sudo が {np} 行（/etc/sudoers と sudoers.d）"))


def check(
    table: Table,
    host: str,
    facts: Facts,
    ports_table: list[dict] | None = None,
    inventory_ids: set[str] | None = None,
    now: dt.datetime | None = None,
) -> list[Finding]:
    """機械の写しを、機械の表・口の表・在庫表と突き合わせる。"""
    m = table.machine(host)
    out: list[Finding] = []
    now = now or dt.datetime.now(dt.UTC)

    when = facts.collected
    if when is None:
        out.append(Finding(False, "写し", "取った時が読めない"))
    elif (now - when).days >= OLD_FACTS_DAYS:
        out.append(Finding(False, "写し", f"{(now - when).days} 日前の写し（集め直す）"))
    if not facts.root:
        out.append(
            Finding(
                False,
                "写し",
                "root でない写し。見えない物: 実際に効いている sshd の値、他の人の authorized_keys、パスワードの状態、sudoers",
            )
        )

    os_ = facts.pairs("os")
    out.append(Finding(False, "OS", f"{os_.get('PRETTY_NAME', '読めない')}、kernel {os_.get('KERNEL', '?')}"))
    if "os" in m and os_.get("ID"):
        got = f"{os_['ID']}-{os_.get('VERSION_ID', '')}".rstrip("-")
        if got != m["os"]:
            out.append(Finding(False, "OS", f"表は {m['os']}、機械は {got}"))
    if os_.get("HOSTNAME") and os_["HOSTNAME"].split(".")[0] != host:
        out.append(Finding(False, "OS", f"機械の名が表と違う（機械は {os_['HOSTNAME']}）"))

    if "required" in facts.lines("reboot"):
        out.append(Finding(True, "更新", "再起動が要る", ["sudo systemctl reboot   # 時を選んで"]))
    up = facts.pairs("updates")
    if up.get("manager") == "apt":
        pkgs = [ln.split() for ln in facts.lines("updates") if ln.startswith("pkg ")]
        sec = sum(1 for p in pkgs if len(p) > 2 and "security" in p[2])
        if pkgs:
            out.append(
                Finding(
                    True,
                    "更新",
                    f"更新が {len(pkgs)} 件（うち security {sec}）",
                    ["sudo apt update && sudo apt full-upgrade"],
                )
            )
        if up.get("lists", "").isdigit() and up.get("now", "").isdigit():
            days = (int(up["now"]) - int(up["lists"])) // 86400
            if days >= OLD_LISTS_DAYS:
                out.append(
                    Finding(
                        True,
                        "更新",
                        f"更新の一覧が {days} 日古い（件数は当てにならない）",
                        ["sudo apt update"],
                    )
                )
        auto = facts.lines("auto")
        installed = any(ln.strip() == "status=install ok installed" for ln in auto)
        on = any("Unattended-Upgrade" in ln and '"1"' in ln for ln in auto)
        if not (installed and on):
            out.append(
                Finding(
                    True,
                    "更新",
                    "自動の更新が無い（unattended-upgrades）",
                    [
                        "sudo apt install -y unattended-upgrades",
                        (
                            "printf '%s\\n' 'APT::Periodic::Update-Package-Lists \"1\";' 'APT::Periodic::Unattended-Upgrade \"1\";' "
                            "| sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null"
                        ),
                    ],
                )
            )
    else:
        out.append(Finding(False, "更新", "apt が無い機械。更新は見ていない"))

    _check_sshd(facts, set(m.get("users", [])) | set(m.get("admins", [])), out)
    _check_keys(table, m, facts, inventory_ids, out)
    _check_people(m, facts, out)

    fw = facts.pairs("firewall")
    if (fw.get("ufw") == "active" and fw.get("ENABLED") == "yes") or fw.get("firewalld") == "active":
        pass
    elif fw.get("nftables") == "active":
        out.append(Finding(False, "防火壁", "nftables が動いている（規則の中身は見ていない）"))
    else:
        out.append(
            Finding(
                True,
                "防火壁",
                "動いていない（ufw も firewalld も nftables も）",
                [
                    "sudo apt install -y ufw",
                    "sudo ufw default deny incoming && sudo ufw default allow outgoing",
                    "sudo ufw limit 22/tcp   # ssh を先に通す。LAN だけにするなら: sudo ufw allow from <LAN> to any port 22 proto tcp",
                    "sudo ufw enable",
                ],
            )
        )

    listens = ports.parse_ss("\n".join(facts.lines("listen")))
    rows = [p for p in (ports_table or []) if p.get("host") == host]
    if rows:
        diff = ports.compare(rows, listens, host)
        for l in diff.unlisted:
            out.append(
                Finding(True, "口", f"表に無い口: {l.port}（{l.bind} {l.process}）".replace(" ）", "）"))
            )
        for p in diff.closed:
            out.append(Finding(True, "口", f"表にあって開いていない: {p['port']}（{p.get('service', '')}）"))
        for l, want in diff.outward:
            out.append(Finding(True, "口", f"外向きで表と違う: {l.port}（機械は {l.bind}、表は {want}）"))
    else:
        nums = sorted({l.port for l in listens})
        out.append(
            Finding(
                False,
                "口",
                f"口の表にこの機械が無い（開いている口 {len(nums)}: {', '.join(map(str, nums))}）",
            )
        )

    t = facts.pairs("time")
    if t and t.get("NTPSynchronized") != "yes":
        out.append(
            Finding(True, "時計", "時計が合わせられていない（K-11）", ["sudo timedatectl set-ntp true"])
        )
    for unit in facts.lines("failed"):
        out.append(
            Finding(
                True,
                "サービス",
                f"落ちている: {unit.strip()}",
                [f"systemctl status {unit.strip()}   # 理由を見る"],
            )
        )
    for line in facts.lines("disk"):
        cols = line.split()
        if len(cols) == 2 and cols[1].rstrip("%").isdigit() and int(cols[1].rstrip("%")) >= DISK_FULL:
            out.append(Finding(True, "盤", f"{cols[0]} が {cols[1]}"))
    if facts.pairs("crypt").get("crypt") == "0":
        out.append(Finding(False, "盤", "暗号化されていない（持ち出す機械なら入れ直す時に。K-08）"))
    return out


def fixes(findings: list[Finding]) -> int:
    return sum(1 for f in findings if f.fix)


def _head(host: str, facts: Facts, findings: list[Finding]) -> str:
    when = facts.collected
    stamp = when.strftime("%Y-%m-%d %H:%M") if when else "時が読めない"
    who = "root の写し" if facts.root else "root でない写し"
    n = fixes(findings)
    return f"機械 {host}（{stamp}、{who}）: " + (f"直す物 {n}。" if n else "直す物は無い。")


def table(host: str, facts: Facts, findings: list[Finding]) -> str:
    lines = [_head(host, facts, findings), "", "| | 何 | 見た物 |", "|---|---|---|"]
    for fix in (True, False):
        for f in findings:
            if f.fix == fix:
                lines.append(f"| {'直す' if fix else '見るだけ'} | {f.what} | {f.result} |")
    return "\n".join(lines)


def fix_script(host: str, facts: Facts, findings: list[Finding]) -> str:
    """直す手を sh の文にする。kagi は走らせない。人が読んで、機械で、一つずつ。"""
    out = [
        "#!/bin/sh",
        f"# {_head(host, facts, findings)}",
        "# kagi はこれを走らせない。人が読んで、機械の端末で一つずつ。終わったら写しを取り直して確かめる。",
        "",
    ]
    done: set[tuple[str, ...]] = set()
    for f in findings:
        if not f.fix:
            continue
        out.append(f"# {f.what}: {f.result}")
        key = tuple(f.how)
        if not f.how:
            out.append("#   決まった手は無い。見て決める")
        elif key in done:
            out.append("#   上と同じ手")
        else:
            out += f.how
            done.add(key)
        out.append("")
    return "\n".join(out)


def key_table(table: Table, inventory: list[dict] | None = None) -> str:
    """鍵の一覧: 持つ人、指紋、入れてよい機械、在庫表の期限。値は無い（指紋は公開の物）。"""
    fps, problems = key_fingerprints(table)
    inv = {str(s.get("id")): s for s in (inventory or [])}
    lines = [
        f"鍵 {len(table.keys)} 件。",
        "",
        "| id | 持つ人 | 指紋 | 入れてよい機械 | 在庫表 |",
        "|---|---|---|---|---|",
    ]
    for k in table.keys:
        kid = k["id"]
        if inventory is None:
            stock = "見ていない"
        elif kid not in inv:
            stock = "無い（K-14）"
        else:
            stock = f"期限 {inv[kid]['expires']}" if inv[kid].get("expires") else "期限が無い（K-05）"
        hosts = ", ".join(table.machines_of(kid)) or "どこにも無い"
        lines.append(
            f"| {kid} | {k.get('holder', '書いていない')} | {fps.get(kid, '読めない')} | {hosts} | {stock} |"
        )
    lines += [f"- 直す: {p}" for p in problems]
    return "\n".join(lines)
