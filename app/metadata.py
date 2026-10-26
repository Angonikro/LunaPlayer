"""Read and edit audio metadata, and extract embedded artwork."""
def read_metadata(path):
    try:
        from mutagen import File
        audio=File(path,easy=True)
        if not audio: return {}
        keys=("title","artist","album","date","genre","tracknumber")
        return {k:(str(audio[k][0]) if audio.get(k) else "") for k in keys}
    except Exception: return {}
def write_metadata(path, fields):
    from mutagen import File
    audio=File(path,easy=True)
    if audio is None: raise ValueError("Datei oder Metadatenformat wird nicht unterstützt.")
    for key,value in fields.items():
        if key in ("title","artist","album","date","genre","tracknumber"):
            audio[key]=[str(value)] if str(value).strip() else []
    audio.save()
def read_cover_bytes(path):
    """Return embedded artwork first, otherwise a local cover image beside the track.

    This is intentionally read-only: sidecar artwork is used for display and is
    never written into or otherwise changes the audio file.
    """
    from pathlib import Path

    # Prefer artwork embedded in the audio file.
    try:
        from mutagen import File
        audio = File(path)
        if audio:
            # MP3 ID3 APIC
            for frame in getattr(getattr(audio, 'tags', None), 'values', lambda: [])():
                if getattr(frame, 'FrameID', None) == 'APIC' and getattr(frame, 'data', None):
                    return frame.data
            # FLAC-style pictures and Ogg picture tags
            pics = getattr(audio, 'pictures', None)
            if pics:
                return pics[0].data
            tags = getattr(audio, 'tags', None)
            if tags:
                for key in ('metadata_block_picture', 'coverart', 'COVERART'):
                    try:
                        val = tags[key]
                        if isinstance(val, list):
                            val = val[0]
                        import base64
                        if key == 'metadata_block_picture':
                            from mutagen.flac import Picture
                            return Picture(base64.b64decode(val)).data
                        return base64.b64decode(val)
                    except Exception:
                        pass
    except Exception:
        # Sidecar artwork should still work even if this format has no Mutagen
        # artwork support or its tags are malformed.
        pass

    # No embedded artwork: look for a conventional cover in the track's folder.
    # Named cover files are preferred over arbitrary images to avoid choosing
    # artist photos or unrelated pictures when possible.
    try:
        folder = Path(path).expanduser().resolve().parent
        preferred = (
            'cover.jpg', 'cover.jpeg', 'cover.png', 'cover.webp',
            'folder.jpg', 'folder.jpeg', 'folder.png', 'folder.webp',
            'front.jpg', 'front.jpeg', 'front.png', 'front.webp',
            'album.jpg', 'album.jpeg', 'album.png', 'album.webp',
            'albumart.jpg', 'albumart.png', 'artwork.jpg', 'artwork.png',
        )
        by_name = {item.name.casefold(): item for item in folder.iterdir() if item.is_file()}
        for name in preferred:
            image_path = by_name.get(name)
            if image_path:
                try:
                    if image_path.stat().st_size <= 20 * 1024 * 1024:
                        data = image_path.read_bytes()
                        if data:
                            return data
                except OSError:
                    pass
        # As a final fallback, accept a single ordinary image in the folder.
        images = sorted(
            (item for item in folder.iterdir()
             if item.is_file() and item.suffix.casefold() in ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
             and item.stat().st_size <= 20 * 1024 * 1024),
            key=lambda item: item.name.casefold(),
        )
        if len(images) == 1:
            return images[0].read_bytes()
    except (OSError, PermissionError):
        pass
    return None
