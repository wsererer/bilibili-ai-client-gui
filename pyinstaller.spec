# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

_datas = [
    ('bilibili-ai-client-gui/whisper_model', 'whisper_model'),
]

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # Application modules
        'config',
        'database',
        'services',
        'message_poller',
        'webhook_server',
        'mcp_server',
        'openclaw_trigger',
        'bilibili_login',

        # GUI modules
        'gui',
        'gui.app',
        'gui.main_window',
        'gui.signal_bus',
        'gui.theme',
        'gui.pages',
        'gui.pages.messages_page',
        'gui.pages.history_page',
        'gui.pages.stats_page',
        'gui.pages.logs_page',
        'gui.pages.settings_page',
        'gui.models',
        'gui.models.message_model',
        'gui.models.summary_model',
        'gui.models.whitelist_model',
        'gui.widgets',
        'gui.widgets.sidebar',
        'gui.widgets.log_panel',
        'gui.widgets.stat_card',
        'gui.widgets.summary_dialog',

        # Utils
        'utils',
        'utils.logger',
        'utils.subtitle_extractor',
        'utils.app_data',
        'utils.crypto',

        # Third-party
        'qasync',
        'httpx',
        'loguru',
        'flask',
        'qrcode',
        'PIL',
        'mcp',
        'mcp.server',
        'mcp.types',
        'yt_dlp',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BilibiliAIClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
