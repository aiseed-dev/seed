#!/usr/bin/env bash
# seed grow --draw の描く server を家の機械に置く（設計書 §16.5）。
# stable-diffusion.cpp の sd-server で FLUX.2 klein 4B（Apache 2.0）を、OpenAI 形の
# /v1/images/generations と /v1/images/edits で出す。写真は家から出ない。
# sd-server は 127.0.0.1 だけで待つ（機械の外から直には届かない）。LAN へは門（Caddy、:11445）が、
# Bearer の token が一致した時だけ通す。門の設定と token の作り方は deploy/halo/（手順.md）。
#
# 人が読んでから、描く機械（AMD の iGPU gfx1151 と ROCm、Debian）で、ふつうの利用者として走らせる。
# 前提（sudo が要るので本人が先に）: render と video の組に入っている、lingering が有効
#   sudo usermod -aG render,video $USER; sudo loginctl enable-linger $USER
# 11435 は開けない。畑の PC から届くよう、門の口 11445 をその PC だけに開ける（例: ufw）
#   sudo ufw allow from <畑の PC の IP> to any port 11445 proto tcp
# 済んだら畑の PC で（token は ~/.config/seed/credentials.toml の draw_token か、環境変数 SEED_DRAW_TOKEN）:
#   seed grow --draw --server http://<この機械>:11445
#   （または seed.toml に [grow] server = "http://<この機械>:11445"、環境変数 SEED_DRAW_URL）
set -euo pipefail

PORT="${PORT:-11435}"
MODEL_DIR="${MODEL_DIR:-$HOME/models/sd}"
SD_DIR="${SD_DIR:-$HOME/sd.cpp}"
SD_COMMIT="${SD_COMMIT:-984eb06}"   # 2026-11-04 に動いた版
GPU="${GPU:-gfx1151}"

# 1. stable-diffusion.cpp を HIP で build（Vulkan でもよい: -DSD_VULKAN=ON）。
[ -d "$SD_DIR" ] || git clone --recursive https://github.com/leejet/stable-diffusion.cpp "$SD_DIR"
cd "$SD_DIR"
git fetch --depth 50 origin && git checkout "$SD_COMMIT" && git submodule update --init --recursive
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -B build -DSD_HIPBLAS=ON -DGPU_TARGETS="$GPU" -DAMDGPU_TARGETS="$GPU" -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "$(nproc)" --target sd-server

# 2. 重み（計 8.3 GB）。sha256 は Hugging Face の表示と同じ物（2026-11-04 に確かめた）。
mkdir -p "$MODEL_DIR" && cd "$MODEL_DIR"
fetch() { # 名 URL sha256
  [ -f "$1" ] || curl -fL -C - --retry 20 -o "$1" "$2"
  echo "$3  $1" | sha256sum -c -
}
fetch flux-2-klein-4b-Q8_0.gguf \
  https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q8_0.gguf \
  0bba6951258ec8f92d51114a8fa13e66828297bfff58a738f52729b3ef66fa28
fetch Qwen3-4B-Q8_0.gguf \
  https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q8_0.gguf \
  eed555233267a33c7e8ee31682762cc7751b3f6d224039086e0e846f05fffa5d
# VAE は black-forest-labs の正本が認証つきなので、Comfy-Org の写し（同じ中身かは未確認）。
fetch flux2-vae.safetensors \
  https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors \
  d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5

# 3. user の service。重みは起動時に読む（command-line preloading。api.md の Model management）。
#    steps 4、cfg 1.0、euler、1280x720 は既定で、seed は prompt の <sd_cpp_extra_args> でも同じ値を渡す。
#    sd-server の待ち受けは --listen-ip（--host ではない）。127.0.0.1 に縛る（外へは門 :11445 から）。
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/sd-server.service <<UNIT
[Unit]
Description=sd-server (stable-diffusion.cpp, FLUX.2 klein 4B Q8_0 + Qwen3-4B Q8_0 + flux2-vae) for seed grow --draw

[Service]
ExecStart=$SD_DIR/build/bin/sd-server --model-dir $MODEL_DIR --listen-ip 127.0.0.1 --listen-port $PORT --diffusion-model $MODEL_DIR/flux-2-klein-4b-Q8_0.gguf --llm $MODEL_DIR/Qwen3-4B-Q8_0.gguf --vae $MODEL_DIR/flux2-vae.safetensors --steps 4 --cfg-scale 1.0 --sampling-method euler -W 1280 -H 720
Restart=on-failure

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now sd-server.service
until curl -s "localhost:$PORT/sdcpp/v1/models/status" | grep -q '"state":"ready"'; do sleep 5; done
echo "ready: http://127.0.0.1:$PORT（この機械の中だけ）"
echo "畑の PC からは門を通して: http://$(hostname -I | awk '{print $1}'):11445（Bearer の token が要る。deploy/halo/）"
