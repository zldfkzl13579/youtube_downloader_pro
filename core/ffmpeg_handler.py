import subprocess
import os
import shutil
import sys

class FFmpegHandler:
    def __init__(self):
        """
        시스템에 설치된 FFmpeg보다, 프로젝트 내부의 bin 폴더에 있는 FFmpeg를 우선적으로 사용합니다.
        """
        self.ffmpeg_path = self._find_ffmpeg_binary()
        self._check_ffmpeg()
    
    def _find_ffmpeg_binary(self) -> str | None:
        """FFmpeg 실행 파일의 경로를 찾습니다."""
        # 1. 현재 프로젝트의 bin 폴더 확인 (배포용/개발용)
        # 현재 파일(ffmpeg_handler.py)의 상위(core)의 상위(root) 폴더 기준
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 윈도우면 .exe, 맥/리눅스면 확장자 없음
        file_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        local_bin_path = os.path.join(base_path, 'bin', file_name)

        if os.path.exists(local_bin_path):
            print(f"[System] 내장 FFmpeg를 사용합니다: {local_bin_path}")
            return local_bin_path

        # 2. 없다면 시스템 환경변수(PATH) 확인 (개발자 컴퓨터용)
        if shutil.which("ffmpeg"):
            print("[System] 시스템(PATH)에 설치된 FFmpeg를 사용합니다.")
            return "ffmpeg"

        # 3. 둘 다 없으면 에러 (None 반환)
        return None

    def _check_ffmpeg(self):
        if not self.ffmpeg_path:
            raise FileNotFoundError(
                "[Error] FFmpeg를 찾을 수 없습니다.\n"
                "1. 프로젝트 내 'bin' 폴더에 ffmpeg.exe를 넣어주세요.\n"
                "2. 또는 시스템에 FFmpeg를 설치해주세요."
            )

    def process_media(self, input_files: list, output_path: str, options: dict):
        """
        입력된 미디어 파일들에 필터와 변환 옵션을 적용하여 최종 파일을 생성합니다.
        """
        cmd = [self.ffmpeg_path, '-y']
        for f in input_files: cmd.extend(['-i', f])

        # --- 비디오 필터 및 코덱 설정 ---
        vf_filters = []

        # 1. Upscale (강제 확대) 로직
        # 조건: upscale 키워드가 있고 + 목표 높이(height)가 설정되어 있어야 함
        if options.get('use_upscale') and options.get('height'):
            target_h = options['height']
            # Lanczos 알고리즘: 확대 시 화질 저하를 최소화하는 알고리즘
            # scale=-2:1080 -> 세로를 1080으로 맞추고 가로는 비율 유지 (짝수 단위)
            vf_filters.append(f"scale=-2:{target_h}:flags=lanczos")
            print(f"[Info] Video Upscale 적용: 높이 {target_h}p (Lanczos)")

        # 2. 비디오 코덱 및 필터 적용 여부 결정
        if vf_filters:
            # 필터가 하나라도 있으면 무조건 재인코딩(Re-encoding) 해야 함
            cmd.extend(['-vf', ','.join(vf_filters)])
            
            # 코덱 지정이 없으면 호환성 좋은 libx264 사용 (확대했으니 용량 관리를 위해)
            v_codec = options.get('video_codec', 'libx264')
            cmd.extend(['-c:v', v_codec])
            
            # h264/hevc 사용 시 픽셀 포맷 호환성 확보 (yuv420p)
            if 'libx264' in v_codec or 'libx265' in v_codec:
                cmd.extend(['-pix_fmt', 'yuv420p'])
        else:
            # 필터가 없으면 (단순 병합/변환)
            if len(input_files) > 1 and not options.get('video_codec'):
                 # 영상+오디오 병합 시 코덱 변경 요청이 없으면 '복사'하여 화질 저하 방지
                 cmd.extend(['-c:v', 'copy']) 
            elif options.get('video_codec'):
                 # 사용자가 특정 코덱(av1 등)을 명시한 경우
                 cmd.extend(['-c:v', options['video_codec']])
            # 그 외의 경우(단일 파일, 코덱 미지정)는 FFmpeg 기본값 따름

        # 3. 오디오 옵션 적용 (DSP, 비트레이트 등)
        cmd.extend(self._build_audio_options(options))
        
        cmd.append(output_path)

        # 4. 실행 및 로그 출력
        print(f"[FFmpeg] 처리 시작: {output_path}")
        
        try:
            # subprocess로 실행
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
            print("[FFmpeg] 변환 성공!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[Error] FFmpeg 변환 중 오류 발생: {e.stderr.decode('utf-8', errors='replace')}")
            return False

    def _build_audio_options(self, options: dict) -> list:
        """
        옵션 딕셔너리를 분석하여 오디오 관련 FFmpeg 인자 리스트를 생성합니다.
        (충돌 우선순위 및 DSP 로직 적용)
        """
        cmds = []
        ext = options.get('ext', 'mp3')
        
        # --- A. 오디오 필터 (DSP) ---
        af_filters = []
        
        # 1. 음질 향상 (Enhance) - Crystalizer
        if options.get('use_enhance'):
            # i=2.0 정도가 적당한 타격감
            af_filters.append("crystalizer=i=2.0")
            print("[Info] DSP: Crystalizer(음질 향상) 필터 적용됨")

        # 2. 오디오 채널 (Mono/Stereo/Surround)
        channels = options.get('audio_channels')
        if channels:
            if channels == '1': cmds.extend(['-ac', '1'])
            elif channels == '2': cmds.extend(['-ac', '2'])
            elif channels == '5.1': cmds.extend(['-ac', '6'])
            elif channels == '7.1': cmds.extend(['-ac', '8'])

        # 필터 체인 합치기
        if af_filters:
            cmds.extend(['-af', ','.join(af_filters)])

        # --- B. 충돌 우선순위 로직 (Hierarchy) ---
        # 손실 포맷 (mp3, aac, m4a, opus) -> 비트레이트 우선
        # 무손실 포맷 (wav, flac) -> 샘플링/비트뎁스 우선
        
        is_lossless = ext in ['wav', 'flac', 'alac', 'aiff']
        
        if is_lossless:
            # [무손실] 비트레이트 무시, 샘플링 속도 & 비트 깊이 적용
            if options.get('sample_rate'):
                cmds.extend(['-ar', str(options['sample_rate'])])
            
            if options.get('bit_depth'):
                # FFmpeg PCM 코덱 매핑 (wav 기준)
                if ext == 'wav':
                    if options['bit_depth'] == 24: cmds.extend(['-c:a', 'pcm_s24le'])
                    elif options['bit_depth'] == 16: cmds.extend(['-c:a', 'pcm_s16le'])
                    elif options['bit_depth'] == 32: cmds.extend(['-c:a', 'pcm_s32le'])
        else:
            # [손실] 비트레이트 적용
            if options.get('audio_bitrate'):
                cmds.extend(['-b:a', f"{options['audio_bitrate']}k"])
            
            if options.get('sample_rate'):
                cmds.extend(['-ar', str(options['sample_rate'])])

        return cmds

# --- 테스트 코드 ---
if __name__ == "__main__":
    print("이 모듈은 단독 실행 시 FFmpeg 설치 여부만 확인합니다.")
    try:
        handler = FFmpegHandler()
        print(f"FFmpeg 확인 완료: {handler.ffmpeg_path}")
    except Exception as e:
        print(e)