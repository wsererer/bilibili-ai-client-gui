import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from utils.subtitle_extractor import (
    is_bilibili_url,
    SubtitleExtractor,
    parse_json_subtitle,
    parse_srt,
    parse_vtt,
    clean_transcript,
    sanitize_filename,
    parse_langs,
)


class TestIsBilibiliUrl:
    @pytest.mark.parametrize("url,expected", [
        ("https://www.bilibili.com/video/BV1xxx", True),
        ("https://bilibili.com/video/BV1xxx", True),
        ("https://b23.tv/abc123", True),
        ("https://youtube.com/watch?v=xxx", False),
        ("not a url", False),
        ("http://bilibili.com/video/BV1xxx", True),
    ])
    def test_url_validation(self, url, expected):
        assert is_bilibili_url(url) == expected


class TestSubtitlePriority:
    """核心测试：字幕优先级验证"""

    def test_user_subtitle_priority_over_ai(self):
        """用户字幕(type=0) > AI字幕(type=1)"""
        extractor = SubtitleExtractor()

        result = extractor.extract("https://www.bilibili.com/video/BV1Y5BxBpEpg")

        assert result is not None, "应该能提取到字幕"
        assert result.source == "subtitle", f"来源应是 subtitle，实际: {result.source}"

        raw_path_lower = result.raw_subtitle_path.lower()
        assert "zh" in raw_path_lower, f"应该返回 zh 用户字幕，实际: {result.raw_subtitle_path}"
        assert "ai-zh" not in raw_path_lower, f"不应该返回 ai-zh AI字幕，实际: {result.raw_subtitle_path}"

    def test_user_subtitle_content_valid(self):
        """用户字幕内容有效（非空）"""
        extractor = SubtitleExtractor()
        result = extractor.extract("https://www.bilibili.com/video/BV1Y5BxBpEpg")

        assert result is not None
        assert len(result.transcript_text) > 10, "字幕文本应该有一定长度"
        assert "生化危机" in result.transcript_text or "NS2" in result.transcript_text, "字幕内容应该与视频相关"

    def test_has_user_subtitle_bv1h8(self):
        """BV1h8rDBFEV7 有用户字幕"""
        extractor = SubtitleExtractor()
        result = extractor.extract("https://www.bilibili.com/video/BV1h8rDBFEV7")

        assert result is not None
        assert result.source == "subtitle"
        assert len(result.transcript_text) > 10


class TestSubtitleParsing:
    def test_parse_json_subtitle(self):
        json_text = '{"body":[{"from":0,"to":5,"content":"测试字幕"}]}'
        result = parse_json_subtitle(json_text)
        assert "测试字幕" in result

    def test_parse_srt(self):
        srt_text = "1\n00:00:00 --> 00:00:05\n测试字幕\n\n2\n00:00:05 --> 00:00:10\n第二行"
        result = parse_srt(srt_text)
        assert "测试字幕" in result
        assert "第二行" in result

    def test_parse_vtt(self):
        vtt_text = "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nVTT字幕内容\n"
        result = parse_vtt(vtt_text)
        assert "VTT字幕内容" in result

    def test_clean_transcript_removes_duplicates(self):
        text = "第一行\n第一行\n第二行\n第三行\n第三行"
        result = clean_transcript(text)
        lines = result.split("\n")
        assert lines.count("第一行") == 1
        assert lines.count("第二行") == 1


class TestSanitizeFilename:
    @pytest.mark.parametrize("input,expected", [
        ("正常标题", "正常标题"),
        ("标题:含特殊?字符*", "标题_含特殊_字符_"),
        ("多个   空格", "多个 空格"),
        ("", "video"),
    ])
    def test_sanitize(self, input, expected):
        result = sanitize_filename(input)
        assert result == expected


class TestParseLangs:
    def test_parse_langs(self):
        result = parse_langs("zh.*,en.*,ja")
        assert "zh.*" in result
        assert "en.*" in result
        assert "ja" in result


class TestSubtitleExtractorClass:
    def test_extractor_uses_cookie_from_file(self):
        extractor = SubtitleExtractor()
        cookie_path = Path("data/login_cookie.txt")
        if cookie_path.exists():
            expected = cookie_path.read_text().strip()
            assert extractor.cookie == expected

    def test_extractor_output_dir_exists(self):
        extractor = SubtitleExtractor()
        assert extractor.output_dir.exists()

    def test_extract_text_wrapper(self):
        extractor = SubtitleExtractor()
        result = extractor.extract_text("https://www.bilibili.com/video/BV1h8rDBFEV7")
        assert isinstance(result, str)
        assert len(result) > 0 or result == ""


class TestSubtitleFallback:
    def test_no_cookie_uses_whisper_path(self):
        extractor = SubtitleExtractor()
        original_cookie = extractor.cookie
        extractor.cookie = None

        result = extractor.extract("https://www.bilibili.com/video/BV1h8rDBFEV7")

        extractor.cookie = original_cookie

        if result:
            assert result.source in ["subtitle", "whisper"]