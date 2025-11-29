import os
import time
import yt_dlp
from core.ffmpeg_handler import FFmpegHandler
from utils.history import log_success

class Downloader:
    def __init__(self, ffmpeg_handler: FFmpegHandler = None):
        self.ffmpeg_handler = ffmpeg_handler if ffmpeg_handler else FFmpegHandler()
        self.max_retries = 3

    def download(self, urls: list, output_dir: str, options: dict, progress_callback=None) -> list:
        results = []
        ydl_opts = self._build_ydl_opts(output_dir, options, progress_callback)
        
        if options.get('noplaylist'):
            ydl_opts['noplaylist'] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                retries = 0
                success = False
                
                while retries < self.max_retries:
                    try:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        final_path = self._get_actual_filename(filename, options)

                        # 심화 후처리 (Upscale, DSP 등)
                        # use_upscale도 여기서 처리해야 하므로 조건 추가
                        if options.get('use_enhance') or options.get('audio_channels') or options.get('use_upscale'):
                            print(f"[Post-Process] 심화 변환 시작: {final_path}")
                            temp_output = final_path.replace('.', '_fixed.')
                            
                            # FFmpegHandler 호출
                            if self.ffmpeg_handler.process_media([final_path], temp_output, options):
                                if os.path.exists(final_path): os.remove(final_path)
                                os.rename(temp_output, final_path)

                        log_success(info.get('title'), url, final_path)
                        
                        results.append({'status': 'success', 'filepath': final_path, 'title': info.get('title')})
                        success = True
                        break

                    except Exception as e:
                        retries += 1
                        print(f"[Warning] 다운로드 실패. 재시도 중 ({retries}/{self.max_retries})... 원인: {e}")
                        time.sleep(2)
                
                if not success:
                    print(f"[Error] 최종 실패: {url}")
                    results.append({'status': 'error', 'url': url, 'msg': "Max retries exceeded"})
        
        return results

    def _build_ydl_opts(self, output_dir: str, options: dict, progress_callback) -> dict:
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': os.path.dirname(self.ffmpeg_handler.ffmpeg_path),
            'progress_hooks': [],
            'postprocessors': [],
            'updatetime': False,
            'updatetime': False,
            'ignoreerrors': True,  # [New] 비공개 영상 등 에러 발생 시 건너뛰기
        }

        # --- [수정된 포맷 선택 로직] ---
        video_fmt = ""
        audio_fmt = ""
        
        # 1. 비디오 모드
        if options.get('ext') not in ['mp3', 'flac', 'wav', 'aac']:
            # 해상도 제약 조건 (이하 화질 선택)
            if options.get('height'):
                video_fmt = f"bestvideo[height<={options['height']}]"
            else:
                video_fmt = "bestvideo"
            
            # [핵심 수정] 오디오 반드시 추가
            audio_fmt = "+bestaudio/best"
            
            # 확장자 병합 설정
            user_ext = options.get('ext')
            use_original = options.get('use_original')

            if user_ext:
                ydl_opts['merge_output_format'] = user_ext
            elif use_original:
                pass # 원본 유지
            else:
                ydl_opts['merge_output_format'] = 'mp4' # 기본값
            
            # 최종 포맷 문자열 결합 (Video + Audio)
            ydl_opts['format'] = video_fmt + audio_fmt

        # 2. 오디오 모드
        else:
            ydl_opts['format'] = "bestaudio/best"
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.get('ext', 'mp3'),
                'preferredquality': str(options.get('audio_bitrate', 192)),
            })

        # 부가 기능
        if options.get('thumbnail'): ydl_opts['writethumbnail'] = True
        if options.get('subtitles'):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = ['ko', 'en']

        # 진행률 콜백
        if progress_callback:
            def hook(d):
                if d['status'] == 'downloading':
                    p_str = d.get('_percent_str', '0%').replace('%','')
                    try: percent = float(p_str)
                    except: percent = 0
                    progress_callback({
                        'status': 'downloading',
                        'percent': percent,
                        'speed': d.get('_speed_str'),
                        'filename': d.get('filename')
                    })
                elif d['status'] == 'finished':
                    progress_callback({'status': 'finished', 'filename': d.get('filename')})
            ydl_opts['progress_hooks'].append(hook)

        return ydl_opts

    def _get_actual_filename(self, prepared_filename, options):
        target_ext = options.get('ext')
        if target_ext:
            base, _ = os.path.splitext(prepared_filename)
            return f"{base}.{target_ext}"
        
        if not options.get('use_original') and options.get('ext') is None:
             base, _ = os.path.splitext(prepared_filename)
             return f"{base}.mp4"
             
        return prepared_filename