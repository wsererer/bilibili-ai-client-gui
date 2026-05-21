import httpx
import json
from config import config

bv_id = 'BV1h8rDBFEV7'
cookie = config.get('bili_auth', '')

headers = {'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'}
url = 'https://api.bilibili.com/x/web-interface/view'
params = {'bvid': bv_id}

resp = httpx.get(url, params=params, headers=headers, timeout=10)
data = resp.json()

subtitle = data.get('data', {}).get('subtitle', {})
sub_list = subtitle.get('list', [])

print('Found subtitles:')
for s in sub_list:
    lan = s.get('lan')
    url_val = s.get('subtitle_url', '')
    print(f'  lan={lan}, url_len={len(url_val)}')
    if url_val:
        print(f'    URL preview: {url_val[:80]}')