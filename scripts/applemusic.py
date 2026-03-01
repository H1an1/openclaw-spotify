#!/usr/bin/env python3
"""Apple Music CLI for OpenClaw — iTunes Search API + Music.app AppleScript control."""
import json, sys, os, subprocess, urllib.request, urllib.parse

ITUNES_API = "https://itunes.apple.com"

def osascript(script):
    """Run AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        if "not authorized" in result.stderr.lower() or "assistive" in result.stderr.lower():
            print("Permission denied. Grant Automation access:")
            print("  System Settings → Privacy & Security → Automation → enable Music.app")
            sys.exit(1)
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def itunes_search(term, media="music", entity=None, limit=20, country="US"):
    """Search iTunes/Apple Music catalog."""
    params = {"term": term, "media": media, "limit": limit, "country": country}
    if entity:
        params["entity"] = entity
    url = f"{ITUNES_API}/search?{urllib.parse.urlencode(params)}"
    data = json.loads(urllib.request.urlopen(url).read())
    return data.get("results", [])

def itunes_lookup(ids, entity=None):
    """Lookup by Apple Music IDs."""
    params = {"id": ",".join(str(i) for i in ids)}
    if entity:
        params["entity"] = entity
    url = f"{ITUNES_API}/lookup?{urllib.parse.urlencode(params)}"
    data = json.loads(urllib.request.urlopen(url).read())
    return data.get("results", [])

def print_tracks(results):
    for i, r in enumerate(results, 1):
        if r.get("wrapperType") == "collection" or r.get("collectionType"):
            print(f"{i}. [Album] {r.get('collectionName','?')} — {r.get('artistName','?')} ({r.get('trackCount','?')} tracks)")
        else:
            dur = r.get("trackTimeMillis", 0) // 1000
            mins, secs = divmod(dur, 60)
            print(f"{i}. {r.get('trackName','?')} — {r.get('artistName','?')} [{mins}:{secs:02d}] (id:{r.get('trackId','?')})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "search":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: applemusic.py search <query>")
            sys.exit(1)
        results = itunes_search(query, limit=20)
        print_tracks(results)

    elif cmd == "search-albums":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: applemusic.py search-albums <query>")
            sys.exit(1)
        results = itunes_search(query, entity="album", limit=10)
        print_tracks(results)

    elif cmd == "artist":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: applemusic.py artist <name>")
            sys.exit(1)
        # Search for artist, then lookup their songs
        artists = itunes_search(query, entity="musicArtist", limit=1)
        if not artists:
            print(f"Artist not found: {query}")
            sys.exit(1)
        a = artists[0]
        aid = a.get("artistId")
        print(f"{a.get('artistName','?')} — {a.get('primaryGenreName','?')}")
        print(f"Apple Music: {a.get('artistLinkUrl','')}\n")
        # Get top songs
        songs = itunes_lookup([aid], entity="song")
        songs = [s for s in songs if s.get("wrapperType") == "track"][:15]
        if songs:
            print("Top Songs:")
            print_tracks(songs)

    elif cmd == "album":
        if len(sys.argv) < 3:
            print("Usage: applemusic.py album <album_id>")
            sys.exit(1)
        aid = int(sys.argv[2])
        results = itunes_lookup([aid], entity="song")
        album_info = [r for r in results if r.get("wrapperType") == "collection"]
        tracks = [r for r in results if r.get("wrapperType") == "track"]
        if album_info:
            a = album_info[0]
            print(f"「{a.get('collectionName','?')}」— {a.get('artistName','?')} ({a.get('releaseDate','')[:4]})\n")
        print_tracks(tracks)

    elif cmd == "lookup":
        if len(sys.argv) < 3:
            print("Usage: applemusic.py lookup <track_id>")
            sys.exit(1)
        tid = int(sys.argv[2])
        results = itunes_lookup([tid])
        if results:
            r = results[0]
            print(f"{r.get('trackName','?')} — {r.get('artistName','?')}")
            print(f"Album: {r.get('collectionName','?')}")
            print(f"Preview: {r.get('previewUrl','N/A')}")
            print(f"Apple Music: {r.get('trackViewUrl','')}")

    elif cmd == "preview":
        if len(sys.argv) < 3:
            print("Usage: applemusic.py preview <track_id|query>")
            sys.exit(1)
        # Get preview URL and play with afplay
        try:
            tid = int(sys.argv[2])
            results = itunes_lookup([tid])
        except ValueError:
            query = " ".join(sys.argv[2:])
            results = itunes_search(query, limit=1)
        if not results:
            print("Not found.")
            sys.exit(1)
        r = results[0]
        preview = r.get("previewUrl")
        if not preview:
            print("No preview available.")
            sys.exit(1)
        print(f"Playing preview: {r.get('trackName','?')} — {r.get('artistName','?')}")
        # Download and play in background
        tmp = "/tmp/applemusic_preview.m4a"
        urllib.request.urlretrieve(preview, tmp)
        subprocess.run(["pkill", "-f", "afplay.*applemusic_preview"], capture_output=True)
        subprocess.Popen(["nohup", "afplay", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    elif cmd == "play":
        if len(sys.argv) < 3:
            print("Usage: applemusic.py play <query|track_id>")
            print("  Opens in Music.app or browser")
            sys.exit(1)
        try:
            tid = int(sys.argv[2])
            results = itunes_lookup([tid])
        except ValueError:
            query = " ".join(sys.argv[2:])
            results = itunes_search(query, limit=1)
        if not results:
            print("Not found.")
            sys.exit(1)
        r = results[0]
        url = r.get("trackViewUrl", "")
        print(f"Opening: {r.get('trackName','?')} — {r.get('artistName','?')}")
        # Open in Music.app directly
        subprocess.run(["open", "-a", "Music", url])

    # --- Music.app controls (macOS only) ---
    elif cmd == "now":
        try:
            script = '''tell application "Music"
                set t to name of current track
                set a to artist of current track
                set al to album of current track
                set s to player state as text
                return t & " — " & a & " [" & al & "] (" & s & ")"
            end tell'''
            print(osascript(script))
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "pause":
        try:
            osascript('tell application "Music" to pause')
            print("Paused.")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "resume":
        try:
            osascript('tell application "Music" to play')
            print("Playing.")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "next":
        try:
            osascript('tell application "Music" to next track')
            print("Next track.")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "prev":
        try:
            osascript('tell application "Music" to previous track')
            print("Previous track.")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "local-playlists":
        try:
            script = '''tell application "Music"
                set output to ""
                repeat with p in playlists
                    set output to output & (name of p) & " (" & (count of tracks of p) & " tracks)" & linefeed
                end repeat
                return output
            end tell'''
            print(osascript(script))
        except Exception as e:
            print(f"Error: {e}")

    else:
        print("""Apple Music CLI for OpenClaw

Usage: applemusic.py <command> [args]

Search (no auth needed, uses iTunes API):
  search <query>            Search songs
  search-albums <query>     Search albums
  artist <name>             Artist info + top songs
  album <album_id>          Album tracks
  lookup <track_id>         Track details

Play:
  play <id|query>           Open in Music.app / browser
  preview <id|query>        Play 30s preview via afplay

Music.app Control (macOS, needs Automation permission):
  now                       Currently playing
  pause                     Pause
  resume                    Resume
  next                      Next track
  prev                      Previous track
  local-playlists           List local playlists
""")
