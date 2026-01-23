"""
고아(orphan) history 파일 정리
모델 파일(.zip)이 없는 history.json 파일들을 삭제합니다
"""
import os
import glob

def cleanup_orphan_history(directory="data/models"):
    """모델 파일이 없는 history 파일 삭제"""
    print(f"📂 디렉토리 확인: {directory}")
    
    if not os.path.exists(directory):
        print("❌ 디렉토리가 존재하지 않습니다.")
        return
    
    # 모든 history.json 파일 찾기
    history_files = glob.glob(os.path.join(directory, "*_history.json"))
    
    if not history_files:
        print("✅ history 파일이 없습니다.")
        return
    
    print(f"📄 {len(history_files)}개의 history 파일 발견")
    
    deleted_count = 0
    for history_path in history_files:
        # 대응하는 .zip 파일 경로
        model_path = history_path.replace('_history.json', '.zip')
        
        # .zip 파일이 없으면 history 파일 삭제
        if not os.path.exists(model_path):
            try:
                os.remove(history_path)
                print(f"🗑️  삭제: {os.path.basename(history_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 삭제 실패 {os.path.basename(history_path)}: {e}")
        else:
            print(f"✅ 유지: {os.path.basename(history_path)} (모델 존재)")
    
    print(f"\n✨ 정리 완료: {deleted_count}개 파일 삭제됨")

if __name__ == "__main__":
    cleanup_orphan_history()
