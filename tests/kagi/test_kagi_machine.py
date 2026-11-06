import base64
import datetime as dt
import hashlib
import os
import subprocess

import pytest

from kagi import app, audit, cli, install, machine, report
from kagi.inventory import Refused

# 見本は全部偽物。鍵は公開鍵の形だけ（中身は決まった字の並びで、対になる秘密鍵は無い）。
NOW = dt.datetime(2026, 11, 7, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))


def _s(b: bytes) -> bytes:
    return len(b).to_bytes(4, "big") + b


def pub_ed(seed: int, comment: str = "someone@pc") -> str:
    blob = _s(b"ssh-ed25519") + _s(bytes([seed]) * 32)
    return f"ssh-ed25519 {base64.b64encode(blob).decode()} {comment}"


def pub_rsa(bits: int) -> str:
    n = (1 << (bits - 1)) | 1
    blob = _s(b"ssh-rsa") + _s(b"\x01\x00\x01") + _s(b"\x00" + n.to_bytes((bits + 7) // 8, "big"))
    return f"ssh-rsa {base64.b64encode(blob).decode()} old@pc"


def fp_of(line: str) -> str:
    blob = base64.b64decode(line.split()[1])
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


KEY_A, KEY_B, HOSTKEY = pub_ed(1), pub_ed(2), pub_ed(9)
FP_A, FP_B, FP_HOST = fp_of(KEY_A), fp_of(KEY_B), fp_of(HOSTKEY)


def table_text(pub_path: str, hostkey: str = FP_HOST, extra: str = "") -> str:
    return f"""\
[[machine]]
host = "box"
ssh = "box"
role = "見本の機械"
os = "debian-13"
users = ["dev"]
admins = ["dev"]
keys = ["k-a"]
hostkey = "{hostkey}"
{extra}
[[key]]
id = "k-a"
holder = "someone"
pub = "{pub_path}"
"""


def facts_text(**over) -> str:
    """良い形の写し。over で節を差し替える。"""
    sec = {
        "collected": "2026-11-07T08:00:00+0900\nuid=1000",
        "os": 'ID=debian\nVERSION_ID="13"\nPRETTY_NAME="Debian GNU/Linux 13 (trixie)"\nKERNEL=6.12.0\nHOSTNAME=box',
        "reboot": "no",
        "updates": "manager=apt\nnow=1794000000\nlists=1793990000",
        "auto": 'status=install ok installed\nAPT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";',
        "sshd": "effective=0\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nAllowUsers dev",
        "hostkeys": f"256 {FP_HOST} (ED25519)\n3072 SHA256:{'r' * 43} (RSA)",
        "authorized": f"dev 256 {FP_A} (ED25519)",
        "users": "dev /bin/bash",
        "admins": "sudo dev",
        "accounts": "",
        "sudoers": "",
        "firewall": "ufw=active\nnftables=inactive\nfirewalld=inactive\nENABLED=yes",
        "listen": 'LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))',
        "time": "NTP=yes\nNTPSynchronized=yes\nTimezone=Asia/Tokyo",
        "failed": "",
        "disk": "/ 41%",
        "crypt": "crypt=1",
    }
    sec.update(over)
    return machine.HEAD + "\n" + "".join(f"\n## kagi {k}\n{v}\n" for k, v in sec.items())


PORTS = [{"host": "box", "port": 22, "proto": "tcp", "bind": "0.0.0.0", "service": "ssh"}]


@pytest.fixture
def tbl(tmp_path):
    pub = tmp_path / "a.pub"
    pub.write_text(KEY_A + "\n")
    return machine.parse_table(table_text(str(pub)))


def run_check(tbl, text, ports_table=PORTS, ids=frozenset({"k-a"})):
    return machine.check(tbl, "box", machine.parse_facts(text), ports_table, set(ids), NOW)


def whats(findings, fix=True):
    return [(f.what, f.result) for f in findings if f.fix == fix]


# ---- 鍵 ----


def test_key_info_matches_ssh_keygen_form():
    info = machine.key_info(KEY_A)
    assert info.type == "ssh-ed25519" and info.fingerprint == FP_A and info.bits is None
    assert machine.FP.match(info.fingerprint)
    assert machine.key_info(pub_rsa(2048)).bits == 2048
    # authorized_keys の前置きの options があっても読む
    assert machine.key_info('from="192.0.2.1",no-pty ' + KEY_A).fingerprint == FP_A


def test_private_key_is_refused_unread(tmp_path):
    with pytest.raises(Refused, match="秘密鍵は読まない"):
        machine.key_info("-----BEGIN OPENSSH PRIVATE KEY-----")
    p = tmp_path / "id_ed25519"
    p.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nnot-a-real-key\n")
    with pytest.raises(Refused, match=r"\.pub"):
        machine.read_pub(p)  # 名で拒む。中身は開かない
    with pytest.raises(Refused, match="公開鍵として読めない"):
        machine.key_info("ssh-ed25519 !!!! x")


def test_table_refuses_value_fields_and_bad_names(tmp_path):
    with pytest.raises(Refused, match="K-13"):
        machine.parse_table('[[key]]\nid = "k"\nfingerprint = "' + FP_A + '"\nprivate = "x"\n')
    with pytest.raises(Refused, match="K-13"):
        machine.parse_table('[[machine]]\nhost = "a"\npassword = "x"\n')
    with pytest.raises(Refused, match="host"):
        machine.parse_table('[[machine]]\nhost = "-oProxyCommand=x"\n')
    with pytest.raises(Refused, match="ssh"):
        machine.parse_table('[[machine]]\nhost = "a"\nssh = "-oProxyCommand=x"\n')
    with pytest.raises(Refused, match="hostkey"):
        machine.parse_table('[[machine]]\nhost = "a"\nhostkey = "abc"\n')
    with pytest.raises(Refused, match="重複"):
        machine.parse_table('[[machine]]\nhost = "a"\n[[machine]]\nhost = "a"\n')


# ---- 写しと突き合わせ ----


def test_good_machine_has_nothing_to_fix(tbl):
    findings = run_check(tbl, facts_text())
    assert whats(findings) == []
    seen = whats(findings, fix=False)
    assert ("認証（ssh）", "鍵でだけ入る形。設定のファイルから（Match の中は見ていない）") in seen
    assert any(w == "写し" and "root でない" in r for w, r in seen)


def test_auth_findings(tbl):
    f = run_check(
        tbl,
        facts_text(
            sshd="effective=1\npasswordauthentication yes\npermitrootlogin yes\nkbdinteractiveauthentication yes"
        ),
    )
    res = [r for w, r in whats(f) if w == "認証（ssh）"]
    assert any("パスワードで入れる" in r and "実際に効いている値" in r for r in res)
    assert any("root がパスワードで入れる" in r for r in res)
    assert any("尋ねて答える形" in r for r in res)
    # 書いていなければ既定（yes）として直す物に
    f = run_check(tbl, facts_text(sshd="effective=0\nPermitRootLogin no"))
    assert any("書いていない。既定は yes" in r for _w, r in whats(f))
    # 最初に出た値が効く（drop-in が先）
    f = run_check(
        tbl,
        facts_text(
            sshd="effective=0\nPasswordAuthentication no\nPasswordAuthentication yes\nPermitRootLogin no"
        ),
    )
    assert not [r for w, r in whats(f) if w == "認証（ssh）"]


def test_key_findings(tbl):
    extra = f"dev 256 {FP_A} (ED25519)\ndev 256 {FP_B} (ED25519)\ndev 1024 SHA256:{'w' * 43} (RSA)"
    f = run_check(tbl, facts_text(authorized=extra))
    res = [r for w, r in whats(f) if w == "入っている鍵"]
    assert any("表に無い鍵が dev に入っている" in r and FP_B in r for r in res)
    assert any("弱い鍵" in r and "1024" in r for r in res)
    assert not any(FP_A in r for r in res)
    # 直す手は消す場所を言うだけで、鍵の中身は無い
    script = machine.fix_script("box", machine.parse_facts(facts_text(authorized=extra)), f)
    assert FP_B in script and "AAAA" not in script


def test_hostkey_mismatch_and_missing(tbl, tmp_path):
    f = run_check(tbl, facts_text(hostkeys=f"256 {FP_B} (ED25519)"))
    assert any(w == "機械の鍵" and "表と違う" in r for w, r in whats(f))
    pub = tmp_path / "a.pub"
    t2 = machine.parse_table(table_text(str(pub)).replace(f'hostkey = "{FP_HOST}"\n', ""))
    f = machine.check(t2, "box", machine.parse_facts(facts_text()), PORTS, {"k-a"}, NOW)
    assert any(w == "機械の鍵" and f'hostkey = "{FP_HOST}"' in r for w, r in whats(f, fix=False))


def test_key_missing_from_inventory_and_table(tbl):
    f = run_check(tbl, facts_text(), ids=frozenset())
    assert ("鍵の表", "鍵 k-a が在庫表に無い（K-14。inventory.toml に同じ id で一件）") in whats(f)
    tbl.machines[0]["keys"] = ["k-a", "ghost"]
    f = run_check(tbl, facts_text())
    assert any("ghost が [[key]] に無い" in r for _w, r in whats(f))


def test_people_findings(tbl):
    f = run_check(
        tbl,
        facts_text(
            users="dev /bin/bash\nformer /bin/bash\nsvc /usr/sbin/nologin",
            admins="sudo dev,former",
            accounts="dev P\nformer NP",
            sudoers="nopasswd=2",
            collected="2026-11-07T08:00:00+0900\nuid=0",
        ),
    )
    got = whats(f)
    assert ("アカウント", "表に無いアカウント: former") in got
    assert ("管理者", "表に無い管理者（sudo の組）: former") in got
    assert ("アカウント", "パスワードが空: former") in got
    assert any("パスワード無しの sudo が 2 行" in r for _w, r in got)
    assert not any("svc" in r for _w, r in got)  # 入れないアカウントは数えない
    assert "sudo usermod -L -e 1 former" in machine.fix_script("box", machine.parse_facts(facts_text()), f)


def test_updates_firewall_ports_time_disk(tbl):
    f = run_check(
        tbl,
        facts_text(
            reboot="required",
            updates="manager=apt\nnow=1794000000\nlists=1793000000\npkg openssl trixie-security\npkg vim trixie",
            auto="",
            firewall="ufw=active\nnftables=inactive\nfirewalld=inactive\nENABLED=no",
            listen='LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:5432 0.0.0.0:* users:(("postgres",pid=2,fd=3))',
            time="NTP=no\nNTPSynchronized=no",
            failed="foo.service",
            disk="/ 41%\n/srv 91%",
            crypt="crypt=0",
        ),
    )
    got = whats(f)
    assert ("更新", "再起動が要る") in got
    assert ("更新", "更新が 2 件（うち security 1）") in got
    assert any("一覧が 11 日古い" in r for _w, r in got)
    assert ("更新", "自動の更新が無い（unattended-upgrades）") in got
    assert any(w == "防火壁" for w, _r in got)
    assert ("口", "表に無い口: 5432（0.0.0.0 postgres）") in got
    assert ("時計", "時計が合わせられていない（K-11）") in got
    assert ("サービス", "落ちている: foo.service") in got
    assert ("盤", "/srv が 91%") in got
    assert any(w == "盤" and "暗号化されていない" in r for w, r in whats(f, fix=False))
    script = machine.fix_script("box", machine.parse_facts(facts_text()), f)
    assert "sudo ufw limit 22/tcp" in script and script.index("ufw limit") < script.index("sudo ufw enable")


def test_old_facts_and_no_ports_table(tbl):
    f = run_check(tbl, facts_text(collected="2026-10-20T08:00:00+0900\nuid=1000"), ports_table=None)
    seen = whats(f, fix=False)
    assert ("写し", "18 日前の写し（集め直す）") in seen
    assert ("口", "口の表にこの機械が無い（開いている口 1: 22）") in seen


def test_parse_facts_refuses_other_text():
    with pytest.raises(Refused):
        machine.parse_facts("LISTEN 0 128 0.0.0.0:22\n")


# ---- 写しを取る ----


def test_ssh_command_is_keys_only_and_known_hosts_only():
    cmd = machine.ssh_command("box")
    assert cmd[0] == "ssh" and cmd[-4:] == ["--", "box", "sh", "-s"]
    for opt in ("BatchMode=yes", "StrictHostKeyChecking=yes", "PasswordAuthentication=no"):
        assert opt in cmd
    with pytest.raises(Refused):
        machine.ssh_command("-oProxyCommand=evil")


def test_collect_with_runner(tmp_path):
    calls = []

    def ok(cmd, **kw):
        calls.append((cmd, kw["input"]))
        return subprocess.CompletedProcess(cmd, 0, facts_text(), "")

    text = machine.collect("box", ok)
    assert calls[0][0][0] == "ssh" and calls[0][1] == machine.SCRIPT
    p = machine.save_facts(tmp_path, "box", text, dt.datetime(2026, 11, 7, 9, 0, 0))
    assert p.name == "box-20261107-090000.txt" and oct(p.stat().st_mode & 0o777) == "0o600"
    assert machine.latest_facts(tmp_path, "box") == p

    def denied(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 255, "", "box: Permission denied (publickey).\n")

    with pytest.raises(Refused, match="Permission denied"):
        machine.collect("box", denied)


def test_script_reads_only_and_runs_here():
    # 変える命令が無い事（書き込み、消す、入れる、止める）
    for word in ("rm ", "apt install", "apt-get", "systemctl re", "systemctl st", "tee ", "chmod", "> /"):
        assert word not in machine.SCRIPT, word
    for word in ("ufw enable", "ufw allow", "usermod", "passwd -l", "sudo sh", "sudo -"):
        assert word not in machine.SCRIPT, word
    facts = machine.parse_facts(machine.collect(None))  # この機械で読むだけ
    assert facts.collected is not None and facts.pairs("os").get("KERNEL")


# ---- 入れる ----


def test_install_files(tbl, tmp_path):
    tbl.machines[0]["lan"] = "192.0.2.0/24"
    files = install.build(tbl, "box", dt.date(2026, 11, 7))
    pre, first, steps = files["preseed.cfg"], files["firstboot.sh"], files["手順.md"]
    # パスワードも盤も書かない
    assert "password" not in pre.replace("# No password", "").replace("The password is typed", "").lower()
    assert "partman" not in pre
    assert "d-i passwd/root-login boolean false" in pre and "d-i passwd/username string dev" in pre
    assert "d-i netcfg/hostname string box" in pre
    late = next(ln for ln in pre.splitlines() if "late_command" in ln)
    b64s = [w for w in late.split() if len(w) > 60]
    ak = base64.b64decode(b64s[0]).decode()
    conf = base64.b64decode(b64s[1]).decode()
    assert ak == KEY_A.rsplit(" ", 1)[0] + " k-a\n"  # 注釈（someone@pc）は入れず、表の id を付ける
    assert "PasswordAuthentication no" in conf and "PermitRootLogin no" in conf and "AllowUsers dev" in conf
    assert late.count("'") == 2  # 一重の引用の中に一重の引用が無い
    assert "ufw allow from 192.0.2.0/24 to any port 22 proto tcp" in first
    assert first.index("ufw allow") < first.index("ufw --force enable")
    assert FP_A in steps and "Permission denied (publickey)" in steps and "まだ確かめていない" in steps
    assert subprocess.run(["sh", "-n"], check=False, input=first, text=True).returncode == 0


def test_install_refuses_half_shapes(tbl, tmp_path):
    def with_(**kw):
        t = machine.parse_table(table_text(str(tmp_path / "a.pub")))
        t.machines[0].update(kw)
        return t

    for kw, msg in (
        ({"os": "ubuntu-24.04"}, "debian-13"),
        ({"admins": []}, "admins"),
        ({"keys": []}, "公開鍵が要る"),
        ({"lan": "192.0.2.1/24"}, "lan"),
        ({"profile": "x"}, "profile"),
        ({"mirror": "evil'; rm"}, "mirror"),
    ):
        with pytest.raises(Refused, match=msg):
            install.build(with_(**kw), "box")
    weak = tmp_path / "w.pub"
    weak.write_text(pub_rsa(1024) + "\n")
    t = machine.parse_table(table_text(str(weak)))
    with pytest.raises(Refused, match="弱い"):
        install.build(t, "box")


# ---- 命令、画面、報告 ----


def _dir(tmp_path, pub_line=KEY_A):
    d = tmp_path / "k"
    d.mkdir()
    (tmp_path / "a.pub").write_text(pub_line + "\n")
    (d / "machines.toml").write_text(table_text(str(tmp_path / "a.pub")))
    (d / "ports.toml").write_text('[[port]]\nhost = "box"\nport = 22\nbind = "0.0.0.0"\n')
    (d / "inventory.toml").write_text(
        '[[secret]]\nid = "k-a"\nkind = "key"\nwhere = "pc:~/.ssh"\nholder = "someone"\nrole = "box に入る"\n'
        'expires = 2999-01-01\nrotate_days = 365\nlost = "l"\nleaked = "k"\n'
    )
    return d


def test_cli_machine_and_key(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("KAGI_LOG_KEY_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    d = _dir(tmp_path)
    assert cli.main(["machine", "check", "--dir", str(d), "--host", "box"]) == 2  # 写しが無い
    assert cli.main(["machine", "check", "--dir", str(d)]) == 1
    assert "見ていない" in capsys.readouterr().out

    bad = tmp_path / "bad.txt"
    bad.write_text(facts_text(sshd="effective=0\nPasswordAuthentication yes"))
    assert cli.main(["machine", "check", "--dir", str(d), "--host", "box", "--facts", str(bad)]) == 1
    assert "パスワードで入れる" in capsys.readouterr().out
    assert cli.main(["machine", "fix", "--dir", str(d), "--host", "box", "--facts", str(bad)]) == 1
    assert "sudo sshd -t" in capsys.readouterr().out

    machine.save_facts(
        d, "box", facts_text(collected=f"{dt.datetime.now().astimezone():%Y-%m-%dT%H:%M:%S%z}\nuid=1000")
    )
    assert cli.main(["machine", "check", "--dir", str(d), "--host", "box"]) == 0
    assert "直す物は無い" in capsys.readouterr().out
    assert cli.main(["machine", "list", "--dir", str(d)]) == 0
    assert cli.main(["machine", "script"]) == 0
    assert capsys.readouterr().out.endswith(machine.SCRIPT)

    assert cli.main(["machine", "install", "--dir", str(d), "--host", "box"]) == 0
    assert {p.name for p in (d / "install" / "box").iterdir()} == {"preseed.cfg", "firstboot.sh", "手順.md"}
    assert cli.main(["scan", str(d / "install")]) == 0  # 作った物に秘密らしい文字列が無い
    capsys.readouterr()

    assert cli.main(["key", "list", "--dir", str(d)]) == 0
    out = capsys.readouterr().out
    assert FP_A in out and "box" in out and "期限 2999-01-01" in out
    assert cli.main(["key", "fingerprint", str(tmp_path / "a.pub")]) == 0
    assert capsys.readouterr().out.startswith(FP_A)
    (d / "inventory.toml").write_text("")
    assert cli.main(["key", "list", "--dir", str(d)]) == 1
    assert "無い（K-14）" in capsys.readouterr().out


def test_cli_collect_local_and_log(tmp_path, capsys, monkeypatch):
    d = _dir(tmp_path)
    keyf = tmp_path / "key"
    keyf.write_bytes(b"machine-test-key-not-a-secret")
    os.chmod(keyf, 0o600)
    monkeypatch.setenv("KAGI_LOG_KEY_FILE", str(keyf))
    assert cli.main(["machine", "collect", "--dir", str(d), "--host", "box", "--local"]) == 0
    assert machine.latest_facts(d, "box") is not None
    assert not (d / "audit.log").exists()  # この機械で取った時は ssh の鍵を使っていないので足さない

    def fake(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, facts_text(), "")

    monkeypatch.setattr(machine.subprocess, "run", fake)
    assert cli.main(["machine", "collect", "--dir", str(d), "--host", "box"]) == 0
    n, fails = audit.verify(d / "audit.log", audit.find_key())
    assert n == 1 and not fails and "machine.collect" in (d / "audit.log").read_text()
    assert cli.main(["machine", "collect", "--dir", str(d), "--host", "nope"]) == 2


def test_app_card_and_report(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGI_LOG_KEY_FILE", raising=False)
    d = _dir(tmp_path)
    c = app.build_cards(d)["machines"]
    assert c["summary"] == "機械 1 台、直す物のある機械 0、写しの無い機械 1"
    machine.save_facts(
        d, "box", facts_text(sshd="effective=0\nPasswordAuthentication yes", reboot="required")
    )
    c = app.build_cards(d)["machines"]
    assert "直す物のある機械 1" in c["summary"]
    assert c["rows"][0][0] == "box" and "認証（ssh）" in c["rows"][0][4] and "更新" in c["rows"][0][4]
    assert ["box", "更新", "再起動が要る"] in c["detail"]
    assert "sudo systemctl reboot" in app.fix_text(d, "box")
    text = report.build(d)
    assert "## 機械" in text and "- box: 直す物" in text

    def fake(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, facts_text(), "")

    p = app.collect_machine(d, "box", runner=fake, env={})
    assert p.exists()
    empty = tmp_path / "e"
    empty.mkdir()
    assert "機械の表が無い" in app.build_cards(empty)["machines"]["summary"]
    assert "機械の表が無い" in report.build(empty)


# ---- 管理の画面（Flet を使わない所）、サービス、動き ----


def test_services_and_load(tbl):
    tbl.machines[0]["services"] = ["seed", "caddy.service"]
    tbl.machines[0]["user_services"] = ["glimmer"]
    text = facts_text(
        services="caddy.service\nssh.service",
        **{
            "user-services": "glimmer.service",
            "load": "since=2026-10-28 14:25:57\nloadavg=1.01 1.01 1.00\nMemTotal=129468412\nMemAvailable=23993536",
        },
    )
    f = run_check(tbl, text)
    assert ("サービス", "動いていない: seed") in whats(f)
    assert not any("caddy" in r for _w, r in whats(f))
    seen = whats(f, fix=False)
    assert ("サービス", "表の 1 件が動いている（glimmer）") in seen
    assert ("動き", "起動 2026-10-28 14:25:57、load 1.01 1.01 1.00、メモリ 101/123 GB") in seen
    assert ("盤", "/ 41%") in seen
    script = machine.fix_script("box", machine.parse_facts(text), f)
    assert "sudo systemctl restart seed" in script and "systemctl status seed" in script
    tbl.machines[0]["user_services"] = ["sd-server"]
    f = run_check(tbl, text)
    assert ("サービス", "動いていない: sd-server（その人の systemd）") in whats(f)
    assert "systemctl --user restart sd-server" in machine.fix_script("box", machine.parse_facts(text), f)
    with pytest.raises(Refused, match="サービスの名"):
        machine.parse_table('[[machine]]\nhost = "a"\nservices = ["x; rm -rf /"]\n')


def test_port_findings_have_guidance(tbl):
    f = run_check(tbl, facts_text(listen="LISTEN 0 128 0.0.0.0:8080 0.0.0.0:*"))
    hows = {x.result: x.how for x in f if x.fix and x.what == "口"}
    assert any("grep ':8080 '" in h[0] for r, h in hows.items() if "表に無い口" in r)
    assert all(h for h in hows.values())


def test_add_machine_and_key_from_the_desk(tmp_path):
    d = tmp_path / "k"
    d.mkdir()
    pub = tmp_path / "a.pub"
    pub.write_text(KEY_A + "\n")
    assert app.keys_view(d)["error"]
    app.add_machine(d, "box", "", "見本", "dev、ops", "ops", "k-a", "seed, caddy", local=True)
    assert app.add_key(d, "k-a", "someone", str(pub)) == FP_A
    t = machine.load(d / "machines.toml")
    m = t.machine("box")
    assert m["users"] == ["dev", "ops"] and m["admins"] == ["ops"] and m["services"] == ["seed", "caddy"]
    assert m["local"] is True and "ssh" not in m and m["os"] == "debian-13"
    assert app.keys_view(d)["rows"] == [["k-a", "someone", FP_A, "box", "見ていない"]]
    # 読めない形は足さない（ファイルは元のまま）
    before = (d / "machines.toml").read_text()
    for bad in ({"host": "box"}, {"host": "-x"}, {"host": "ok", "users": "Bad Name"}):
        with pytest.raises(Refused):
            app.add_machine(d, **bad)
    with pytest.raises(Refused):
        app.add_key(d, "k-b", "x", str(tmp_path / "id_ed25519"))  # .pub でない
    assert (d / "machines.toml").read_text() == before


def test_machine_view_and_local_collect(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGI_LOG_KEY_FILE", raising=False)
    d = tmp_path / "k"
    d.mkdir()
    app.add_machine(d, "box", users="dev", admins="dev", local=True)
    v = app.machine_view(d, "box")
    assert v["facts"] is None and "写しが無い" in v["head"]
    assert app.machine_view(d, "nope")["error"] == "機械の表に nope が無い"
    called = []

    def fake(cmd, **kw):
        called.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, facts_text(reboot="required"), "")

    app.collect_machine(d, "box", runner=fake)
    assert called == [["sh", "-s"]]  # local = true の機械は ssh を使わない
    assert not (d / "audit.log").exists()
    v = app.machine_view(d, "box")
    assert v["head"].startswith("機械 box（") and "直す物" in v["head"]
    fix = next(f for f in v["fixes"] if f["result"] == "再起動が要る")
    assert fix["what"] == "更新" and fix["how"] == ["sudo systemctl reboot   # 時を選んで"]
    assert ["OS", "Debian GNU/Linux 13 (trixie)、kernel 6.12.0"] in v["notes"]
    with pytest.raises(Refused, match="公開鍵が要る"):
        app.install_files(d, "box")
