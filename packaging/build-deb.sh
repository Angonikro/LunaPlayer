#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=1.4.1
STAGE="$ROOT/build/deb"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/share/lunaplayer" "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/scalable/apps" "$STAGE/usr/share/pixmaps" "$STAGE/usr/share/doc/lunaplayer" "$STAGE/usr/share/lunaplayer/scripts"
chmod 755 "$STAGE/DEBIAN"; chmod g-s "$STAGE/DEBIAN"
cp "$ROOT/packaging/debian/control" "$STAGE/DEBIAN/control"
for maintainer_script in postinst postrm; do
    if [ -f "$ROOT/packaging/debian/$maintainer_script" ]; then
        cp "$ROOT/packaging/debian/$maintainer_script" "$STAGE/DEBIAN/$maintainer_script"
        chmod 755 "$STAGE/DEBIAN/$maintainer_script"
    fi
done
sed -i "s/^Version: .*/Version: $VERSION/" "$STAGE/DEBIAN/control"
cp "$ROOT/packaging/debian/changelog" "$STAGE/DEBIAN/changelog"
cp "$ROOT/packaging/debian/copyright" "$STAGE/usr/share/doc/lunaplayer/copyright"
for doc in README.md CHANGELOG.md RELEASE_NOTES_1.4.1.md LunaPlayer-1.3.1-Handbuch-DE-EN.pdf; do
    if [ -f "$ROOT/$doc" ]; then cp "$ROOT/$doc" "$STAGE/usr/share/doc/lunaplayer/"; fi
done
cp "$ROOT/main.py" "$STAGE/usr/share/lunaplayer/main.py"
cp "$ROOT/gtk_app.py" "$STAGE/usr/share/lunaplayer/gtk_app.py"
cp -r "$ROOT/app" "$ROOT/ui" "$STAGE/usr/share/lunaplayer/"
cp "$ROOT/scripts/create_desktop_entry.sh" "$STAGE/usr/share/lunaplayer/scripts/"
cat > "$STAGE/usr/share/lunaplayer/install_desktop_launcher.sh" <<'WRAPPER'
#!/bin/sh
set -eu
exec /usr/share/lunaplayer/scripts/create_desktop_entry.sh
WRAPPER
chmod 755 "$STAGE/usr/share/lunaplayer/install_desktop_launcher.sh"
cp "$ROOT/scripts/create_desktop_entry.sh" "$STAGE/usr/share/lunaplayer/create_desktop_entry.sh"
chmod 755 "$STAGE/usr/share/lunaplayer/scripts/create_desktop_entry.sh"
find "$STAGE/usr/share/lunaplayer" -type d -name __pycache__ -prune -exec rm -rf {} +
cp "$ROOT/data/icons/lunaplayer.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/lunaplayer.svg"
cp "$ROOT/data/icons/lunaplayer-256.png" "$STAGE/usr/share/pixmaps/lunaplayer.png"
sed 's|^Exec=.*|Exec=/usr/bin/lunaplayer|; s|^Icon=.*|Icon=/usr/share/pixmaps/lunaplayer.png|' "$ROOT/data/desktop/lunaplayer.desktop" > "$STAGE/usr/share/applications/lunaplayer.desktop"
cat > "$STAGE/usr/bin/lunaplayer" <<'WRAPPER'
#!/bin/sh
exec /usr/bin/python3 /usr/share/lunaplayer/main.py "$@"
WRAPPER
chmod 755 "$STAGE/usr/bin/lunaplayer"
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
find "$STAGE"/DEBIAN -maxdepth 1 -type f \( -name postinst -o -name postrm \) -exec chmod 755 {} +
chmod 755 "$STAGE/usr/bin/lunaplayer" "$STAGE/usr/share/lunaplayer/install_desktop_launcher.sh" "$STAGE/usr/share/lunaplayer/create_desktop_entry.sh" "$STAGE/usr/share/lunaplayer/scripts/create_desktop_entry.sh"
find "$STAGE" -type d -exec chmod g-s {} +
mkdir -p "$ROOT/dist"
dpkg-deb --build --root-owner-group "$STAGE" "$ROOT/dist/lunaplayer_${VERSION}_all.deb"
echo "Built $ROOT/dist/lunaplayer_${VERSION}_all.deb"

