"""Small startup checks for required system libraries."""
def require_gtk():
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk  # noqa: F401
    except Exception as exc:
        raise SystemExit(
            "LunaPlayer benötigt GTK 4 und PyGObject. Unter Debian installieren mit:\n"
            "sudo apt install python3-gi gir1.2-gtk-4.0"
        ) from exc
