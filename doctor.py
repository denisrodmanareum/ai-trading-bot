#!/usr/bin/env python3
"""
AI Trading Bot - 자동 진단 및 수정 도구
모든 일반적인 오류를 자동으로 감지하고 수정합니다.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class Colors:
    """터미널 색상"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def get_project_root():
    """프로젝트 루트 디렉토리 찾기 (폴더명 무관)"""
    current = Path(__file__).parent.absolute()
    return current


def check_python_version():
    """Python 버전 확인"""
    print_header("Python 버전 확인")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    print(f"현재 Python 버전: {version_str}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python 버전이 너무 낮습니다! (최소 3.9 필요)")
        print_info("https://www.python.org/downloads/ 에서 최신 버전을 다운로드하세요")
        return False
    elif version.minor < 11:
        print_warning(f"Python 3.11 이상을 권장합니다")
        return True
    else:
        print_success(f"Python 버전 OK ({version_str})")
        return True


def check_venv():
    """가상환경 확인 및 생성"""
    print_header("가상환경 확인")
    
    root = get_project_root()
    backend_dir = root / "backend"
    venv_dir = backend_dir / "venv"
    
    if not backend_dir.exists():
        print_error("backend 폴더를 찾을 수 없습니다!")
        return False
    
    if venv_dir.exists():
        print_success("가상환경이 존재합니다")
        return True
    else:
        print_warning("가상환경이 없습니다. 생성 중...")
        
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
            print_success("가상환경 생성 완료")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"가상환경 생성 실패: {e}")
            return False


def check_pip_packages():
    """필수 패키지 확인"""
    print_header("Python 패키지 확인")
    
    root = get_project_root()
    backend_dir = root / "backend"
    requirements_file = backend_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print_error("requirements.txt 파일이 없습니다!")
        return False
    
    # 가상환경의 pip 경로 찾기
    if platform.system() == "Windows":
        pip_path = backend_dir / "venv" / "Scripts" / "pip.exe"
        python_path = backend_dir / "venv" / "Scripts" / "python.exe"
    else:
        pip_path = backend_dir / "venv" / "bin" / "pip"
        python_path = backend_dir / "venv" / "bin" / "python"
    
    if not pip_path.exists():
        print_error("가상환경의 pip를 찾을 수 없습니다!")
        return False
    
    # pip 업그레이드
    print_info("pip 업그레이드 중...")
    try:
        subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip", "--quiet"], 
                       check=True)
        print_success("pip 업그레이드 완료")
    except subprocess.CalledProcessError:
        print_warning("pip 업그레이드 실패 (계속 진행)")
    
    # 패키지 설치 확인
    print_info("필수 패키지 확인 중...")
    
    try:
        result = subprocess.run([str(pip_path), "list"], 
                                capture_output=True, text=True, check=True)
        installed_packages = result.stdout.lower()
        
        required_packages = [
            'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 
            'numpy', 'pandas', 'stable-baselines3', 'torch'
        ]
        
        missing_packages = []
        for pkg in required_packages:
            if pkg not in installed_packages:
                missing_packages.append(pkg)
        
        if missing_packages:
            print_warning(f"누락된 패키지: {', '.join(missing_packages)}")
            print_info("requirements.txt에서 패키지 설치 중...")
            
            subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], 
                           check=True)
            print_success("패키지 설치 완료")
        else:
            print_success("모든 필수 패키지 설치됨")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"패키지 확인 실패: {e}")
        return False


def check_env_file():
    """환경 변수 파일 확인"""
    print_header("환경 변수 파일 확인")
    
    root = get_project_root()
    backend_dir = root / "backend"
    env_file = backend_dir / ".env"
    env_example = root / ".env.example"
    
    if env_file.exists():
        print_success(".env 파일이 존재합니다")
        
        # API 키 설정 여부 확인
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'your_api_key_here' in content or 'your_api_secret_here' in content:
            print_warning("⚠️  API 키가 설정되지 않았습니다!")
            print_info("backend\\.env 파일을 열어서 실제 API 키를 입력하세요")
        else:
            print_success("API 키 설정됨")
        
        return True
    else:
        print_warning(".env 파일이 없습니다. 생성 중...")
        
        # .env.example에서 복사
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print_success(".env 파일 생성 완료")
            print_warning("⚠️  backend\\.env 파일을 열어서 API 키를 입력하세요!")
            return True
        else:
            # 기본 .env 파일 생성
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write("""# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=True

# Exchange Selection
ACTIVE_EXCHANGE=BINANCE

# Database
DATABASE_URL=sqlite:///./trading_bot.db

# AI Settings
DEFAULT_LEVERAGE=5
MAX_LEVERAGE=125

# Trading Mode
TRADING_MODE=SCALP

# Risk Management
DAILY_LOSS_LIMIT=25
MAX_MARGIN_LEVEL=0.8
""")
            print_success(".env 파일 생성 완료")
            print_warning("⚠️  backend\\.env 파일을 열어서 API 키를 입력하세요!")
            return True


def check_database():
    """데이터베이스 확인"""
    print_header("데이터베이스 확인")
    
    root = get_project_root()
    backend_dir = root / "backend"
    db_file = backend_dir / "trading_bot.db"
    
    if db_file.exists():
        print_success("데이터베이스 파일 존재")
        print_info(f"크기: {db_file.stat().st_size / 1024:.2f} KB")
        return True
    else:
        print_warning("데이터베이스 파일이 없습니다")
        print_info("봇 실행 시 자동으로 생성됩니다")
        return True


def check_node_modules():
    """Node.js 모듈 확인"""
    print_header("프론트엔드 패키지 확인")
    
    root = get_project_root()
    frontend_dir = root / "frontend"
    node_modules = frontend_dir / "node_modules"
    
    if not frontend_dir.exists():
        print_error("frontend 폴더를 찾을 수 없습니다!")
        return False
    
    if node_modules.exists():
        print_success("node_modules 존재")
        return True
    else:
        print_warning("node_modules가 없습니다")
        print_info("EASY_INSTALL.bat을 다시 실행하거나")
        print_info("frontend 폴더에서 'npm install'을 실행하세요")
        return False


def check_directory_structure():
    """디렉토리 구조 확인 및 생성"""
    print_header("디렉토리 구조 확인")
    
    root = get_project_root()
    backend_dir = root / "backend"
    
    required_dirs = [
        backend_dir / "data" / "models",
        backend_dir / "data" / "logs",
        backend_dir / "data" / "reviews",
        backend_dir / "data" / "tensorboard",
    ]
    
    created_dirs = []
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path.name)
    
    if created_dirs:
        print_success(f"생성된 디렉토리: {', '.join(created_dirs)}")
    else:
        print_success("모든 디렉토리 존재")
    
    return True


def check_common_issues():
    """일반적인 문제 확인"""
    print_header("일반적인 문제 확인")
    
    root = get_project_root()
    
    issues_found = []
    
    # 1. 한글 경로 확인
    if any(ord(c) > 127 for c in str(root)):
        print_warning("경로에 한글이 포함되어 있습니다")
        print_info("일부 패키지에서 문제가 발생할 수 있습니다")
        print_info("영문 경로로 이동하는 것을 권장합니다")
        issues_found.append("korean_path")
    
    # 2. 공백 경로 확인
    if ' ' in str(root):
        print_warning("경로에 공백이 포함되어 있습니다")
        print_info("일부 도구에서 문제가 발생할 수 있습니다")
        issues_found.append("space_in_path")
    
    # 3. 긴 경로 확인 (Windows)
    if platform.system() == "Windows" and len(str(root)) > 200:
        print_warning("경로가 너무 깁니다 (200자 이상)")
        print_info("일부 파일 작업에서 문제가 발생할 수 있습니다")
        issues_found.append("long_path")
    
    if not issues_found:
        print_success("일반적인 문제 없음")
    
    return len(issues_found) == 0


def fix_common_errors():
    """자동 수정 가능한 오류 수정"""
    print_header("자동 오류 수정")
    
    root = get_project_root()
    backend_dir = root / "backend"
    
    fixes_applied = []
    
    # 1. __pycache__ 정리
    print_info("캐시 파일 정리 중...")
    for cache_dir in backend_dir.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
        fixes_applied.append("pycache_cleaned")
    
    # 2. .pyc 파일 삭제
    for pyc_file in backend_dir.rglob("*.pyc"):
        pyc_file.unlink(missing_ok=True)
    
    # 3. 로그 파일 정리 (선택적)
    log_dir = backend_dir / "data" / "logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if len(log_files) > 10:
            print_info(f"오래된 로그 파일 정리 중... ({len(log_files)}개)")
            # 최신 10개만 유지
            sorted_logs = sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
            for old_log in sorted_logs[10:]:
                old_log.unlink(missing_ok=True)
            fixes_applied.append("logs_cleaned")
    
    if fixes_applied:
        print_success(f"수정 완료: {', '.join(fixes_applied)}")
    else:
        print_success("수정할 사항 없음")
    
    return True


def generate_diagnostic_report():
    """진단 보고서 생성"""
    print_header("진단 보고서 생성")
    
    root = get_project_root()
    report_file = root / "DIAGNOSTIC_REPORT.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("AI Trading Bot - 진단 보고서\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"생성 시간: {__import__('datetime').datetime.now()}\n")
        f.write(f"프로젝트 경로: {root}\n")
        f.write(f"Python 버전: {sys.version}\n")
        f.write(f"운영체제: {platform.system()} {platform.release()}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("설치 상태\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"가상환경: {'✅' if (root / 'backend' / 'venv').exists() else '❌'}\n")
        f.write(f"환경변수: {'✅' if (root / 'backend' / '.env').exists() else '❌'}\n")
        f.write(f"데이터베이스: {'✅' if (root / 'backend' / 'trading_bot.db').exists() else '❌'}\n")
        f.write(f"node_modules: {'✅' if (root / 'frontend' / 'node_modules').exists() else '❌'}\n\n")
    
    print_success(f"진단 보고서 생성: {report_file}")
    print_info("문제 발생 시 이 파일을 공유하세요")
    
    return True


def main():
    """메인 함수"""
    print("\n")
    print("=" * 70)
    print("  🔧 AI Trading Bot - 자동 진단 도구")
    print("=" * 70)
    print()
    
    all_checks_passed = True
    
    # 시스템 검사
    checks = [
        ("Python 버전", check_python_version),
        ("가상환경", check_venv),
        ("Python 패키지", check_pip_packages),
        ("환경 변수", check_env_file),
        ("데이터베이스", check_database),
        ("프론트엔드 패키지", check_node_modules),
        ("디렉토리 구조", check_directory_structure),
        ("일반 문제", check_common_issues),
    ]
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            if not result:
                all_checks_passed = False
        except Exception as e:
            print_error(f"{check_name} 검사 중 오류: {e}")
            all_checks_passed = False
    
    # 자동 수정
    try:
        fix_common_errors()
    except Exception as e:
        print_error(f"자동 수정 중 오류: {e}")
    
    # 진단 보고서 생성
    try:
        generate_diagnostic_report()
    except Exception as e:
        print_error(f"보고서 생성 중 오류: {e}")
    
    # 최종 결과
    print_header("진단 완료")
    
    if all_checks_passed:
        print_success("모든 검사 통과! 🎉")
        print_info("START_BOT.bat을 실행하여 봇을 시작하세요")
    else:
        print_warning("일부 문제가 발견되었습니다")
        print_info("EASY_INSTALL.bat을 다시 실행하거나")
        print_info("위의 오류 메시지를 참고하여 수동으로 수정하세요")
    
    print()
    
    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n진단이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print_error(f"예기치 않은 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
