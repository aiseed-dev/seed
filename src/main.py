# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリの入口。`flet run`（PC、`--android`、`--ios`）と `flet build`（apk、ipa）がこれを開く。"""

import os
import sys

# スマートフォンでは、アプリの入れ物の中を家にする。記録（~/seed）も秘密（~/.config/seed）もこの中に置かれる。
# PC の `flet run` も FLET_APP_STORAGE_DATA を渡すので、スマートフォン（Python 3.13 からの sys.platform）か
# HOME が無い時だけ。PC で家を替えると、claude が ~/.claude のログインを見つけられず「ログインが切れています」になる（11-07）
_data = os.environ.get("FLET_APP_STORAGE_DATA")
if _data and (sys.platform in ("android", "ios") or not os.environ.get("HOME")):
    os.environ["HOME"] = _data

if sys.platform == "android":  # 写真を Pictures/seed に残せるかの確かめ（デバッグの記録に一行）
    try:
        import logging

        from seed import photos

        _pics = photos.device_pictures_dir()
        try:
            _pics.mkdir(parents=True, exist_ok=True)
            _result = "ok"
        except Exception as _ex:  # noqa: BLE001
            _result = type(_ex).__name__
        logging.getLogger("seed").info("Pictures/seed: %s", _result)
        print(f"Pictures/seed: {_result}", flush=True)
    except Exception:  # noqa: BLE001, S110  確かめが落ちても起動は続ける
        pass

import flet as ft

from seed.app.main import make_main

ft.run(make_main())
