#!/usr/bin/env python3
"""Netease Cloud Music CLI for OpenClaw — via pyncm."""
import json, sys, os

CONFIG_DIR = os.path.expanduser("~/.config/openclaw-ears")
SESSION_FILE = os.path.join(CONFIG_DIR, "netease-session.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

def save_session():
    from pyncm import GetCurrentSession
    sess = GetCurrentSession()
    cookies = []
    for cookie in iter(sess.cookies):
        cookies.append({"name": cookie.name, "value": cookie.value,
                        "domain": cookie.domain, "path": cookie.path})
    data = {
        "cookies_list": cookies,
        "csrf_token": getattr(sess, 'csrf_token', ''),
        "uid": getattr(sess, 'uid', 0),
        "login_info": getattr(sess, 'login_info', {}),
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(SESSION_FILE, 0o600)

def load_session():
    if not os.path.exists(SESSION_FILE):
        return False
    from pyncm import GetCurrentSession
    with open(SESSION_FILE) as f:
        data = json.load(f)
    sess = GetCurrentSession()
    for c in data.get("cookies_list", []):
        sess.cookies.set(c["name"], c["value"], domain=c.get("domain",""), path=c.get("path","/"))
    # Legacy format
    for k, v in data.get("cookies", {}).items():
        sess.cookies.set(k, v)
    if data.get("csrf_token"):
        sess.csrf_token = data["csrf_token"]
    if data.get("uid"):
        sess.uid = data["uid"]
    if data.get("login_info"):
        sess.login_info = data["login_info"]
    return True

def require_login():
    if not load_session():
        print("Not logged in. Run: netease.py login <phone>")
        sys.exit(1)
    from pyncm import apis
    try:
        result = apis.login.GetCurrentLoginStatus()
        # Check various response formats
        account = result.get("account") or (result.get("data", {}) or {}).get("account")
        profile = result.get("profile") or (result.get("data", {}) or {}).get("profile")
        if not account and not profile:
            print("Session expired. Run: netease.py login <phone>")
            sys.exit(1)
    except Exception:
        print("Session expired. Run: netease.py login <phone>")
        sys.exit(1)

def print_tracks(songs, numbered=True):
    for i, s in enumerate(songs, 1):
        artists = "/".join(a["name"] for a in s.get("ar", s.get("artists", [])))
        name = s.get("name", "?")
        sid = s.get("id", "?")
        prefix = f"{i}. " if numbered else ""
        print(f"{prefix}{name} — {artists} (id:{sid})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "login":
        from pyncm import apis
        if len(sys.argv) < 3:
            print("Usage: netease.py login <phone> [country_code]")
            print("  Default country code: 86 (China)")
            sys.exit(1)
        phone = sys.argv[2]
        ctcode = sys.argv[3] if len(sys.argv) > 3 else "86"
        print(f"Sending verification code to +{ctcode} {phone}...")
        try:
            result = apis.login.SetSendRegisterVerifcationCode(ctcode, phone)
            if result.get("code") != 200:
                print(f"Failed: {result.get('message', result)}")
                print("Try: netease.py login-qr")
                sys.exit(1)
        except Exception as e:
            print(f"Failed to send code: {e}")
            print("Try: netease.py login-qr")
            sys.exit(1)
        code = input("Enter verification code: ").strip()
        result = apis.login.LoginViaCellphone(phone=phone, ctcode=ctcode, captcha=code)
        if result.get("code") == 200:
            save_session()
            profile = result.get("profile", {})
            print(f"Logged in as: {profile.get('nickname', 'unknown')}")
        else:
            print(f"Login failed: {result.get('message', result)}")
            sys.exit(1)

    elif cmd == "login-qr":
        from pyncm import apis
        import time
        unikey_result = apis.login.LoginQrcodeUnikey()
        unikey = unikey_result.get("unikey")
        if not unikey:
            print(f"Failed to get QR key: {unikey_result}")
            sys.exit(1)
        qr_url = f"https://music.163.com/login?codekey={unikey}"
        print(f"Scan this QR code in 网易云音乐 app:")
        print(f"QR_URL:{qr_url}")
        try:
            import subprocess
            subprocess.run(["qrencode", "-t", "UTF8", qr_url], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("(Install qrencode for terminal QR: brew install qrencode)")
        print("\nWaiting for scan...")
        for _ in range(60):
            time.sleep(2)
            check = apis.login.LoginQrcodeCheck(unikey)
            code = check.get("code")
            if code == 803:
                save_session()
                print("Login successful!")
                status = apis.login.GetCurrentLoginStatus()
                profile = status.get("data", {}).get("profile", {})
                print(f"Welcome: {profile.get('nickname', 'unknown')}")
                sys.exit(0)
            elif code == 802:
                print("Scanned, waiting for confirmation...")
            elif code == 800:
                print("QR expired.")
                sys.exit(1)
        print("Timeout waiting for scan.")
        sys.exit(1)

    elif cmd == "status":
        if not load_session():
            print("Not logged in.")
            sys.exit(0)
        from pyncm import apis
        try:
            result = apis.login.GetCurrentLoginStatus()
            profile = result.get("profile") or (result.get("data", {}) or {}).get("profile")
            if profile:
                print(f"Logged in as: {profile.get('nickname')} (uid: {profile.get('userId')})")
            else:
                print("Session expired.")
        except Exception:
            print("Session expired.")

    elif cmd == "search":
        from pyncm import apis
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: netease.py search <query>")
            sys.exit(1)
        result = apis.cloudsearch.GetSearchResult(query, limit=20)
        songs = result.get("result", {}).get("songs", [])
        if songs:
            print_tracks(songs)
        else:
            print("No results.")

    elif cmd == "playlists":
        require_login()
        from pyncm import apis
        status = apis.login.GetCurrentLoginStatus()
        uid = status.get("data", {}).get("account", {}).get("id", 0)
        result = apis.user.GetUserPlaylists(uid, limit=50)
        for i, p in enumerate(result.get("playlist", []), 1):
            count = p.get("trackCount", "?")
            print(f"{i}. {p['name']} ({count} tracks) — id:{p['id']}")

    elif cmd == "playlist":
        from pyncm import apis
        if len(sys.argv) < 3:
            print("Usage: netease.py playlist <id>")
            sys.exit(1)
        pid = int(sys.argv[2])
        result = apis.playlist.GetPlaylistInfo(pid)
        playlist = result.get("playlist", {})
        tracks = playlist.get("tracks", [])
        if tracks:
            print(f"「{playlist.get('name', '?')}」- {len(tracks)} tracks\n")
            print_tracks(tracks)
        else:
            track_ids = [t["id"] for t in playlist.get("trackIds", [])]
            if track_ids:
                detail = apis.track.GetTrackDetail(track_ids[:100])
                print_tracks(detail.get("songs", []))
            else:
                print("Empty playlist.")

    elif cmd == "recent":
        require_login()
        from pyncm import apis
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        result = apis.user.GetRecentPlaylist()
        songs_data = result.get("data", {}).get("list", [])
        for i, item in enumerate(songs_data[:limit], 1):
            resource = item.get("resourceId", "")
            name = item.get("resourceName", "?")
            print(f"{i}. {name} (id:{resource})")

    elif cmd == "likes":
        require_login()
        from pyncm import apis
        status = apis.login.GetCurrentLoginStatus()
        uid = status.get("data", {}).get("account", {}).get("id", 0)
        playlists = apis.user.GetUserPlaylists(uid, limit=1)
        liked_id = playlists["playlist"][0]["id"]
        result = apis.playlist.GetPlaylistInfo(liked_id)
        tracks = result.get("playlist", {}).get("tracks", [])
        if tracks:
            print_tracks(tracks[:50])
        else:
            track_ids = [t["id"] for t in result.get("playlist", {}).get("trackIds", [])][:50]
            if track_ids:
                detail = apis.track.GetTrackDetail(track_ids)
                print_tracks(detail.get("songs", []))

    elif cmd == "url":
        require_login()
        from pyncm import apis
        if len(sys.argv) < 3:
            print("Usage: netease.py url <track_id> [bitrate]")
            sys.exit(1)
        track_id = int(sys.argv[2])
        bitrate = int(sys.argv[3]) if len(sys.argv) > 3 else 320000
        result = apis.track.GetTrackAudio([track_id], bitrate=bitrate)
        for d in result.get("data", []):
            if d.get("url"):
                print(d["url"])
            else:
                print(f"No URL available (code: {d.get('code')}, fee: {d.get('fee')})")

    elif cmd == "download":
        require_login()
        from pyncm import apis
        import urllib.request
        if len(sys.argv) < 3:
            print("Usage: netease.py download <track_id|search query> [output_dir]")
            sys.exit(1)

        # Check if arg is a number (track ID) or search query
        try:
            track_id = int(sys.argv[2])
            detail = apis.track.GetTrackDetail([track_id])
            track = detail["songs"][0]
        except ValueError:
            query = " ".join(sys.argv[2:])
            sr = apis.cloudsearch.GetSearchResult(query, limit=1)
            songs = sr.get("result", {}).get("songs", [])
            if not songs:
                print(f"No results for: {query}")
                sys.exit(1)
            track = songs[0]
            track_id = track["id"]

        artists = "/".join(a["name"] for a in track.get("ar", track.get("artists", [])))
        name = track.get("name", "unknown")
        print(f"Downloading: {name} — {artists}")

        audio = apis.track.GetTrackAudio([track_id], bitrate=320000)
        url = None
        ext = "mp3"
        for d in audio.get("data", []):
            if d.get("url"):
                url = d["url"]
                ext = d.get("type", "mp3")
                break
        if not url:
            print("No audio URL available. Track may require VIP or is region-locked.")
            sys.exit(1)

        out_dir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else "."
        os.makedirs(out_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in " -_.()" else "_" for c in f"{name} - {artists}")
        out_path = os.path.join(out_dir, f"{safe_name}.{ext}")

        urllib.request.urlretrieve(url, out_path)
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"Saved: {out_path} ({size_mb:.1f} MB)")

    elif cmd == "download-playlist":
        require_login()
        from pyncm import apis
        import urllib.request
        if len(sys.argv) < 3:
            print("Usage: netease.py download-playlist <playlist_id> [output_dir] [--limit N]")
            sys.exit(1)
        pid = int(sys.argv[2])
        out_dir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else "."
        limit = 50
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])

        result = apis.playlist.GetPlaylistInfo(pid)
        playlist = result.get("playlist", {})
        tracks = playlist.get("tracks", [])
        if not tracks:
            track_ids = [t["id"] for t in playlist.get("trackIds", [])][:limit]
            if track_ids:
                detail = apis.track.GetTrackDetail(track_ids)
                tracks = detail.get("songs", [])
        tracks = tracks[:limit]

        pname = "".join(c if c.isalnum() or c in " -_()" else "_" for c in playlist.get("name", "playlist"))
        out_dir = os.path.join(out_dir, pname)
        os.makedirs(out_dir, exist_ok=True)
        print(f"Downloading「{playlist.get('name')}」→ {out_dir}\n")

        for i, t in enumerate(tracks, 1):
            artists = "/".join(a["name"] for a in t.get("ar", []))
            name = t.get("name", "?")
            audio = apis.track.GetTrackAudio([t["id"]], bitrate=320000)
            url = None
            ext = "mp3"
            for d in audio.get("data", []):
                if d.get("url"):
                    url = d["url"]
                    ext = d.get("type", "mp3")
                    break
            if not url:
                print(f"{i}. SKIP (no URL): {name} — {artists}")
                continue
            safe = "".join(c if c.isalnum() or c in " -_.()" else "_" for c in f"{name} - {artists}")
            path = os.path.join(out_dir, f"{i:02d}. {safe}.{ext}")
            try:
                urllib.request.urlretrieve(url, path)
                size = os.path.getsize(path) / 1024 / 1024
                print(f"{i}. {name} — {artists} ({size:.1f} MB)")
            except Exception as e:
                print(f"{i}. FAILED: {name} — {e}")

        print(f"\nDone! Files in: {out_dir}")

    elif cmd == "play":
        # Search → download to temp → afplay
        import subprocess, tempfile, urllib.request
        if len(sys.argv) < 3:
            print("Usage: netease.py play <query|track_id>")
            sys.exit(1)
        require_login()
        from pyncm import apis

        try:
            track_id = int(sys.argv[2])
            # Lookup track info
            detail = apis.track.GetTrackDetail([track_id])
            songs = detail.get("songs", [])
            if songs:
                name = songs[0].get("name", "?")
                artists = "/".join(a["name"] for a in songs[0].get("ar", []))
            else:
                name, artists = str(track_id), ""
        except ValueError:
            query = " ".join(sys.argv[2:])
            result = apis.cloudsearch.GetSearchResult(query, limit=1)
            songs = result.get("result", {}).get("songs", [])
            if not songs:
                print(f"No results: {query}")
                sys.exit(1)
            track_id = songs[0]["id"]
            name = songs[0].get("name", "?")
            artists = "/".join(a["name"] for a in songs[0].get("ar", []))

        # Get audio URL
        audio = apis.track.GetTrackAudio([track_id], bitrate=320000)
        audio_url = (audio.get("data", [{}])[0] or {}).get("url")
        if not audio_url:
            print(f"No audio URL for: {name} — may be VIP-only.")
            sys.exit(1)

        print(f"Playing: {name} — {artists}")
        # Download to temp and play in background
        ext = "mp3" if ".mp3" in audio_url else "m4a"
        tmp = os.path.join(tempfile.gettempdir(), f"ears-play.{ext}")
        urllib.request.urlretrieve(audio_url, tmp)
        # Kill any previous afplay
        subprocess.run(["pkill", "-f", "afplay.*ears-play"], capture_output=True)
        subprocess.Popen(["nohup", "afplay", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    elif cmd == "play-mac":
        import subprocess
        action = sys.argv[2] if len(sys.argv) > 2 else "toggle"
        # Uses nowplaying-cli (brew install nowplaying-cli)
        cmds = {
            "toggle": ["nowplaying-cli", "togglePlayPause"],
            "play": ["nowplaying-cli", "play"],
            "pause": ["nowplaying-cli", "pause"],
            "next": ["nowplaying-cli", "next"],
            "prev": ["nowplaying-cli", "previous"],
            "now": ["nowplaying-cli", "get", "title", "artist", "album"],
        }
        if action not in cmds:
            print(f"Unknown action: {action}\nActions: toggle, play, pause, next, prev, now")
            sys.exit(1)
        try:
            r = subprocess.run(cmds[action], capture_output=True, text=True, timeout=5)
            if action == "now":
                lines = r.stdout.strip().split("\n")
                title = lines[0] if lines[0] != "null" else "?"
                artist = lines[1] if len(lines) > 1 and lines[1] != "null" else "?"
                album = lines[2] if len(lines) > 2 and lines[2] != "null" else "?"
                if title == "?" and artist == "?":
                    print("Nothing playing.")
                else:
                    print(f"{title} — {artist} [{album}]")
            else:
                labels = {"toggle": "Toggled play/pause", "play": "Playing", "pause": "Paused", "next": "Next track", "prev": "Previous track"}
                print(f"{labels[action]}.")
        except FileNotFoundError:
            print("nowplaying-cli not found. Install: brew install nowplaying-cli")

    else:
        print("""Netease Cloud Music CLI for OpenClaw

Usage: netease.py <command> [args]

Auth:
  login <phone> [country]   Login via SMS (default country: 86)
  login-qr                  Login via QR code scan
  status                    Check login status

Browse:
  search <query>            Search songs
  playlists                 Your playlists
  playlist <id>             Tracks in a playlist
  recent                    Recently played
  likes                     Your liked songs

Audio:
  url <track_id> [bitrate]  Get audio URL
  download <id|query> [dir] Download a track
  download-playlist <id> [dir] [--limit N]  Download playlist

Playback (macOS desktop app):
  play-mac toggle           Play/pause
  play-mac next             Next track
  play-mac prev             Previous track
""")
