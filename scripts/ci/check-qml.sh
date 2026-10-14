#!/usr/bin/env bash
set -euo pipefail

: "${OMARCHY_PATH:?Set OMARCHY_PATH to the pinned Omarchy checkout}"
bash "$OMARCHY_PATH/bin/omarchy-plugin-validate" /package
# Require the shipped notification dependency here; generic Python matrix jobs
# also cover pure helpers without the desktop's GObject bindings.
python3 -c 'from gi.repository import Gio, GLib'
python3 -m unittest discover -s tests -p test_notification_send.py -v
export XDG_RUNTIME_DIR
XDG_RUNTIME_DIR=$(mktemp -d)
chmod 700 "$XDG_RUNTIME_DIR"
compositor_pid=
cleanup() {
  if [[ -n $compositor_pid ]]; then
    kill "$compositor_pid" 2>/dev/null || true
    wait "$compositor_pid" 2>/dev/null || true
  fi
  rm -rf "$XDG_RUNTIME_DIR"
}
trap cleanup EXIT
cat > "$XDG_RUNTIME_DIR/sway.conf" <<'CONFIG'
xwayland disable
output HEADLESS-1 mode 1280x1024
CONFIG
sway -c "$XDG_RUNTIME_DIR/sway.conf" > "$XDG_RUNTIME_DIR/sway.log" 2>&1 &
compositor_pid=$!
for ((attempt=0; attempt<100; attempt++)); do
  for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
    if [[ -S $socket ]]; then
      export WAYLAND_DISPLAY=${socket##*/}
      python3 tests/smoke_qml.py --preview
      exit 0
    fi
  done
  if ! kill -0 "$compositor_pid" 2>/dev/null; then break; fi
  sleep 0.1
done
cat "$XDG_RUNTIME_DIR/sway.log" >&2
exit 1
