# SPDX-License-Identifier: AGPL-3.0-or-later
"""スマートフォンのアプリ（iPhone 版、Android 版）の入口。`flet build ipa` がこれを包む（docs/iPhone 版.md）。"""

import os

# スマートフォンでは、アプリの入れ物の中を家にする。記録（~/seed）も秘密（~/.config/seed）もこの中に置かれる
_data = os.environ.get("FLET_APP_STORAGE_DATA")
if _data:
    os.environ["HOME"] = _data

import flet as ft

from seed.app.main import make_main

ft.run(make_main())
