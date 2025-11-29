import re

def parse_quality_string(input_str: str) -> dict:
    """
    사용자가 입력한 품질 옵션 문자열을 파싱하여 구조화된 딕셔너리로 반환합니다.
    
    Args:
        input_str (str): 사용자가 입력한 키워드 문자열 
                         (예: "1080p 60fps BR_192k surround5.1 enhance")
    
    Returns:
        dict: 정규화된 옵션 값들이 담긴 딕셔너리
    """
    
    # 1. 기본 옵션 딕셔너리 초기화 (모든 값은 None 또는 False로 시작)
    options = {
        # 비디오 관련
        'height': None,         # 해상도 (int)
        'fps': None,            # 프레임 (int)
        'video_codec': None,    # 코덱 (str)
        'hdr': False,           # HDR 여부 (bool)
        'chroma_subsampling': None, # 444 등 (str)
        
        # 오디오 관련
        'audio_bitrate': None,  # 비트레이트 kbps (int)
        'sample_rate': None,    # 샘플링 속도 Hz (int)
        'bit_depth': None,      # 비트 깊이 (int)
        'audio_channels': None, # 채널 구성 (str: '1', '2', '5.1', '7.1')
        'audio_codec': None,    # 오디오 코덱 (str)
        
        # 파일/후처리 관련
        'ext': None,            # 확장자 (str)
        'use_enhance': False,   # 음질 향상 DSP 사용 여부 (bool)
        'subtitles': False,     # 자막 포함 여부 (bool)
        'thumbnail': False,     # 썸네일 포함 여부 (bool)
        'metadata': False,      # 메타데이터 포함 여부 (bool)

        # 특수 기능 관련
        'use_original': False,      # original 키워드
        'use_best_quality': False,  # bestQuality 키워드
        'use_upscale': False,   # 강제 확대 옵션
    }
    
    if not input_str:
        return options

    # 2. 입력을 소문자로 변환하고 공백으로 분리
    tokens = input_str.lower().split()
    
    # 3. 각 토큰 순회하며 파싱
    for token in tokens:
        
        # --- [Video] 해상도 (예: 1080p) ---
        if match := re.match(r'^(\d+)p$', token):
            options['height'] = int(match.group(1))
            continue
            
        # --- [Video] 프레임 (예: 60fps) ---
        if match := re.match(r'^(\d+)fps$', token):
            options['fps'] = int(match.group(1))
            continue
            
        # --- [Video] 심화 옵션 ---
        if token == 'hdr':
            options['hdr'] = True
            continue
        if token == '444':
            options['chroma_subsampling'] = '4:4:4'
            continue
            
        # --- [Audio] 비트레이트 (예: BR_192k) ---
        if match := re.match(r'^br_(\d+)k$', token):
            options['audio_bitrate'] = int(match.group(1))
            continue

        # --- [Audio] 샘플링 속도 (예: SR_48k, SR_44.1k) ---
        if match := re.match(r'^sr_([\d.]+)k$', token):
            val = float(match.group(1))
            options['sample_rate'] = int(val * 1000) # 48k -> 48000
            continue
            
        # --- [Audio] 비트 깊이 (예: 24bit) ---
        if match := re.match(r'^(\d+)bit$', token):
            options['bit_depth'] = int(match.group(1))
            continue

        # --- [Audio] 채널 (mono, stereo, surround5.1, surround7.1) ---
        if token == 'mono':
            options['audio_channels'] = '1'
        elif token == 'stereo':
            options['audio_channels'] = '2'
        elif token == 'surround5.1':
            options['audio_channels'] = '5.1'
        elif token == 'surround7.1':
            options['audio_channels'] = '7.1'
        
        # --- 특수 플래그 ---
        if token == 'original':
            options['use_original'] = True
        elif token == 'bestquality':
            options['use_best_quality'] = True
        if token == 'upscale':
            options['use_upscale'] = True

        # --- 확장자 및 코덱 (알려진 리스트와 매칭) ---
        elif token in ['mp4', 'mkv', 'webm', 'mp3', 'flac', 'wav', 'aac', 'm4a']:
            options['ext'] = token
        elif token in ['av1', 'vp9', 'h264', 'hevc']:
            options['video_codec'] = token
        elif token in ['opus', 'vorbis']:
            options['audio_codec'] = token
            
        # --- 기타 플래그 ---
        elif token == 'enhance':
            options['use_enhance'] = True
        elif token == 'sub':
            options['subtitles'] = True
        elif token == 'thumb':
            options['thumbnail'] = True
        elif token == 'meta':
            options['metadata'] = True
    return options