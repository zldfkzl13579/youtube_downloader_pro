# ui/display.py
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, 
    DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
)
from rich.panel import Panel

console = Console()

class DisplayManager:
    def show_formats_table(self, video_info: dict):
        """메타데이터 정보를 받아 분석된 표를 출력합니다."""
        
        # 1. 영상 기본 정보 출력
        title = video_info.get('title', 'Unknown Title')
        duration = video_info.get('duration', 0)
        console.print(Panel(f"[bold white]{title}[/bold white]\n[dim]길이: {duration}초[/dim]", title="Target Video", border_style="blue"))

        # 2. 비디오 옵션 테이블 생성
        v_table = Table(title="[Video Options]", show_header=True, header_style="bold magenta")
        v_table.add_column("ID", style="cyan", justify="center")
        v_table.add_column("Res", style="green")
        v_table.add_column("FPS", justify="right")
        v_table.add_column("Codec", style="dim")
        v_table.add_column("Ext", style="yellow")
        v_table.add_column("Size", justify="right")

        # 상위 5개 또는 10개만 출력 (너무 길어지는 것 방지)
        for fmt in video_info['formats']['video'][:8]:
            size_mb = f"{fmt['filesize'] / 1024 / 1024:.1f}MB" if fmt['filesize'] else "?"
            v_table.add_row(
                str(fmt['id']), 
                fmt['res'], 
                f"{fmt['fps']}fps", 
                fmt['codec'], 
                fmt['ext'], 
                size_mb
            )

        # 3. 오디오 옵션 테이블 생성
        a_table = Table(title="[Audio Options]", show_header=True, header_style="bold cyan")
        a_table.add_column("ID", style="cyan", justify="center")
        a_table.add_column("Bitrate", style="green")
        a_table.add_column("Codec", style="dim")
        a_table.add_column("Ext", style="yellow")
        a_table.add_column("Size", justify="right")

        for fmt in video_info['formats']['audio'][:5]:
            size_mb = f"{fmt['filesize'] / 1024 / 1024:.1f}MB" if fmt['filesize'] else "?"
            a_table.add_row(
                str(fmt['id']), 
                f"{int(fmt['abr'])}k" if fmt['abr'] else "?", 
                fmt['codec'], 
                fmt['ext'], 
                size_mb
            )

        # 표 출력 (옆으로 나란히 보여줄 수도 있지만, 콘솔 폭 문제로 위아래 배치 추천)
        console.print(v_table)
        console.print(a_table)
        console.print("\n")

        """사용자 정의 입력 시 사용할 수 있는 모든 키워드를 안내합니다."""
        
        table = Table(title="[Custom Input Keywords Reference]", border_style="green")
        
        table.add_column("구분", style="bold cyan", justify="center")
        table.add_column("키워드 규칙 / 예시", style="yellow")
        table.add_column("설명", style="white")

        # 비디오 기초
        table.add_row("해상도", "1080p, 2160p, 720p", "숫자 뒤에 'p' (높이 기준)")
        table.add_row("프레임", "60fps, 30fps", "숫자 뒤에 'fps'")
        table.add_row("코덱", "av1, vp9, h264", "비디오 코덱 지정")
        table.add_section()

        # 비디오 심화
        table.add_row("화질옵션", "hdr", "HDR 영상 다운로드")
        table.add_row("색상압축", "444", "크로마 서브샘플링 4:4:4 적용")
        table.add_section()

        # 오디오
        table.add_row("비트레이트", "BR_320k, BR_192k", "BR_ + 숫자 + k (손실압축용)")
        table.add_row("샘플링", "SR_48k, SR_44.1k", "SR_ + 숫자 + k (Hz 단위)")
        table.add_row("비트깊이", "24bit, 16bit", "숫자 + bit")
        table.add_row("채널", "mono, stereo, surround5.1", "오디오 채널 구성")
        table.add_section()

        # 특수 기능 섹션
        table.add_row("원본유지", "original", "확장자 변환 없이 원본 그대로 다운로드")
        table.add_row("자동최고", "bestQuality", "최고 품질 자동 선택 (--no-input 대체)")
        table.add_section()

        # 기타
        table.add_row("확장자", "mp4, mp3, mkv, wav, flac", "최종 저장 포맷 (original보다 우선됨)")
        table.add_row("부가기능", "sub", "자막 포함 (Embed)")
        table.add_row("", "thumb", "썸네일 포함")
        table.add_row("", "enhance", "DSP 음질 향상 (Crystalizer)")
        table.add_row("강제확대", "upscale", "저화질 영상을 설정한 해상도로 강제 확대 (Lanczos)")

        console.print(table)
        console.print("[dim]※ 여러 옵션을 띄어쓰기로 조합하여 입력하세요.[/dim]\n")

    def get_progress_bar(self):
        """멀티 다운로드에 최적화된 진행바 객체를 반환합니다."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}", justify="left"), # 파일명 왼쪽 정렬
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
            transient=False # 완료된 바가 사라지지 않게 설정 (취향에 따라 True 가능)
        )