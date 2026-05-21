import httpx

cookie = 'SESSDATA=5cba1450,1794757055,4c657*52CjCSJEX_X2zm2TmZF568Dpz4bx9-U26XMRevr5joYYjFW3AhrwdMfJXVMy7zary0VosSVmY1SFVXTjJnanZPWGY0M1Q2WGM1VnhTSlcwYkJlVHp4VHdOeGktckEtMXFjRWhjNy12SWNHVWYzN2pWaGNkODFOX0RCR1ZDRFRoeFg5MHZyb1BjaHRnIIEC; bili_jct=4dc1c732544a43158bf1cdd3e1c762eb; DedeUserID=3706977582582494'
headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}

apis = [
    '/x/msgfeed/at',
    '/x/msgfeed/like',
    '/x/notify/feed/me',
    '/x/msg/chat/list',
]

for api in apis:
    try:
        resp = httpx.get(f'https://api.bilibili.com{api}', headers=headers, timeout=10)
        data = resp.json()
        code = data.get('code', -1)
        items = data.get('data', {}).get('items', [])
        print(f'{api}: status={resp.status_code}, code={code}, items_count={len(items)}')
        if items:
            print(f'  First item: {str(items[0])[:200]}')
    except Exception as e:
        print(f'{api}: ERROR - {e}')
