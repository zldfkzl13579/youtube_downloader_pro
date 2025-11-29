import json
import os
from ui.logger import Logger

CONFIG_FILE = 'settings.json'

def get_optimal_workers():
    """시스템의 CPU 코어 수를 확인하여 적절한 작업자 수를 반환합니다."""
    try:
        # os.cpu_count()는 논리 코어(스레드) 수를 반환합니다. (예: 4코어 8스레드 -> 8)
        cpu_count = os.cpu_count() or 2
        
        # [공식]
        # 1. 기본적으로 CPU 코어 수만큼 설정
        # 2. 하지만 4개를 넘어가면 네트워크/디스크 병목이 올 수 있으므로 보수적으로 설정
        # 3. 최대 8개로 제한 (너무 많으면 유튜브 차단 위험 및 시스템 렉 유발)
        
        if cpu_count <= 4:
            return cpu_count  # 저사양: 코어 수 그대로 (2~4)
        else:
            return min(cpu_count, 6) # 고사양: 최대 6개까지만 (안전빵)
            
    except:
        return 3 # 조회 실패 시 기본값

# 초기 설정값 생성 시 함수 호출
DEFAULT_CONFIG = {
    # 윈도우 기본 다운로드 폴더 자동 감지
    'default_output_dir': os.path.join(os.path.expanduser('~'), 'Downloads'),
    'max_retries': 3,
    'max_workers': get_optimal_workers()  # [New] 자동 계산된 값 적용
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
            except Exception as e:
                Logger.warning(f"설정 로드 중 오류: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            Logger.error(f"설정 저장 실패: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()