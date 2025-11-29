import csv
import os
from datetime import datetime

HISTORY_FILE = 'download_history.csv'

def log_success(title, url, filepath):
    """다운로드 성공 기록을 CSV에 남깁니다."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    file_exists = os.path.exists(HISTORY_FILE)
    
    try:
        # [수정됨] encoding='utf-8' -> 'utf-8-sig' (엑셀 호환성 해결)
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 파일이 처음 생성될 때만 헤더 작성
            if not file_exists:
                writer.writerow(['Date', 'Title', 'URL', 'Filepath'])
            
            writer.writerow([now, title, url, filepath])
    except Exception as e:
        # 기록 실패가 프로그램 전체 에러로 이어지지 않게 예외 처리
        print(f"[Warning] 기록 저장 실패: {e}")