import yt_dlp
from urllib.parse import parse_qs, urlparse  # [New] URL 파싱용 모듈

class MetadataAnalyzer:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False, 
            'ignoreerrors': True,  
        }

    def get_video_info(self, url: str) -> dict:
        """
        URL을 받아 영상의 제목, 썸네일, 그리고 사용 가능한 포맷 리스트를 반환합니다.
        (재생목록인 경우, 첫 번째 유효한 영상의 포맷 정보를 반환합니다.)
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info: return None

                # [Case 1] 재생목록인 경우
                if info.get('_type') == 'playlist' or 'entries' in info:
                    valid_entry = None
                    if 'entries' in info:
                        for entry in info['entries']:
                            if entry and 'formats' in entry:
                                valid_entry = entry
                                break
                    
                    if not valid_entry:
                        return None
                    
                    return {
                        'id': info.get('id'),
                        'title': info.get('title'),
                        '_type': 'playlist',
                        'thumbnail': valid_entry.get('thumbnail'),
                        'duration': valid_entry.get('duration'),
                        'formats': self._parse_formats(valid_entry.get('formats', []))
                    }

                # [Case 2] 단일 영상인 경우
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    '_type': 'video',
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'view_count': info.get('view_count'),
                    'formats': self._parse_formats(info.get('formats', []))
                }

        except Exception as e:
            print(f"[Error] 메타데이터 분석 실패: {e}")
            return None

    def _parse_formats(self, raw_formats: list) -> dict:
        parsed = { 'video': [], 'audio': [] }

        for f in raw_formats:
            if not f.get('format_id') or not f.get('ext'): continue
            filesize = f.get('filesize') or f.get('filesize_approx') or 0

            # Audio Only
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                parsed['audio'].append({
                    'id': f['format_id'],
                    'ext': f['ext'],
                    'abr': f.get('abr', 0),
                    'codec': f.get('acodec'),
                    'asr': f.get('asr'),
                    'filesize': filesize
                })
            # Video
            elif f.get('vcodec') != 'none':
                if not f.get('height'): continue
                parsed['video'].append({
                    'id': f['format_id'],
                    'ext': f['ext'],
                    'res': f"{f.get('height')}p",
                    'fps': f.get('fps'),
                    'codec': f.get('vcodec'),
                    'vbr': f.get('vbr', 0),
                    'filesize': filesize,
                    'hdr': 'HDR' in f.get('dynamic_range', '') 
                })

        parsed['video'].sort(key=lambda x: (int(x['res'][:-1]), x['fps']), reverse=True)
        parsed['audio'].sort(key=lambda x: x['abr'] or 0, reverse=True)
        return parsed
    
    def get_playlist_items(self, url: str) -> list:
        """
        재생목록 URL을 받아 포함된 모든 영상의 정보(URL, 제목) 리스트를 반환합니다.
        """
        try:
            # [핵심 수정] URL에 'list=' 파라미터가 있다면 순수 재생목록 주소로 변환
            # (watch?v=...&list=... 형태를 playlist?list=... 형태로 변경)
            parsed_url = urlparse(url)
            qs = parse_qs(parsed_url.query)
            
            target_url = url
            if 'list' in qs:
                playlist_id = qs['list'][0]
                # 영상 ID가 섞여 있으면 yt-dlp가 헷갈려하므로 순수 playlist 주소로 변경
                target_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                # print(f"[Debug] 재생목록 순수 URL로 변환: {target_url}")

            list_opts = {
                'extract_flat': True, 
                'quiet': True,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(list_opts) as ydl:
                # 변환된 target_url 사용
                info = ydl.extract_info(target_url, download=False)
                
                if not info: return []
                
                items = []
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry: continue

                        video_url = entry.get('url')
                        if not video_url and entry.get('id'):
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"

                        if video_url:
                            items.append({
                                'url': video_url,
                                'title': entry.get('title', 'Unknown')
                            })
                return items
                
        except Exception as e:
            print(f"[Error] 재생목록 추출 실패: {e}")
            return []