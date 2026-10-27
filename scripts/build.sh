#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .build
SOURCES=(Sources/*.swift)
FRAMEWORKS=(-framework AppKit -framework QuartzCore)
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "原生桌宠需要 macOS；Windows/Linux 请用 dafeiyu tui" >&2
  exit 2
fi
echo "building dafeiyu-daemon (universal arm64 + x86_64)..."
swiftc -O -swift-version 5 -target arm64-apple-macosx13.0 \
  "${SOURCES[@]}" "${FRAMEWORKS[@]}" -o .build/dafeiyu-daemon-arm64
swiftc -O -swift-version 5 -target x86_64-apple-macosx13.0 \
  "${SOURCES[@]}" "${FRAMEWORKS[@]}" -o .build/dafeiyu-daemon-x86_64
lipo -create .build/dafeiyu-daemon-arm64 .build/dafeiyu-daemon-x86_64 -output .build/dafeiyu-daemon
rm -f .build/dafeiyu-daemon-arm64 .build/dafeiyu-daemon-x86_64
lipo .build/dafeiyu-daemon -verify_arch arm64 x86_64
echo "built .build/dafeiyu-daemon ($(du -h .build/dafeiyu-daemon | cut -f1))"
