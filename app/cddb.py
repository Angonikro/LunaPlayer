"""CD metadata from the fre:ac and dBpoweramp CDDB mirrors; artwork from MusicBrainz/Cover Art Archive."""
import json, re, shutil, subprocess, urllib.parse, urllib.request

APP_VERSION = "1.2.2"
USER_AGENT = f"LunaPlayer/{APP_VERSION} (Linux desktop audio player)"
CDDB_PROVIDERS = (
    ("fre:ac", "freedb.freac.org", "/~cddb/cddb.cgi", "80"),
    ("dBpoweramp", "freedb.dbpoweramp.com", "/~cddb/cddb.cgi", "80"),
)

def discid_parts(device):
    if not shutil.which("cd-discid"):
        raise RuntimeError("cd-discid fehlt; bitte installieren.")
    p = subprocess.run(["cd-discid", device], capture_output=True, text=True, timeout=10)
    parts = p.stdout.strip().split()
    if p.returncode or len(parts) < 4:
        raise RuntimeError((p.stderr or p.stdout or "CD konnte nicht identifiziert werden.").strip())
    count = int(parts[1]); offsets = [int(x) for x in parts[2:2+count]]; total = int(parts[2+count])
    if count < 1 or len(offsets) != count: raise RuntimeError("Ungültige CD-TOC-Daten.")
    return parts[0], count, offsets, total

def _get(url, accept=None, timeout=15):
    headers = {"User-Agent": USER_AGENT}
    if accept: headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp: return resp.read()

def lookup_cddb(parts, provider, settings=None):
    discid, count, offsets, total = parts
    settings = settings or {}
    name, host, path, port = provider
    if name == "fre:ac": host = settings.get("cddb_freac_host", host)
    else: host = settings.get("cddb_dbpoweramp_host", host)
    path = settings.get("cddb_path", path)
    port = str(settings.get("cddb_port", port))
    scheme = "https" if port == "443" else "http"
    port_suffix = "" if (scheme == "https" and port == "443") or (scheme == "http" and port == "80") else f":{port}"
    base = f"{scheme}://{host}{port_suffix}{path}"
    # Use the same CDDB hello field format as the proven LunaRipper implementation.
    # A contact address is optional; when absent use a neutral localhost identity.
    email = str(settings.get("cddb_email", "") or "").strip()
    if "@" in email:
        email_name, email_domain = email.rsplit("@", 1)
    else:
        email_name, email_domain = "lunaripper", "localhost"
    hello = f"{email_name} {email_domain} LunaRipper {APP_VERSION}"
    def command(cmd):
        url = base + "?" + urllib.parse.urlencode({"cmd": cmd, "hello": hello, "proto": "6"})
        return _get(url).decode("utf-8", "replace")
    query = "cddb query " + " ".join([discid, str(count), *map(str, offsets), str(total)])
    lines = command(query).replace("\r", "").splitlines()
    match = None
    for line in lines:
        m = re.match(r"^\s*200\s+([a-zA-Z0-9_-]+)\s+([0-9a-fA-F]{8})\s+(.+)$", line)
        if m: match = (m.group(1), m.group(2)); break
    if not match and any(re.match(r"^\s*(?:210|211)\b", x) for x in lines):
        for line in lines:
            m = re.match(r"^\s*([a-zA-Z0-9_-]+)\s+([0-9a-fA-F]{8})\s+(.+?)\s*$", line)
            if m and m.group(1) not in ("210", "211"): match = (m.group(1), m.group(2)); break
    if not match:
        reply = next((line.strip() for line in lines if line.strip()), "leere Serverantwort")
        raise RuntimeError(f"{name} ({host}:{port}): kein passender CD-Eintrag. Serverantwort: {reply[:240]}")
    entry = command(f"cddb read {match[0]} {match[1]}")
    fields = {}; current = None
    for line in entry.replace("\r", "").splitlines():
        if line == ".": break
        if "=" in line and not line.startswith("#"):
            current, value = line.split("=", 1); fields[current] = value
        elif line[:1].isspace() and current: fields[current] += line.strip()
    dtitle = fields.get("DTITLE", "")
    artist, album = dtitle.split(" / ", 1) if " / " in dtitle else ("", dtitle)
    result = {"provider": name, "discid": discid, "artist": artist.strip(), "album": album.strip(),
              "year": fields.get("DYEAR", "").strip(),
              "tracks": [fields.get(f"TTITLE{i}", "").strip() for i in range(count)]}
    if not (result["album"] or result["artist"] or any(result["tracks"])):
        raise RuntimeError(f"{name}: Eintrag enthält keine Titelinformationen.")
    return result

def lookup_musicbrainz_covers(artist, album, limit=20):
    """Find more editions than the first result so the correct cover can be chosen."""
    artist = (artist or "").strip()
    album = (album or "").strip()
    if not album:
        raise RuntimeError("Albumtitel fehlt; Online-Cover-Suche nicht möglich.")

    # LunaRipper's successful query order comes first. If its first page does not
    # contain the desired artwork, broaden the search rather than stopping at 5.
    queries = []
    if artist:
        queries.append(f'artist:"{artist}" AND release:"{album}"')
    queries.append(f'release:"{album}"')
    if artist:
        queries.append(f'{artist} {album}')

    candidates = []
    seen = set()
    errors = []
    for query in queries:
        url = "https://musicbrainz.org/ws/2/release/?" + urllib.parse.urlencode(
            {"query": query, "fmt": "json", "limit": str(max(20, limit))})
        try:
            data = json.loads(_get(url, "application/json").decode("utf-8"))
        except Exception as exc:
            errors.append(str(exc))
            continue
        for release in data.get("releases", []):
            rid = release.get("id")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            try:
                cover = _get(f"https://coverartarchive.org/release/{rid}/front-500", "image/*", 8)
            except Exception:
                continue
            credits = release.get("artist-credit", [])
            names = []
            for credit in credits:
                if isinstance(credit, dict):
                    name = credit.get("name") or (credit.get("artist") or {}).get("name")
                    if name: names.append(name)
                elif isinstance(credit, str):
                    names.append(credit)
            candidates.append({"release_id": rid, "title": release.get("title", album),
                               "artist": "".join(names) or artist,
                               "date": release.get("date", ""), "cover_bytes": cover})
            # Show up to ten actual cover choices from the ranked results.
            if len(candidates) >= 10:
                break
        if len(candidates) >= 10:
            break
        # Continue with broader searches when fewer than ten covers were found;
        # this helps surface alternate editions that the exact query ranked lower.
    if not candidates:
        detail = f" ({errors[-1]})" if errors else ""
        raise RuntimeError("MusicBrainz/Cover Art Archive: kein Cover für Interpret und Album gefunden." + detail)
    return candidates

# Compatibility wrapper retained for callers that expect one cover.
def lookup_musicbrainz_cover(discid):
    url = f"https://musicbrainz.org/ws/2/discid/{urllib.parse.quote(discid)}?" + urllib.parse.urlencode(
        {"inc": "artists+recordings", "fmt": "json"})
    data = json.loads(_get(url, "application/json").decode("utf-8"))
    for release in data.get("releases", []):
        rid = release.get("id")
        if rid:
            try:
                return _get(f"https://coverartarchive.org/release/{rid}/front-500", "image/*", 12), rid
            except Exception:
                pass
    raise RuntimeError("MusicBrainz/Cover Art Archive: kein Cover verfügbar.")

def lookup_cd(device, settings=None):
    settings = settings or {}
    parts = discid_parts(device); errors = []
    # Prefer the selected provider, then try the other mirror as fallback.
    preferred = settings.get("cddb_provider", "fre:ac")
    providers = sorted(CDDB_PROVIDERS, key=lambda p: 0 if p[0] == preferred else 1)
    for provider in providers:
        try:
            result = lookup_cddb(parts, provider, settings)
            result["release_id"] = ""; result["cover_bytes"] = None; result["cover_candidates"] = []
            try:
                result["cover_candidates"] = lookup_musicbrainz_covers(result.get("artist"), result.get("album"))
                first = result["cover_candidates"][0]
                result["cover_bytes"] = first["cover_bytes"]
                result["release_id"] = first["release_id"]
            except Exception as exc:
                result["cover_error"] = str(exc)
            return result
        except Exception as exc: errors.append(str(exc))
    raise RuntimeError("; ".join(errors))
