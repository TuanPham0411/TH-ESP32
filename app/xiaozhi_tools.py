"""Public, free XiaoZhi tools. No subscription, device licence or parent-site lookup."""
from __future__ import annotations
import html,hashlib,json,os,re,secrets,subprocess,threading,time
from pathlib import Path
import urllib.parse,urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from flask import Blueprint,Response,jsonify,request,stream_with_context

USER_AGENT='TH-ESP32-Tools/1.0'
CACHE={}
CACHE_LOCK=threading.Lock()
SESSION_LOCK=threading.Lock()
SESSIONS={}
MUSIC_SESSION_DIR=Path(os.environ.get('DATA_DIR',str(Path(__file__).resolve().parents[1]/'data')))/'music_sessions'
TOOLS={
    "prepare_music": "Chuẩn bị luồng nhạc Opus riêng cho loa robot.",
    "search_web": "Tra cứu thông tin trên Internet.",
    "get_latest_news": "Cập nhật tin tức mới theo chủ đề.",
    "get_gold_price": "Tra cứu thông tin giá vàng mới nhất tại Việt Nam.",
    "get_fuel_price": "Tra cứu thông tin giá xăng dầu mới nhất tại Việt Nam.",
    "search_music": "Tìm bài hát, nghệ sĩ và bản nghe thử hợp pháp.",
    "chat_with_gpt": "Trò chuyện tiếng Việt với GPT qua OpenAI Responses API.",
    "search_youtube_music": "Tìm video nhạc bằng YouTube Data API chính thức.",
}

def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def _fetch(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"upstream HTTP {response.status}")
        return response.read(1_000_001)

def _cached(key: str, ttl: int, loader):
    now = time.monotonic()
    with CACHE_LOCK:
        hit = CACHE.get(key)
        if hit and hit[0] > now:
            result = dict(hit[1])
            result["cached"] = True
            return result
    result = loader()
    result["cached"] = False
    with CACHE_LOCK:
        CACHE[key] = (now + ttl, result)
    return result

def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", value).strip()

def _normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9A-Fa-f]", "", value or "").upper()
    if len(compact) != 12:
        return ""
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2))

def _rss(query: str, limit: int = 5) -> dict:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi"
    root = ET.fromstring(_fetch(url))
    items = []
    for node in root.findall("./channel/item")[:limit]:
        source = node.find("source")
        items.append(
            {
                "title": _clean(node.findtext("title", "")),
                "url": node.findtext("link", ""),
                "source": _clean(source.text if source is not None else "Google News"),
                "published_at": node.findtext("pubDate", ""),
            }
        )
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(item["title"] for item in items[:3]),
        "items": items,
        "updated_at": _now(),
    }

def _search(query: str, limit: int = 5) -> dict:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    body = _fetch(url).decode("utf-8", "replace")
    pattern = re.compile(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        re.I | re.S,
    )
    items = []
    for href, title, snippet in pattern.findall(body)[:limit]:
        parsed = urllib.parse.urlparse(html.unescape(href))
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
        items.append({"title": _clean(title), "url": target, "snippet": _clean(snippet)})
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(item["title"] for item in items[:3]),
        "items": items,
        "updated_at": _now(),
    }

def _music(query: str, limit: int = 5) -> dict:
    url = (
        "https://itunes.apple.com/search?country=VN&media=music&entity=song&limit="
        + str(limit)
        + "&term="
        + urllib.parse.quote_plus(query)
    )
    payload = json.loads(_fetch(url).decode("utf-8"))
    items = [
        {
            "title": item.get("trackName", ""),
            "artist": item.get("artistName", ""),
            "album": item.get("collectionName", ""),
            "url": item.get("trackViewUrl", ""),
            "preview_url": item.get("previewUrl", ""),
        }
        for item in payload.get("results", [])[:limit]
    ]
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(f'{x["title"]} — {x["artist"]}' for x in items[:3]),
        "items": items,
        "updated_at": _now(),
    }

def _gpt(message: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    payload = json.dumps(
        {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "instructions": (
                "Bạn là trợ lý tiếng Việt của robot Copper. Trả lời tự nhiên, chính xác, "
                "ngắn gọn để đọc TTS; không khẳng định dữ liệu thời gian thực nếu chưa tra cứu."
            ),
            "input": message,
            "max_output_tokens": 500,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read(1_000_001).decode("utf-8"))
    texts = []
    for output in result.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(content["text"])
    answer = "\n".join(texts).strip()
    if not answer:
        raise RuntimeError("OpenAI response contained no output text")
    return {
        "ok": True,
        "summary_vi": answer,
        "model": result.get("model", ""),
        "response_id": result.get("id", ""),
        "updated_at": _now(),
    }

def _youtube_music(query: str, limit: int = 5) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is not configured")
    params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "type": "video",
            "videoCategoryId": "10",
            "maxResults": limit,
            "q": query,
            "regionCode": "VN",
            "relevanceLanguage": "vi",
            "key": api_key,
        }
    )
    payload = json.loads(_fetch("https://www.googleapis.com/youtube/v3/search?" + params).decode())
    items = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId", "")
        snippet = item.get("snippet", {})
        if video_id:
            items.append(
                {
                    "title": _clean(snippet.get("title", "")),
                    "channel": _clean(snippet.get("channelTitle", "")),
                    "video_id": video_id,
                    "url": "https://www.youtube.com/watch?v=" + video_id,
                    "published_at": snippet.get("publishedAt", ""),
                }
            )
    return {
        "ok": True,
        "query": query,
        "summary_vi": " | ".join(f'{x["title"]} — {x["channel"]}' for x in items[:3]),
        "items": items,
        "playback_supported": False,
        "playback_note_vi": (
            "Firmware chỉ phát OGG/Opus trong /ai-music; không tải hoặc giải mã luồng YouTube."
        ),
        "updated_at": _now(),
    }

def register_xiaozhi_tools(app):
    bp=Blueprint('xiaozhi_tools',__name__,url_prefix='/api/xiaozhi')

    @bp.get('/health')
    def health():
        return jsonify(ok=True,service='th-esp32-tools',tools=len(TOOLS))

    @bp.get('/tools/list')
    def list_tools():
        return jsonify(ok=True,tools=[{'name':name,'description':value} for name,value in TOOLS.items()])

    @bp.get("/music/<session_id>/stream.ogg")
    def music_stream(session_id: str):
        token = request.args.get("token", "")
        with SESSION_LOCK:
            state = dict(SESSIONS.get(session_id, {}))
        session_file = MUSIC_SESSION_DIR / f"{session_id}.json"
        if session_file.is_file():
            try:
                state = json.loads(session_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
        if not token or not secrets.compare_digest(token, state.get("music_token", "")):
            return jsonify(ok=False, error="invalid music session"), 403
        source = state.get("music_source", "")
        if not source.startswith("https://audio-ssl.itunes.apple.com/"):
            return jsonify(ok=False, error="music source unavailable"), 404

        def generate():
            process = subprocess.Popen(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", source, "-vn",
                 "-ac", "1", "-ar", "24000", "-c:a", "libopus", "-b:a", "48k",
                 "-frame_duration", "60", "-f", "ogg", "pipe:1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            finally:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

        return Response(stream_with_context(generate()), mimetype="audio/ogg",
                        headers={"Cache-Control": "no-store", "X-Xiaozhi-Session": session_id})

    @bp.post("/tools/call")
    def call_tool():
        session_id=request.headers.get('X-Xiaozhi-Session') or secrets.token_urlsafe(16)
        if not re.fullmatch(r'[A-Za-z0-9._:-]{8,80}',session_id):
            return jsonify(ok=False,error='invalid session ID'),400
        body=request.get_json(silent=True)
        if not isinstance(body,dict):
            return jsonify(ok=False,error='JSON object required'),400
        name=str(body.get('name',''))[:64]
        args=body.get('arguments') if isinstance(body.get('arguments'),dict) else {}
        query=str(args.get('query') or args.get('topic') or '').strip()[:240]
        try:
            limit=max(1,min(int(args.get('limit',5)),8))
        except (TypeError,ValueError):
            return jsonify(ok=False,error='invalid limit'),400
        try:
            if name == "search_web" and query:
                result = _cached(f"search:{query}:{limit}", 300, lambda: _search(query, limit))
            elif name == "get_latest_news":
                query = query or "tin tức Việt Nam mới nhất when:1d"
                result = _cached(f"news:{query}:{limit}", 300, lambda: _rss(query, limit))
            elif name == "get_gold_price":
                query = "giá vàng SJC hôm nay Việt Nam when:1d"
                result = _cached("gold", 300, lambda: _rss(query, limit))
            elif name == "get_fuel_price":
                query = "giá xăng dầu mới nhất Việt Nam when:7d"
                result = _cached("fuel", 900, lambda: _rss(query, limit))
            elif name == "search_music" and query:
                result = _cached(f"music:{query}:{limit}", 3600, lambda: _music(query, limit))
            elif name == "prepare_music" and query:
                music = _music(query, 1)
                item = next((x for x in music.get("items", []) if x.get("preview_url")), None)
                if not item:
                    raise RuntimeError("no playable music result")
                token = secrets.token_urlsafe(24)
                with SESSION_LOCK:
                    SESSIONS[session_id] = {
                        "music_source": item["preview_url"], "music_token": token,
                        "updated_at": _now(),
                    }
                    MUSIC_SESSION_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
                    session_file = MUSIC_SESSION_DIR / f"{session_id}.json"
                    temporary = session_file.with_suffix(".tmp")
                    temporary.write_text(json.dumps(SESSIONS[session_id]), encoding="utf-8")
                    os.chmod(temporary, 0o600)
                    temporary.replace(session_file)
                result = {
                    "ok": True, "title": item.get("title", ""),
                    "artist": item.get("artist", ""),
                    "stream_url": (
                        f"{(app.config.get('PUBLIC_URL') or request.url_root.rstrip('/'))}/api/xiaozhi/music/{session_id}/stream.ogg?"
                        + urllib.parse.urlencode({"token": token})
                    ),
                    "format": "Ogg Opus 24 kHz mono", "output": "robot_speaker",
                    "updated_at": _now(),
                }
            elif name == "chat_with_gpt" and query:
                result = _gpt(query)
            elif name == "search_youtube_music" and query:
                result = _cached(
                    f"youtube:{query}:{limit}", 900, lambda: _youtube_music(query, limit)
                )
            else:
                return jsonify(ok=False, error="unknown tool or missing query"), 400
            with SESSION_LOCK:
                state = SESSIONS.setdefault(session_id, {})
                state.update({"last_tool": name, "last_query": query, "updated_at": _now()})
                if len(SESSIONS) > 2048:
                    oldest = next(iter(SESSIONS))
                    SESSIONS.pop(oldest, None)
            result["session_id"] = session_id
            result["tool"] = name
            return jsonify(result)
        except RuntimeError as exc:
            if 'is not configured' in str(exc):
                return jsonify(ok=False,tool=name,error='This optional upstream provider is not configured'),503
            app.logger.warning('XiaoZhi upstream unavailable for %s',name)
            return jsonify(ok=False,tool=name,error='upstream unavailable'),502
        except Exception:
            app.logger.warning('XiaoZhi upstream unavailable for %s',name)
            return jsonify(ok=False, tool=name, error="upstream unavailable", updated_at=_now()), 502

    app.register_blueprint(bp)
