#!/usr/bin/env bash
# seed のアプリを開く（macOS）。Finder で二度押しすると、ターミナルが開いて動きます
# 初めての時は、このフォルダーに .venv を作って部品を入れ（数分）、それからアプリを開きます。
# Opens the seed app (macOS). Double-click it in Finder. The first time, it makes .venv here and installs the parts (a few minutes).
# SEED_OPEN_DRY=1 で、走らせる命令を出すだけにします（何も作らず、開きません）。
set -u
cd "$(dirname "$0")" || exit 1

PYTHON_PAGE="https://www.python.org/downloads/"

run() {
    if [ "${SEED_OPEN_DRY:-}" = "1" ]; then
        printf '+ %s\n' "$*"
        return 0
    fi
    "$@"
}

find_python() {
    # Xcode の python3（3.9）は外れるので、python.org と Homebrew の物を先に見ます
    for p in /usr/local/bin/python3 /opt/homebrew/bin/python3 python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$p" >/dev/null 2>&1 &&
            "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

if [ ! -x .venv/bin/seed ]; then
    if [ ! -x .venv/bin/python ]; then
        if ! PY="$(find_python)"; then
            echo "Python 3.11 以上が要ります。開いた頁から入れて、もう一度開いてください。"
            echo "seed needs Python 3.11 or later. Install it from the page that opened, then open this again."
            if [ "$(uname)" = "Darwin" ]; then
                run open "$PYTHON_PAGE"
            else
                run xdg-open "$PYTHON_PAGE"
            fi
            exit 1
        fi
        echo "初めてなので、部品を入れます（数分かかります）。"
        echo "First time: installing the parts (a few minutes)."
        run "$PY" -m venv .venv || exit 1
    fi
    if ! run .venv/bin/python -m pip install -e ".[app,server]"; then
        echo "部品を入れられませんでした。上の文を Discord か GitHub の Issues で見せてください。"
        echo "Could not install the parts. Please share the messages above on Discord or GitHub Issues."
        exit 1
    fi
fi

run .venv/bin/seed app
