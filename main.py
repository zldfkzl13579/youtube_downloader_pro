import sys
import os
import argparse
import questionary
from concurrent.futures import ThreadPoolExecutor, as_completed

# 로컬 모듈 import
from core.metadata import MetadataAnalyzer
from core.parser import parse_quality_string
from core.downloader import Downloader
from core.config import ConfigManager
from ui.interface import UserInterface
from ui.logger import Logger
from ui.display import DisplayManager

def parse_inputs(inputs: list) -> list:
    """
    입력값을 분석하여 '작업 그룹' 리스트를 반환합니다.
    형식: [{'source': 'file'|'arg', 'group_name': str, 'urls': [url, ...]}]
    """
    tasks = []
    
    for item in inputs:
        # 1. 텍스트 파일인 경우 -> 그룹명은 파일명
        if os.path.isfile(item):
            try:
                group_name = os.path.splitext(os.path.basename(item))[0]
                Logger.info(f"파일 감지: {item} -> 그룹 폴더 '{group_name}'로 설정됩니다.")
                
                with open(item, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f.readlines() if line.strip()]
                    
                tasks.append({
                    'source': 'file',
                    'group_name': group_name,
                    'urls': urls
                })
            except Exception as e:
                Logger.error(f"파일 읽기 실패 ({item}): {e}")
        else:
            # 2. 단일 URL인 경우 -> 그룹명 없음 (나중에 재생목록 확인 후 결정)
            tasks.append({
                'source': 'arg',
                'group_name': None,
                'urls': [item]
            })
    
    return tasks

def main():
    # --- 0. 설정 로드 ---
    config = ConfigManager()
    default_dir = config.get('default_output_dir')
    # 동시 다운로드 개수 (설정에 없으면 기본값 3)
    max_workers = config.get('max_workers') or 3

    # --- 1. CLI 인자 설정 ---
    parser = argparse.ArgumentParser(description="YouTube Downloader CLI")
    
    parser.add_argument('--url', nargs='+', required=True, 
                        help='다운로드할 URL 또는 URL이 담긴 텍스트 파일 경로')
    parser.add_argument('--output', default=default_dir, 
                        help=f'저장할 경로 (현재 설정값: {default_dir})')
    
    args = parser.parse_args()

    # 사용자가 경로를 바꿨다면 설정 업데이트
    if args.output != default_dir:
        config.set('default_output_dir', args.output)

    # --- 2. 초기화 ---
    analyzer = MetadataAnalyzer()
    ui = UserInterface()
    display = DisplayManager()
    downloader = Downloader()
    
    # 작업 그룹핑 (파일 vs URL)
    tasks_groups = parse_inputs(args.url)
    if not tasks_groups:
        Logger.error("처리할 유효한 대상이 없습니다.")
        return

    Logger.info(f"총 {len(tasks_groups)}개의 입력 그룹을 확인했습니다.")

    # --- 3. 메타데이터 분석 및 옵션 선택 ---
    # 첫 번째 유효한 URL을 찾아 옵션 질문용으로 사용
    first_url = None
    for tg in tasks_groups:
        if tg['urls']:
            first_url = tg['urls'][0]
            break
            
    if not first_url: return

    Logger.info("메타데이터 분석 중... (옵션 설정을 위해 첫 번째 영상 조회)")
    meta_info = analyzer.get_video_info(first_url)
    
    if not meta_info:
        Logger.error("메타데이터 분석 실패. 네트워크 상태를 확인하세요.")
        return

    # 대화형 모드 진입
    mode = ui.ask_download_mode()
    if not mode or "종료" in mode: return
        
    # mode[0]은 "1" 또는 "2" (Video/Audio)
    input_str = ui.ask_quality_options(meta_info, mode[0])
    if not input_str: return

    # 옵션 파싱
    quality_options = parse_quality_string(input_str)
    Logger.info(f"적용된 옵션: {quality_options}")

    # --- 4. 병렬 다운로드 준비 (Queueing) ---
    download_queue = [] 

    Logger.info("다운로드 대기열을 생성하고 폴더를 준비합니다...")

    for group in tasks_groups:
        target_urls = group['urls']
        
        # [Logic] 텍스트 파일 소스
        if group['source'] == 'file' and group['group_name']:
            # ... (기존과 동일)
            current_dir = os.path.join(args.output, group['group_name'])
            group_options = quality_options.copy()
            
            if not os.path.exists(current_dir): os.makedirs(current_dir)
            
            for url in target_urls:
                download_queue.append({'url': url, 'output_dir': current_dir, 'options': group_options})
        
        # [Logic] URL 소스 (여기가 핵심 변경!)
        elif group['source'] == 'arg':
            if len(target_urls) == 1:
                url = target_urls[0]
                info = analyzer.get_video_info(url)
                
                # 재생목록 감지
                if info and info.get('_type') == 'playlist':
                    Logger.ask(f"재생목록 감지: '{info.get('title')}'")
                    is_playlist = questionary.confirm("전체 재생목록을 다운로드하시겠습니까?").ask()
                    
                    if is_playlist:
                        # 1. 재생목록 폴더 생성
                        safe_title = "".join([c for c in info.get('title', 'Playlist') if c.isalnum() or c in (' ','_','-')]).strip()
                        playlist_dir = os.path.join(args.output, safe_title)
                        if not os.path.exists(playlist_dir): os.makedirs(playlist_dir)
                        
                        Logger.info("재생목록 내 영상 목록을 가져오는 중...")
                        
                        # 2. [핵심] 재생목록 펼치기 (Flattening)
                        # metadata.py에 새로 만든 함수 사용
                        playlist_items = analyzer.get_playlist_items(url)
                        
                        Logger.info(f"총 {len(playlist_items)}개의 영상을 대기열에 추가합니다.")
                        
                        # 3. 개별 작업으로 등록
                        playlist_opts = quality_options.copy()
                        # 개별 영상으로 쪼갰으니 noplaylist는 필요 없음 (오히려 충돌 가능성 있으니 제거)
                        
                        for item in playlist_items:
                            download_queue.append({
                                'url': item['url'],
                                'output_dir': playlist_dir,
                                'options': playlist_opts
                            })
                            
                    else:
                        # "No" 선택 시: 단일 영상 취급 (기존 로직)
                        single_opts = quality_options.copy()
                        single_opts['noplaylist'] = True
                        if not os.path.exists(args.output): os.makedirs(args.output)
                        
                        download_queue.append({
                            'url': url, 
                            'output_dir': args.output, 
                            'options': single_opts
                        })
                else:
                    # 일반 단일 영상
                    if not os.path.exists(args.output): os.makedirs(args.output)
                    download_queue.append({
                        'url': url,
                        'output_dir': args.output,
                        'options': quality_options
                    })

    # --- 5. 병렬 실행 (Executor) ---
    Logger.info(f"총 {len(download_queue)}개의 작업을 {max_workers}개의 스레드로 병렬 처리합니다.")
    
    total_success = 0
    total_fail = 0
    results_log = []

    # Rich Progress Bar 컨텍스트
    with display.get_progress_bar() as progress:
        # 전체 진행률 바 (Total)
        overall_task = progress.add_task("[magenta]Total Progress", total=len(download_queue), filename="Batch")

        # 스레드 풀 실행
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for job in download_queue:
                # 개별 진행바 생성
                task_id = progress.add_task("Pending...", total=100, filename="Waiting")
                
                # 동적 콜백 함수 생성 (클로저)
                def make_callback(tid):
                    def cb(d):
                        if d['status'] == 'downloading':
                            progress.update(
                                tid, 
                                description="[cyan]Downloading", 
                                filename=d.get('filename', 'Unknown'), 
                                completed=d.get('percent', 0)
                            )
                        elif d['status'] == 'finished':
                            progress.update(tid, description="[green]Converting", completed=100)
                    return cb

                # 작업 제출 (url은 리스트로 감싸서 전달)
                future = executor.submit(
                    downloader.download, 
                    [job['url']], 
                    job['output_dir'], 
                    job['options'], 
                    make_callback(task_id)
                )
                futures[future] = task_id

            # 결과 수집
            for future in as_completed(futures):
                tid = futures[future]
                try:
                    res_list = future.result()
                    
                    for res in res_list:
                        results_log.append(res)
                        if res['status'] == 'success':
                            total_success += 1
                            progress.update(tid, description="[bold green]Done", filename=os.path.basename(res['filepath']))
                        else:
                            total_fail += 1
                            progress.update(tid, description="[bold red]Failed", filename="Error")
                except Exception as e:
                    Logger.error(f"Task Error: {e}")
                    total_fail += 1
                    progress.update(tid, description="[bold red]Error", filename="System Error")
                
                # 전체 진행률 1칸 전진
                progress.advance(overall_task)

    # --- 6. 최종 결과 리포트 ---
    print("\n")
    if total_fail == 0:
        Logger.success(f"모든 작업이 완료되었습니다! ({total_success}/{len(download_queue)})")
    else:
        Logger.warning(f"작업 완료. 성공: {total_success}, 실패: {total_fail}")
        
    for res in results_log:
        status_icon = "[OK]" if res['status'] == 'success' else "[FAIL]"
        msg = os.path.basename(res['filepath']) if res['status']=='success' else res.get('msg')
        print(f" - {status_icon} {msg}")

    if os.name == 'nt':
        os.system("pause")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[System] 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        Logger.error(f"오류 발생: {e}")