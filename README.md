# 🎧 OpenClaw Ears

Audio superpowers for [OpenClaw](https://github.com/openclaw/openclaw) agents — multi-platform music, system audio capture, and podcast/video transcription.

Seven tools, one goal: **let your AI agent hear the world.**

## What's Inside

| Tool | What it does |
|------|-------------|
| 🎵 **spotify.py** | Spotify — search, playlists, playback via Spotify Connect |
| 🎵 **netease.py** | 网易云音乐 — search, download, play (320kbps) |
| 🎵 **ytmusic.py** | YouTube Music — search, playlists, download via yt-dlp |
| 🎵 **applemusic.py** | Apple Music — search, preview, Music.app integration |
| 🎵 **qqmusic.py** | QQ 音乐 — search (download blocked by anti-scraping) |
| 🎤 **audiosnap** | Record system audio on macOS (no virtual drivers needed) |
| 🎙️ **podsnap** | Download + transcribe from YouTube, 小宇宙, Bilibili, etc. |

### Platform Capabilities

```
              Search  Playlists  Download  Playback
网易云          ✅       ✅         ✅        ✅ (afplay, full tracks)
Spotify        ✅       ✅         ❌        ✅ (Connect, remote)
YouTube Music  ✅       ✅         ✅        ⚠️ (yt-dlp + browser)
Apple Music    ✅       ❌         ⚠️        ⚠️ (Music.app, manual)
QQ 音乐        ✅       ⚠️         ❌        ❌
```

---

## 🎵 Spotify

Control Spotify playback via the Web API.

### Setup

1. Create a Spotify app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
   - Redirect URI: `http://127.0.0.1:8989/login`
   - Enable **Web API**
2. Configure:
   ```bash
   python3 scripts/spotify.py config --client-id YOUR_CLIENT_ID
   python3 scripts/spotify.py auth
   ```

### Commands

```bash
spotify.py now                       # What's playing
spotify.py play "Björk"              # Search and play
spotify.py pause / next / prev       # Playback controls
spotify.py search "query"            # Search tracks
spotify.py top-tracks / top-artists  # Your top items
spotify.py recent                    # Recently played
spotify.py playlists                 # Your playlists
spotify.py devices                   # Available devices
spotify.py raw GET /me/player        # Direct API access
```

---

## 🎵 网易云音乐 (NetEase Cloud Music)

Full-featured CLI with search, download, and local playback.

### Setup

```bash
pip3 install pyncm
python3 scripts/netease.py login-qr   # Scan QR with 网易云 App
# or
python3 scripts/netease.py login <phone>  # SMS login
```

### Commands

```bash
netease.py status                    # Login status
netease.py search "JACE 大車"        # Search
netease.py play "Kiri T"             # Search → download → play
netease.py play 3318341860           # Play by track ID
netease.py playlists                 # Your playlists
netease.py playlist <id>             # Tracks in a playlist
netease.py likes                     # Your liked songs
netease.py recent                    # Recently played
netease.py download <id> [dir]       # Download track (320kbps)
netease.py download-playlist <id> [dir]  # Download entire playlist
netease.py url <id>                  # Get audio URL
netease.py play-mac toggle           # Media key: play/pause
netease.py play-mac next / prev      # Media key: next/previous
netease.py play-mac now              # Now playing info
```

### Notes

- Audio download at 320kbps, no DRM
- `play` command downloads to temp and plays via `afplay` (background, non-blocking)
- Media key controls work with any macOS music player (requires `brew install nowplaying-cli`)
- NeteaseMusic desktop app doesn't register macOS NowPlaying, so `now` may return empty

---

## 🎵 YouTube Music

Search, browse, and download via `ytmusicapi`.

### Setup

```bash
pip3 install ytmusicapi
python3 scripts/ytmusic.py auth      # Opens browser for OAuth
```

### Commands

```bash
ytmusic.py search "query"            # Search
ytmusic.py playlists                 # Your playlists
ytmusic.py playlist <id>             # Playlist tracks
ytmusic.py likes                     # Liked songs
ytmusic.py history                   # Play history
ytmusic.py artist <id>               # Artist info
ytmusic.py album <id>                # Album tracks
ytmusic.py download <video_id> [dir] # Download via yt-dlp
ytmusic.py play "query"              # Open in browser
```

### Requirements

- `ytmusicapi` — API client
- `yt-dlp` — for downloads (`brew install yt-dlp`)

---

## 🎵 Apple Music

Zero-config search via iTunes API. No login, no developer account needed.

### Commands

```bash
applemusic.py search "query"         # Search tracks
applemusic.py artist "name"          # Search artists
applemusic.py album "name"           # Search albums
applemusic.py preview "query"        # Play 30s preview (afplay)
applemusic.py play "query"           # Open in Music.app
applemusic.py now                    # Now playing in Music.app
applemusic.py toggle / next / prev   # Music.app controls
```

### Notes

- Search uses the free iTunes Search API — works everywhere, no auth
- Preview is 30 seconds only (API limitation)
- `play` opens the track in Music.app; requires Apple Music subscription for full playback
- Music.app AppleScript controls require macOS Automation permission

---

## 🎵 QQ 音乐

Search works without login. Personal library and downloads are heavily restricted.

### Commands

```bash
qqmusic.py search "query"            # Search (no login needed)
qqmusic.py login-cookie              # Login via browser cookie
qqmusic.py playlists                 # Your playlists (limited)
```

### Limitations

QQ Music has the strictest anti-scraping of all platforms:
- Audio URLs are IP+cookie bound — server-side download doesn't work
- Playlist details may return empty despite valid auth
- Search is the only reliable feature

---

## 🎤 audiosnap

Capture system audio on macOS using Apple's native [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit/). No BlackHole, no Soundflower, no kernel extensions.

### Why?

Virtual audio drivers like BlackHole break on every major macOS update. On macOS Tahoe, BlackHole is completely non-functional — the driver appears but passes zero audio. ScreenCaptureKit is Apple's official API and works reliably.

### Build & Install

```bash
cd audiosnap
swift build -c release
ln -s $(pwd)/.build/release/audiosnap /usr/local/bin/audiosnap
```

### Usage

```bash
audiosnap                                # Record 5s → audiosnap-output.wav
audiosnap 10 output.wav                  # Record 10s to file
audiosnap 30 meeting.wav --exclude-self  # Exclude own process audio
audiosnap 5 out.wav --sample-rate 44100 --channels 1
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `duration` | Recording duration in seconds | `5` |
| `output` | Output file path | `audiosnap-output.wav` |
| `--exclude-self` | Exclude this process's audio | off |
| `--sample-rate N` | Sample rate in Hz | `48000` |
| `--channels N` | Number of channels | `2` |

### TCC Permission Workaround

macOS requires Screen Recording permission. If running from a process that doesn't have it (like an AI agent daemon), use the wrapper:

```bash
./audiosnap/audiosnap-wrapper.sh 10 output.wav
```

### Requirements

- macOS 13 (Ventura) or later
- Screen Recording permission (prompted on first run)

---

## 🎙️ podsnap

Download and transcribe audio from podcasts, YouTube, and more — one command.

### Install

```bash
ln -s $(pwd)/audiosnap/podsnap.py /usr/local/bin/podsnap
```

### Usage

```bash
podsnap https://youtube.com/watch?v=xxx           # YouTube → transcript
podsnap https://xiaoyuzhoufm.com/episode/xxx      # 小宇宙 → transcript
podsnap https://bilibili.com/video/xxx            # Bilibili → transcript
podsnap https://example.com/podcast.mp3            # Direct URL → transcript
podsnap local-recording.mp3                        # Local file → transcript
```

### Options

```bash
podsnap URL -o audio.mp3              # Save audio to specific path
podsnap URL --no-transcribe           # Download only, skip transcription
podsnap URL -t transcript.txt         # Save transcript to file
podsnap URL --method mlx_whisper      # Use specific transcription engine
```

### Supported Sources

| Source | Method |
|--------|--------|
| 🎬 YouTube | yt-dlp |
| 📺 Bilibili | yt-dlp |
| 🎧 小宇宙 (Xiaoyuzhou FM) | Direct extraction |
| 🍎 Apple Podcasts | yt-dlp |
| 📡 RSS / Atom feeds | Direct download |
| 🔗 1000+ sites | [yt-dlp supported](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) |
| 🎵 Direct audio URLs | mp3, m4a, wav, ogg, opus, flac |
| 📁 Local files | Transcribe only |

### Transcription

podsnap auto-detects the best available transcription tool:
1. **groq-whisper** (cloud, fast) — preferred
2. **mlx_whisper** (local, Apple Silicon) — fallback

---

## 📦 Install All Dependencies

```bash
# Music platforms
pip3 install pyncm ytmusicapi

# Audio tools
brew install nowplaying-cli yt-dlp

# audiosnap (macOS system audio)
cd audiosnap && swift build -c release

# Transcription (optional)
pip3 install openai-whisper   # or mlx_whisper for Apple Silicon
```

---

## Use Cases

- 🤖 **AI agents** that can search, play, and download music across platforms
- 🎙️ **Podcast transcription** — give it a URL, get text
- 📝 **Meeting notes** — record system audio during calls
- 🎵 **Cross-platform music** — one CLI to rule them all
- 📚 **Video learning** — transcribe lectures and talks

## Origin Story

Born when BlackHole broke on macOS Tahoe and an AI agent wanted to listen to Björk. The agent wrote audiosnap in 160 lines of Swift, then kept going — Spotify, 网易云, YouTube Music, Apple Music, QQ 音乐, podcasts. Now it hears everything.

## License

MIT
