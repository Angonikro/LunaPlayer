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
    try:
        from mutagen import File
        audio=File(path)
        if not audio: return None
        # MP3 ID3 APIC
        for frame in getattr(getattr(audio,'tags',None),'values',lambda:[])():
            if getattr(frame,'FrameID',None)=='APIC' and getattr(frame,'data',None): return frame.data
        # FLAC-style pictures and Ogg picture tags
        pics=getattr(audio,'pictures',None)
        if pics: return pics[0].data
        tags=getattr(audio,'tags',None)
        if tags:
            for key in ('metadata_block_picture','coverart','COVERART'):
                try:
                    val=tags[key]
                    if isinstance(val,list): val=val[0]
                    if key=='metadata_block_picture':
                        import base64
                        from mutagen.flac import Picture
                        return Picture(base64.b64decode(val)).data
                    import base64
                    return base64.b64decode(val)
                except Exception: pass
    except Exception: pass
    return None
