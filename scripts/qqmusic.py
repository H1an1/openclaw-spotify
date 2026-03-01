#!/usr/bin/env python3
"""QQ Music CLI for OpenClaw — direct API calls."""
import json, sys, os, urllib.request, urllib.parse

CONFIG_DIR = os.path.expanduser("~/.config/openclaw-ears")
COOKIE_FILE = os.path.join(CONFIG_DIR, "qqmusic-cookie.txt")
os.makedirs(CONFIG_DIR, exist_ok=True)

BASE_HEADERS = {
    "Referer": "https://y.qq.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

def api_call(module, method, param, cookie=None):
    """Call QQ Music unified API."""
    payload = json.dumps({
        "comm": {"ct": 19, "cv": 1859},
        "req": {"module": module, "method": method, "param": param}
    })
    req = urllib.request.Request(
        "https://u.y.qq.com/cgi-bin/musicu.fcg",
        data=payload.encode(),
        headers={**BASE_HEADERS, "Content-Type": "application/json",
                 **({"Cookie": cookie} if cookie else {})}
    )
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return data.get("req", {}).get("data", {})

def load_cookie():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE) as f:
            return f.read().strip()
    return None

def require_cookie():
    cookie = load_cookie()
    if not cookie:
        print("Not logged in. Run: qqmusic.py login")
        sys.exit(1)
    return cookie

def print_tracks(songs, numbered=True):
    for i, s in enumerate(songs, 1):
        singers = "/".join(x["name"] for x in s.get("singer", []))
        name = s.get("name", s.get("songname", "?"))
        mid = s.get("mid", s.get("songmid", "?"))
        prefix = f"{i}. " if numbered else ""
        print(f"{prefix}{name} — {singers} (mid:{mid})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "login":
        print("QQ Music requires a cookie from your browser.")
        print("")
        print("Steps:")
        print("1. Open https://y.qq.com in your browser")
        print("2. Log in with QQ or WeChat")
        print("3. Open DevTools (F12) → Application → Cookies → https://y.qq.com")
        print("4. Copy the full cookie string (or just the key cookies: qqmusic_key, Q_H_L_*, qm_keyst)")
        print("")
        print("Or use DevTools → Network → copy any request's Cookie header.")
        print("")
        cookie = input("Paste cookie string: ").strip()
        if cookie:
            with open(COOKIE_FILE, "w") as f:
                f.write(cookie)
            os.chmod(COOKIE_FILE, 0o600)
            print("Cookie saved!")
        else:
            print("No cookie provided.")
            sys.exit(1)

    elif cmd == "login-qr":
        import time, http.cookiejar
        # Get QR code
        req = urllib.request.Request(
            "https://ssl.ptlogin2.qq.com/ptqrshow?appid=716027609&e=2&l=M&s=3&d=72&v=4&daid=383",
            headers=BASE_HEADERS
        )
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        resp = opener.open(req)
        qr_data = resp.read()
        qr_path = "/tmp/qqmusic-qr.png"
        with open(qr_path, "wb") as f:
            f.write(qr_data)
        print(f"QR code saved to: {qr_path}")
        print("Scan with QQ app to log in.")

        # Get qrsig cookie
        qrsig = ""
        for cookie in cj:
            if cookie.name == "qrsig":
                qrsig = cookie.value
                break

        if not qrsig:
            print("Failed to get QR session.")
            sys.exit(1)

        # Hash function for ptqrlogin
        def hash33(s):
            h = 0
            for c in s:
                h += (h << 5) + ord(c)
            return h & 0x7FFFFFFF

        print("\nWaiting for scan...")
        for _ in range(60):
            time.sleep(2)
            ptqrtoken = hash33(qrsig)
            check_url = f"https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https%3A%2F%2Fy.qq.com&ptqrtoken={ptqrtoken}&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action=0-0-{int(time.time()*1000)}&js_ver=20102616&js_type=1&pt_uistyle=40&aid=716027609&daid=383"
            req = urllib.request.Request(check_url, headers={**BASE_HEADERS, "Cookie": f"qrsig={qrsig}"})
            resp = opener.open(req)
            text = resp.read().decode()
            if "'登录成功'" in text or "ptuiCB('0'" in text:
                # Extract cookies
                cookies_str = "; ".join(f"{c.name}={c.value}" for c in cj)
                # Follow redirect to get music cookies
                import re
                m = re.search(r"'(https?://[^']+)'", text)
                if m:
                    redirect_url = m.group(1)
                    req2 = urllib.request.Request(redirect_url, headers=BASE_HEADERS)
                    try:
                        opener.open(req2)
                    except Exception:
                        pass
                    cookies_str = "; ".join(f"{c.name}={c.value}" for c in cj)

                with open(COOKIE_FILE, "w") as f:
                    f.write(cookies_str)
                os.chmod(COOKIE_FILE, 0o600)
                print("Login successful! Cookie saved.")
                sys.exit(0)
            elif "'二维码已失效'" in text:
                print("QR code expired.")
                sys.exit(1)
            elif "'二维码认证中'" in text:
                print("Scanned, waiting for confirmation...")
        print("Timeout.")
        sys.exit(1)

    elif cmd == "status":
        cookie = load_cookie()
        if not cookie:
            print("Not logged in.")
        else:
            print(f"Cookie loaded ({len(cookie)} chars).")
            # Try a simple API call to verify
            try:
                data = api_call(
                    "music.musichallSong.PlayLaterSvr",
                    "GetPlayLaterTotal", {}, cookie
                )
                print("Session appears valid.")
            except Exception as e:
                print(f"Session may be expired: {e}")

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: qqmusic.py search <query>")
            sys.exit(1)
        data = api_call(
            "music.search.SearchCgiService",
            "DoSearchForQQMusicDesktop",
            {"num_per_page": 20, "page_num": 1, "query": query, "search_type": 0}
        )
        songs = data.get("body", {}).get("song", {}).get("list", [])
        print_tracks(songs)

    elif cmd == "search-albums":
        query = " ".join(sys.argv[2:])
        if not query:
            print("Usage: qqmusic.py search-albums <query>")
            sys.exit(1)
        data = api_call(
            "music.search.SearchCgiService",
            "DoSearchForQQMusicDesktop",
            {"num_per_page": 10, "page_num": 1, "query": query, "search_type": 2}
        )
        albums = data.get("body", {}).get("album", {}).get("list", [])
        for i, a in enumerate(albums, 1):
            singers = "/".join(x["name"] for x in a.get("singer_list", a.get("singer", [])))
            print(f"{i}. {a.get('albumName', a.get('name','?'))} — {singers} (mid:{a.get('albumMid', a.get('mid','?'))})")

    elif cmd == "playlists":
        cookie = require_cookie()
        # Get user's playlists - need uin from cookie
        import re
        uin_match = re.search(r'uin=(\d+)', cookie) or re.search(r'wxuin=(\d+)', cookie)
        if not uin_match:
            print("Cannot extract QQ uin from cookie. Make sure you're logged in.")
            sys.exit(1)
        uin = uin_match.group(1)

        url = f"https://c.y.qq.com/rsc/fcgi-bin/fcg_user_created_diss?hostuin={uin}&size=50&format=json"
        req = urllib.request.Request(url, headers={**BASE_HEADERS, "Cookie": cookie})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        playlists = data.get("data", {}).get("disslist", [])
        for i, p in enumerate(playlists, 1):
            print(f"{i}. {p.get('title', '?')} ({p.get('subtitle', '?')}) — id:{p.get('tid', '?')}")

    elif cmd == "playlist":
        if len(sys.argv) < 3:
            print("Usage: qqmusic.py playlist <id>")
            sys.exit(1)
        pid = sys.argv[2]
        cookie = load_cookie() or ""
        url = f"https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg?disstid={pid}&type=1&json=1&utf8=1&format=json"
        req = urllib.request.Request(url, headers={**BASE_HEADERS, "Cookie": cookie})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        cdlist = data.get("cdlist", [{}])
        if cdlist:
            cd = cdlist[0]
            songs = cd.get("songlist", [])
            print(f"「{cd.get('dissname', '?')}」— {len(songs)} tracks\n")
            for i, s in enumerate(songs, 1):
                singers = "/".join(x["name"] for x in s.get("singer", []))
                print(f"{i}. {s.get('songname', '?')} — {singers} (mid:{s.get('songmid', '?')})")

    elif cmd == "url":
        if len(sys.argv) < 3:
            print("Usage: qqmusic.py url <songmid>")
            sys.exit(1)
        mid = sys.argv[2]
        cookie = load_cookie() or ""
        # Try to get play URL
        data = api_call(
            "vkey.GetVkeyServer",
            "CgiGetVkey",
            {
                "guid": "1234567890",
                "songmid": [mid],
                "songtype": [0],
                "uin": "0",
                "loginflag": 1,
                "platform": "20"
            },
            cookie
        )
        midurlinfo = data.get("midurlinfo", [])
        if midurlinfo and midurlinfo[0].get("purl"):
            sip = data.get("sip", ["https://ws.stream.qqmusic.qq.com/"])[0]
            print(f"{sip}{midurlinfo[0]['purl']}")
        else:
            print("No URL available (may require VIP).")
            # Fallback: try lower quality
            print(f"Try in browser: https://y.qq.com/n/ryqq/songDetail/{mid}")

    elif cmd == "play":
        if len(sys.argv) < 3:
            print("Usage: qqmusic.py play <songmid|query>")
            sys.exit(1)
        import webbrowser
        arg = sys.argv[2]
        # If it looks like a mid (alphanumeric, ~14 chars), use directly
        if len(arg) >= 10 and arg.isalnum() and not " " in " ".join(sys.argv[2:]):
            mid = arg
        else:
            query = " ".join(sys.argv[2:])
            data = api_call(
                "music.search.SearchCgiService",
                "DoSearchForQQMusicDesktop",
                {"num_per_page": 1, "page_num": 1, "query": query, "search_type": 0}
            )
            songs = data.get("body", {}).get("song", {}).get("list", [])
            if not songs:
                print(f"No results: {query}")
                sys.exit(1)
            mid = songs[0].get("mid", "")
            singers = "/".join(x["name"] for x in songs[0].get("singer", []))
            print(f"Playing: {songs[0].get('name','?')} — {singers}")

        url = f"https://y.qq.com/n/ryqq/songDetail/{mid}"
        webbrowser.open(url)
        print(f"Opened: {url}")

    elif cmd == "download":
        if len(sys.argv) < 3:
            print("Usage: qqmusic.py download <songmid|query> [output_dir]")
            sys.exit(1)
        cookie = load_cookie() or ""

        arg = sys.argv[2]
        out_dir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else "."

        # Resolve to songmid
        if len(arg) >= 10 and arg.isalnum():
            mid = arg
            name = mid
            artists = ""
        else:
            # Exclude output_dir from query
            query_parts = sys.argv[2:]
            if len(query_parts) > 1 and os.path.isdir(query_parts[-1]):
                query = " ".join(query_parts[:-1])
            else:
                query = " ".join(query_parts)
            data = api_call(
                "music.search.SearchCgiService",
                "DoSearchForQQMusicDesktop",
                {"num_per_page": 1, "page_num": 1, "query": query, "search_type": 0}
            )
            songs = data.get("body", {}).get("song", {}).get("list", [])
            if not songs:
                print(f"No results: {query}")
                sys.exit(1)
            s = songs[0]
            mid = s.get("mid", "")
            name = s.get("name", "?")
            artists = "/".join(x["name"] for x in s.get("singer", []))
            print(f"Downloading: {name} — {artists}")

        # Get URL
        data = api_call(
            "vkey.GetVkeyServer",
            "CgiGetVkey",
            {
                "guid": "1234567890",
                "songmid": [mid],
                "songtype": [0],
                "uin": "0",
                "loginflag": 1,
                "platform": "20"
            },
            cookie
        )
        midurlinfo = data.get("midurlinfo", [])
        if not midurlinfo or not midurlinfo[0].get("purl"):
            print("No audio URL. Track may require VIP.")
            sys.exit(1)

        sip = data.get("sip", ["https://ws.stream.qqmusic.qq.com/"])[0]
        audio_url = f"{sip}{midurlinfo[0]['purl']}"

        os.makedirs(out_dir, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in " -_.()" else "_" for c in f"{name} - {artists}")
        ext = "m4a"
        out_path = os.path.join(out_dir, f"{safe}.{ext}")

        urllib.request.urlretrieve(audio_url, out_path)
        size = os.path.getsize(out_path) / 1024 / 1024
        print(f"Saved: {out_path} ({size:.1f} MB)")

    else:
        print("""QQ Music CLI for OpenClaw

Usage: qqmusic.py <command> [args]

Auth:
  login                     Login via browser cookie (paste)
  login-qr                  Login via QQ QR code scan
  status                    Check login status

Browse:
  search <query>            Search songs
  search-albums <query>     Search albums
  playlists                 Your playlists (needs login)
  playlist <id>             Tracks in a playlist

Audio:
  url <songmid>             Get audio URL
  play <mid|query>          Open in browser
  download <mid|query> [dir] Download audio

Notes:
  - Search works without login
  - Playlists/download may require login (cookie)
  - VIP tracks may not be downloadable
""")
