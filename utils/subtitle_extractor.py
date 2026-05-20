import json
import re
import shutil
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
from urllib.request import Request, urlopen
from utils.logger import logger

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import httpx
except ImportError:
    httpx = None


LogFn = Callable[[str], None]


class ExtractionError(Exception):
    pass


@dataclass
class ExtractResult:
    title: str
    video_id: str
    source: str
    transcript_text: str
    raw_subtitle_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None


SUPPORTED_EXTS = {".srt", ".vtt", ".json", ".txt"}
AUDIO_EXTS = {".m4a", ".mp3", ".webm", ".wav", ".mp4", ".aac", ".flac", ".ogg", ".opus"}
DEFAULT_LANGS = "zh.*,zh-CN,zh-Hans,zh-Hant,en.*"


def ensure_dependency() -> None:
    if yt_dlp is None:
        raise ExtractionError("缺少 yt-dlp。请先运行: pip install yt-dlp")


def is_bilibili_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "bilibili.com" in host or "b23.tv" in host


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] or "video"


def parse_langs(lang_text: str) -> List[str]:
    return [item.strip() for item in lang_text.split(",") if item.strip()]


def choose_best_file(candidates: list[Path]) -> Optional[Path]:
    ranked: List[tuple[int, Path]] = []
    for path in candidates:
        score = 0
        suffix = path.suffix.lower()
        if suffix == ".srt":
            score += 4
        elif suffix == ".vtt":
            score += 3
        elif suffix == ".json":
            score += 2
        elif suffix == ".txt":
            score += 1
        ranked.append((score, path))
    if not ranked:
        return None
    ranked.sort(key=lambda x: (x[0], x[1].stat().st_size if x[1].exists() else 0), reverse=True)
    return ranked[0][1]


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_srt(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        lines.append(line)
    return clean_transcript("\n".join(lines))


def parse_vtt(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("WEBVTT") or upper.startswith("NOTE"):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    return clean_transcript("\n".join(lines))


def parse_json_subtitle(text: str) -> str:
    data = json.loads(text)
    body = data.get("body") if isinstance(data, dict) else None
    if isinstance(body, list):
        joined = "\n".join(
            str(item.get("content", "")).strip()
            for item in body
            if isinstance(item, dict) and str(item.get("content", "")).strip()
        )
        return clean_transcript(joined)
    if isinstance(data, dict):
        for key in ("text", "content", "transcript"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return clean_transcript(value)
    raise ExtractionError("字幕 JSON 格式无法识别。")


def subtitle_file_to_text(path: Path) -> str:
    raw = _read_text(path)
    suffix = path.suffix.lower()
    if suffix == ".srt":
        return parse_srt(raw)
    if suffix == ".vtt":
        return parse_vtt(raw)
    if suffix == ".json":
        return parse_json_subtitle(raw)
    return clean_transcript(raw)


def clean_transcript(text: str) -> str:
    lines = []
    last = None
    for raw in text.splitlines():
        line = re.sub(r"<[^>]+>", "", raw)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if line == last:
            continue
        lines.append(line)
        last = line
    return "\n".join(lines).strip()


def fetch_info(url: str, cookie: Optional[str] = None) -> dict:
    ensure_dependency()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        },
    }
    if cookie:
        opts["http_headers"]["Cookie"] = cookie
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise ExtractionError("无法读取视频信息。")
    return info


def _fetch_subtitles_from_bilibili_api(
    url: str,
    cookie: Optional[str],
    log: LogFn,
) -> Optional[Path]:
    if httpx is None:
        log("缺少 httpx，无法使用 B站 API 获取字幕")
        return None

    bv_id = url.split("/video/")[-1].split("?")[0].strip()
    if not bv_id.startswith("BV"):
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    if cookie:
        headers["Cookie"] = cookie

    try:
        view_url = "https://api.bilibili.com/x/web-interface/view"
        resp = httpx.get(view_url, params={"bvid": bv_id}, headers=headers, timeout=10)
        data = resp.json()
        cid = data.get("data", {}).get("cid")
        if not cid:
            return None
    except Exception as exc:
        log(f"B站 API 获取视频信息失败：{exc}")
        return None

    try:
        player_url = "https://api.bilibili.com/x/player/v2"
        resp2 = httpx.get(player_url, params={"cid": cid, "bvid": bv_id}, headers=headers, timeout=10)
        player_data = resp2.json()
    except Exception as exc:
        log(f"B站 player/v2 API 失败：{exc}")
        return None

    subtitles_data = player_data.get("data", {}).get("subtitle", {})
    if not subtitles_data:
        return None

    subtitle_list = subtitles_data.get("subtitles", []) or subtitles_data.get("list", [])
    if not subtitle_list:
        return None

    user_subtitle = None
    for _ in range(5):
        for sub in subtitle_list:
            sub_url = sub.get("subtitle_url", "")
            if not sub_url:
                continue
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url
            lan = sub.get("lan", "unknown")
            sub_type = sub.get("type", -1)
            if sub_type == 0 and lan in ("zh", "zh-CN", "zh-Hans", "zh-Hant"):
                user_subtitle = (sub, sub_url, lan)
                break
        if user_subtitle:
            break
        import time
        time.sleep(0.3)
        resp_retry = httpx.get(player_url, params={"cid": cid, "bvid": bv_id}, headers=headers, timeout=10)
        player_data = resp_retry.json()
        subtitles_data = player_data.get("data", {}).get("subtitle", {})
        subtitle_list = subtitles_data.get("subtitles", []) or subtitles_data.get("list", [])

    if user_subtitle:
        best_sub, sub_url, lan = user_subtitle
        _priority = 0
    else:
        for sub in subtitle_list:
            sub_url = sub.get("subtitle_url", "")
            if not sub_url:
                continue
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url
            lan = sub.get("lan", "unknown")
            sub_type = sub.get("type", -1)
            if sub_type == 1:
                best_sub = sub
                _priority = 1
                break
        else:
            return None

    if cookie and len(cookie) > 50:
        output_dir = Path("data/subtitles")
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = sanitize_filename(bv_id)
        out_path = output_dir / f"{safe_title}.{lan}.json"

        try:
            req = Request(sub_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=60) as resp, out_path.open("wb") as f:
                shutil.copyfileobj(resp, f)
            log(f"通过 B站 API 获取字幕：{lan} (优先级: {'用户' if _priority == 0 else 'AI'})")
            return out_path
        except Exception as exc:
            log(f"字幕下载失败：{exc}")
            return None

    return None


def _matches_any_lang(lang: str, preferred_langs: List[str]) -> bool:
    return any(
        re.fullmatch(pattern.replace("*", ".*"), lang) or re.search(pattern, lang)
        for pattern in preferred_langs
    )


def try_direct_subtitle_from_info(
    info: dict,
    output_dir: Path,
    preferred_langs: List[str],
    log: LogFn,
) -> Optional[Path]:
    candidates = []
    for source_name in ("subtitles", "automatic_captions"):
        source = info.get(source_name)
        if not isinstance(source, dict):
            continue
        for lang, entries in source.items():
            if isinstance(entries, list):
                for item in entries:
                    if not isinstance(item, dict):
                        continue
                    subtitle_url = item.get("url")
                    ext = item.get("ext") or "json"
                    if subtitle_url:
                        candidates.append(
                            (lang, ext, subtitle_url, source_name, _matches_any_lang(lang, preferred_langs))
                        )
    if not candidates:
        return None

    def lang_score(lang: str, matched: bool) -> int:
        score = 50 if matched else 0
        for idx, pattern in enumerate(preferred_langs):
            regex = pattern.replace("*", ".*")
            if re.fullmatch(regex, lang) or re.search(regex, lang):
                score = max(score, 100 - idx)
        if lang.startswith("zh"):
            score += 20
        elif lang.startswith("en"):
            score += 10
        return score

    def ext_score(ext: str) -> int:
        mapping = {"srt": 4, "vtt": 3, "json": 2, "txt": 1}
        return mapping.get(ext.lower(), 0)

    candidates.sort(
        key=lambda item: (lang_score(item[0], item[4]), ext_score(item[1]), 1 if item[3] == "subtitles" else 0),
        reverse=True,
    )
    lang, ext, sub_url, source_name, _matched = candidates[0]
    safe_title = sanitize_filename(str(info.get("title") or info.get("id") or "video"))
    out_path = output_dir / f"{safe_title}.{lang}.{ext}"
    log(f"找到{source_name}：{lang} ({ext})")
    req = Request(sub_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp, out_path.open("wb") as f:
        shutil.copyfileobj(resp, f)
    return out_path


def try_download_subtitle_with_ytdlp(
    url: str,
    output_dir: Path,
    preferred_langs: List[str],
    cookie: Optional[str],
    log: LogFn,
) -> Optional[Path]:
    ensure_dependency()
    before = set(output_dir.rglob("*"))
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": preferred_langs,
        "subtitlesformat": "srt/vtt/best",
        "paths": {"home": str(output_dir), "subtitle": str(output_dir)},
        "outtmpl": {"default": "%(title).80s [%(id)s].%(ext)s"},
        "compat_opts": ["no-live-chat"],
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": False,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        },
    }
    if cookie:
        opts["http_headers"]["Cookie"] = cookie
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        log(f"yt-dlp 直接下载字幕失败：{exc}")
        return None
    after = set(output_dir.rglob("*"))
    new_files = [p for p in after - before if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    return choose_best_file(new_files)


def download_audio(
    url: str,
    output_dir: Path,
    cookie: Optional[str],
    log: LogFn,
) -> Path:
    ensure_dependency()
    video_id = url.split('/video/')[-1].split('?')[0].strip()
    
    existing = list(output_dir.glob(f"*{video_id}*.m4a"))
    if existing:
        log(f"音频已存在：{existing[0].name}")
        return existing[0]
    
    before = set(output_dir.rglob("*"))
    opts = {
        "format": "bestaudio/best",
        "paths": {"home": str(output_dir)},
        "outtmpl": {"default": "%(title).80s [%(id)s].%(ext)s"},
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        },
    }
    if cookie:
        opts["http_headers"]["Cookie"] = cookie
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    after = set(output_dir.rglob("*"))
    new_files = [p for p in after - before if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    chosen = choose_best_file(new_files)
    if not chosen:
        raise ExtractionError("音频下载完成，但没有找到音频文件。")
    log(f"音频已下载：{chosen.name}")
    return chosen


def transcribe_audio(
    audio_path: Path,
    model_size: str,
    device: str,
    log: LogFn,
) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ExtractionError("缺少 faster-whisper。请先运行: pip install faster-whisper") from exc

    compute_type = "int8"
    actual_device = device
    if device == "auto":
        try:
            import torch
            actual_device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            actual_device = "cpu"

    if actual_device == "cuda":
        compute_type = "float16"

    local_model_path = Path(__file__).parent.parent / "whisper_model"
    log(f"开始加载模型：model={local_model_path}, device={actual_device}, compute_type={compute_type}")
    
    if local_model_path.exists():
        model = WhisperModel(str(local_model_path), device=actual_device, compute_type=compute_type, local_files_only=True)
    else:
        log("未找到本地模型，使用默认方式加载...")
        model = WhisperModel(model_size, device=actual_device, compute_type=compute_type)
    
    log("模型加载完成，开始转写。首次运行可能需要更久。")

    segments, info = model.transcribe(str(audio_path), vad_filter=False)
    chunks: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        text = seg.text.strip()
        if text:
            chunks.append(text)
        if idx % 20 == 0:
            log(f"转写中：已处理约 {idx} 个片段...")

    text = "\n".join(chunks)
    if not text.strip():
        raise ExtractionError("转写结果为空。")
    lang = getattr(info, "language", "unknown")
    prob = getattr(info, "language_probability", None)
    if prob is not None:
        log(f"检测语言：{lang} (置信度 {prob:.2f})")
    else:
        log(f"检测语言：{lang}")
    return clean_transcript(text)


def save_transcript(output_dir: Path, title: str, text: str) -> Path:
    safe_title = sanitize_filename(title)
    out = output_dir / f"{safe_title}.transcript.txt"
    out.write_text(text, encoding="utf-8")
    return out


class SubtitleExtractor:
    def __init__(self, cookie: Optional[str] = None, proxy: Optional[str] = None):
        from utils.app_data import APP_DATA_DIR
        if cookie is None:
            cookie_path = APP_DATA_DIR / "login_cookie.txt"
            if cookie_path.exists():
                cookie = cookie_path.read_text().strip()
        self.cookie = cookie if cookie and len(cookie) > 50 else None
        self.proxy = proxy
        self.output_dir = APP_DATA_DIR / "subtitles"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if proxy:
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy

    def _log(self, msg: str) -> None:
        logger.info(msg)

    def extract(self, url: str, preferred_langs: str = DEFAULT_LANGS) -> Optional[ExtractResult]:
        if not is_bilibili_url(url):
            logger.error(f"不是B站链接: {url}")
            return None

        langs = parse_langs(preferred_langs)
        self._log(f"读取视频信息: {url}")
        try:
            info = fetch_info(url, cookie=self.cookie)
        except ExtractionError as e:
            logger.error(f"获取视频信息失败: {e}")
            return None

        title = str(info.get("title") or "Bilibili Video")
        video_id = str(info.get("id") or "unknown")
        self._log(f"标题：{title}")
        self._log(f"视频 ID：{video_id}")

        subtitle_path = None

        if self.cookie and len(self.cookie) > 50:
            self._log("尝试通过 B站 API 获取字幕...")
            subtitle_path = _fetch_subtitles_from_bilibili_api(url, self.cookie, self._log)

        if subtitle_path is None:
            self._log("尝试通过 yt-dlp 获取字幕...")
            subtitle_path = try_download_subtitle_with_ytdlp(url, self.output_dir, langs, self.cookie, self._log)

        if subtitle_path and subtitle_path.exists():
            text = subtitle_file_to_text(subtitle_path)
            transcript_path = save_transcript(self.output_dir, title, text)
            self._log(f"字幕提取完成：{subtitle_path.name}")
            return ExtractResult(
                title=title,
                video_id=video_id,
                source="subtitle",
                transcript_text=text,
                raw_subtitle_path=str(subtitle_path),
                transcript_path=str(transcript_path),
            )

        self._log("没有找到可用字幕，开始下载音频并转写...")
        try:
            audio_path = download_audio(url, self.output_dir, self.cookie, self._log)
        except ExtractionError as e:
            logger.error(f"音频下载失败: {e}")
            return None

        text = transcribe_audio(audio_path, "small", "auto", self._log)
        transcript_path = save_transcript(self.output_dir, title, text)
        self._log("语音转写完成。")
        return ExtractResult(
            title=title,
            video_id=video_id,
            source="whisper",
            transcript_text=text,
            audio_path=str(audio_path),
            transcript_path=str(transcript_path),
        )

    def extract_text(self, url: str) -> str:
        result = self.extract(url)
        if result:
            return result.transcript_text
        return ""


subtitle_extractor = SubtitleExtractor()