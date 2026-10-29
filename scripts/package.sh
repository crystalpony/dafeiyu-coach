#!/usr/bin/env bash
# 构建 GitHub Release 资产：macOS .app + Windows 安装包 + SHA256。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="1.4.0"
DIST="${DAFEIYU_DIST:-$ROOT/dist}"
WORK="$(mktemp -d /tmp/dafeiyu-package.XXXXXX)"
APP="$WORK/Dafeiyu Coach.app"
mkdir -p "$DIST"
rm -rf "$DIST"/Dafeiyu\ Coach.app "$DIST"/dafeiyu-coach-"$VERSION"-macos.zip "$DIST"/dafeiyu-coach-"$VERSION"-windows.zip "$DIST"/SHA256SUMS

./scripts/build.sh
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/bin" "$APP/Contents/Resources"
cp .build/dafeiyu-daemon "$APP/Contents/Resources/bin/dafeiyu-daemon"
cp -R Runtime/clips "$APP/Contents/Resources/clips"
python3 scripts/prune_characters.py "${DAFEIYU_CHARACTERS_SRC:-$ROOT/Runtime/characters}" --snapshot "$APP/Contents/Resources/characters"
python3 scripts/prune_characters.py "$APP/Contents/Resources/characters" >/dev/null
cp -R Runtime/music "$APP/Contents/Resources/music"
cp -R Runtime/sounds "$APP/Contents/Resources/sounds"
cp Runtime/mascot.png "$APP/Contents/Resources/mascot.png"
cp bin/dafeiyu bin/dafeiyu_music.py bin/dafeiyu_tui.py bin/dafeiyu_gui.py bin/dafeiyu_mcp.py "$APP/Contents/Resources/bin/"
cp README.md LICENSE NOTICE.md CHANGELOG.md "$APP/Contents/Resources/"
cp -R skills adapter* "$APP/Contents/Resources/" 2>/dev/null || true
chmod +x "$APP/Contents/Resources/bin/"*

cat > "$APP/Contents/MacOS/DafeiyuCoach" <<'LAUNCH'
#!/bin/bash
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$HERE/Resources/bin"
export DAFEIYU_ASSETS="$HERE/Resources/clips"
export DAFEIYU_CHARACTERS="$HERE/Resources/characters"
export DAFEIYU_SOUNDS="$HERE/Resources/sounds"
export DAFEIYU_MUSIC_DIR="$HERE/Resources/music"
"$BIN/dafeiyu-daemon" &
DPID=$!
sleep 1
if kill -0 "$DPID" 2>/dev/null; then
  "$BIN/dafeiyu" music on >/dev/null 2>&1 || true
fi
trap 'kill "$(cat "$HOME/.dafeiyu/music.pid" 2>/dev/null)" 2>/dev/null || true' EXIT
wait "$DPID"
LAUNCH
chmod +x "$APP/Contents/MacOS/DafeiyuCoach"

APP_BUNDLE="$APP" python3 - <<'PY'
import os
from PIL import Image, ImageDraw
from pathlib import Path
import subprocess, shutil
root=Path('.')
im=Image.open('Runtime/clips/idle/idle_000.webp').convert('RGBA')
im.thumbnail((400,400), Image.LANCZOS)
canvas=Image.new('RGBA',(512,512),(246,242,234,255))
canvas.alpha_composite(im,((512-im.width)//2,(512-im.height)//2+20))
iconset=Path('/tmp/Dafeiyu.iconset'); shutil.rmtree(iconset,ignore_errors=True); iconset.mkdir()
for s in [16,32,128,256,512]:
    canvas.resize((s,s),Image.LANCZOS).save(iconset/f'icon_{s}x{s}.png')
    canvas.resize((s*2,s*2),Image.LANCZOS).save(iconset/f'icon_{s}x{s}@2x.png')
subprocess.run(['iconutil','-c','icns',str(iconset),'-o','/tmp/AppIcon.icns'],check=True)
shutil.copy2('/tmp/AppIcon.icns', __import__('os').environ['APP_BUNDLE'] + '/Contents/Resources/AppIcon.icns')
PY

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>DafeiyuCoach</string>
<key>CFBundleIdentifier</key><string>com.dafeiyu.coach</string>
<key>CFBundleName</key><string>Dafeiyu Coach</string>
<key>CFBundleDisplayName</key><string>桌面大肥鱼 Coach</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>$VERSION</string>
<key>CFBundleVersion</key><string>$VERSION</string>
<key>CFBundleIconFile</key><string>AppIcon</string>
<key>LSUIElement</key><true/>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
plutil -lint "$APP/Contents/Info.plist" >/dev/null
xattr -cr "$APP" 2>/dev/null || true
xattr -r -d com.apple.FinderInfo "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
(cd "$WORK" && ditto -c -k --keepParent --norsrc --noextattr "$APP" "$DIST/dafeiyu-coach-$VERSION-macos.zip")
rm -rf "$WORK"

# Windows：源码 + 素材 + 安装器（不捆绑 Python；安装器检查/安装 Pillow）
WIN="$DIST/dafeiyu-coach-$VERSION-windows"
rm -rf "$WIN"; mkdir -p "$WIN/bin" "$WIN/Runtime/music" "$WIN/scripts" "$WIN/skills" "$WIN/adapters"
cp bin/dafeiyu bin/dafeiyu_music.py bin/dafeiyu_tui.py bin/dafeiyu_gui.py bin/dafeiyu_mcp.py "$WIN/bin/"
cp scripts/install.ps1 requirements-windows.txt "$WIN/scripts/" 2>/dev/null || true
cp -R Runtime/clips "$WIN/Runtime/clips"
python3 scripts/prune_characters.py "${DAFEIYU_CHARACTERS_SRC:-$ROOT/Runtime/characters}" --snapshot "$WIN/Runtime/characters"
python3 scripts/prune_characters.py "$WIN/Runtime/characters" >/dev/null
cp -R Runtime/sounds "$WIN/Runtime/sounds"
cp Runtime/music/media_smtc.ps1 Runtime/music/README.md Runtime/music/LICENSE-MediaRemoteAdapter.txt "$WIN/Runtime/music/"
cp -R skills/dafeiyu-coach "$WIN/skills/"
cp -R adapters/* "$WIN/adapters/"
cp README.md LICENSE NOTICE.md CHANGELOG.md "$WIN/"
(cd "$DIST" && zip -qr "dafeiyu-coach-$VERSION-windows.zip" "dafeiyu-coach-$VERSION-windows")
rm -rf "$WIN"
(cd "$DIST" && shasum -a 256 dafeiyu-coach-"$VERSION"-macos.zip dafeiyu-coach-"$VERSION"-windows.zip > SHA256SUMS)
echo "--- dist ---"; ls -lh "$DIST"; echo; cat "$DIST/SHA256SUMS"
