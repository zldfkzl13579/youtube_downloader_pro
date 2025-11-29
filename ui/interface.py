# ui/interface.py
import questionary
from ui.display import DisplayManager
from ui.logger import Logger

class UserInterface:
    def __init__(self):
        self.display = DisplayManager()

    def ask_download_mode(self):
        """다운로드 모드를 선택합니다."""
        answer = questionary.select(
            "어떤 작업을 수행하시겠습니까?",
            choices=[
                "1. Video (영상 + 소리)",
                "2. Audio (소리 추출)",
                "3. Custom (직접 입력)",
                "4. 종료 (Exit)"
            ],
            use_indicator=True,
        ).ask()
        
        if not answer: return None
        return answer[0] # "1" 또는 "2" 반환

    def ask_quality_options(self, video_info: dict, mode: str):
        """
        메타데이터를 보여주고 품질 옵션을 입력받습니다.
        Returns:
            str: 사용자 입력 문자열 (예: '1080p 60fps')
        """
        # 1. 정보 표 출력
        self.display.show_formats_table(video_info)
        
        # 2. 모드별 질문
        if mode == '1': # Video
            choice = questionary.select(
                "품질을 선택하세요:",
                choices=[
                    "1. [추천] 최고 품질 (Best Quality)",
                    "2. 1080p (FHD)",
                    "3. 720p (HD)",
                    "4. 직접 입력 (Custom)"
                ]
            ).ask()
            
            if choice.startswith('1'): return "best" # 매크로
            if choice.startswith('2'): return "1080p"
            if choice.startswith('3'): return "720p"
            # 4번이면 아래로 통과해서 직접 입력 받음

        elif mode == '2': # Audio
            choice = questionary.select(
                "음질을 선택하세요:",
                choices=[
                    "1. [추천] 최고 음질 (mp3 192k~320k)",
                    "2. m4a (aac) 원본",
                    "3. 직접 입력 (Custom)"
                ]
            ).ask()
            if choice.startswith('1'): return "mp3 BR_192k"
            if choice.startswith('2'): return "m4a"

        # 3. 직접 입력 (Custom)
        Logger.ask("원하는 옵션을 입력하세요. (도움말: '?help')")
        print("   [Tip] 예시: 1080p 60fps av1 enhance sub")
        
        while True:
            custom_input = questionary.text(">> ").ask()
            
            # 입력값 검증 및 도움말 처리
            if custom_input is None: # 취소 시
                return None
                
            stripped = custom_input.strip()
            
            if stripped == "?help" or stripped == "?":
                # 도움말 표 출력 후 다시 입력 대기
                self.display.show_help_table()
                continue
            
            if not stripped:
                Logger.warning("옵션을 입력하거나, Enter를 눌러 기본값(Best)으로 진행하세요.")
                # 빈 값 엔터 -> 그냥 리턴하여 Best로 처리하게 할 수도 있고, 다시 물을 수도 있음
                # 여기서는 '빈 값 = Best'로 처리
                return "best"

            return stripped