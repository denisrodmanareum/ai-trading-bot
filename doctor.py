"""
AI Trading Bot - Environment Doctor

목표:
- 다른 PC에서 clone 후 실행 시 자주 나는 오류를 빠르게 진단
  (Git LFS, 모델 파일, Python/venv, Node/npm, .env, node_modules 등)

사용:
  python doctor.py
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, Optional


ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
        )
        return p.returncode, (p.stdout or "").strip()
    except FileNotFoundError:
        return 127, f"NOT FOUND: {cmd[0]}"
    except Exception as e:
        return 1, f"FAILED: {e}"


def headline(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def ok(msg: str) -> None:
    print(f"[OK]  {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def bad(msg: str) -> None:
    print(f"[FAIL] {msg}")


def exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        return False


def is_lfs_pointer(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size > 2048:
            return False
        head = path.read_bytes()[:2048]
        return b"git-lfs.github.com/spec/v1" in head
    except Exception:
        return False


def check_git_lfs_and_models() -> None:
    headline("1) Git / Git LFS / 모델 파일 검사")

    code, out = run(["git", "--version"])
    if code == 0:
        ok(out)
    else:
        bad("git이 설치되어 있지 않습니다. Git 설치 후 다시 실행하세요.")
        return

    code, out = run(["git", "lfs", "version"])
    if code == 0:
        ok(out)
    else:
        bad("git-lfs가 설치되어 있지 않습니다.")
        print("  해결: https://git-lfs.com/ 설치 후 아래 실행")
        print("    git lfs install")
        print("    git lfs pull")

    model_dirs = [
        ROOT / "backend" / "data" / "models",
        ROOT / "backend" / "models",
    ]

    any_models = False
    any_pointer = False

    for d in model_dirs:
        if not d.exists():
            continue
        zips = list(d.glob("*.zip"))
        if not zips:
            continue
        any_models = True
        for z in zips[:20]:
            if is_lfs_pointer(z):
                any_pointer = True
                bad(f"LFS 포인터 파일로 내려옴: {z.relative_to(ROOT)}")
                print("  해결: git lfs install && git lfs pull")
                break

    if not any_models:
        warn("모델(.zip)을 찾지 못했습니다. (학습 모델을 LFS로 올렸는지 확인)")
    elif not any_pointer:
        ok("모델 파일(.zip) 형식 정상 (LFS 포인터 아님)")


def check_python_backend() -> None:
    headline("2) Python / Backend(vENV) 검사")

    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 11):
        ok(f"Python {major}.{minor} (현재 실행 중)")
    else:
        bad(f"Python {major}.{minor} 감지됨. Python 3.11+ 필요")

    venv_py = ROOT / "backend" / "venv" / "Scripts" / "python.exe"
    if exists(venv_py):
        ok(f"venv 감지: {venv_py.relative_to(ROOT)}")
        code, out = run([str(venv_py), "-c", "import fastapi, uvicorn, aiohttp; print('imports ok')"], cwd=ROOT / "backend")
        if code == 0:
            ok("backend 패키지 import 정상 (fastapi/uvicorn/aiohttp)")
        else:
            bad("backend 의존성이 설치되지 않았습니다.")
            print("  해결: INSTALL.bat 또는 setup.bat 실행")
            print(f"  상세: {out[:200]}")
    else:
        warn("backend venv가 없습니다.")
        print("  해결: INSTALL.bat 또는 setup.bat 실행")

    env_path = ROOT / "backend" / ".env"
    if exists(env_path):
        txt = env_path.read_text(encoding="utf-8", errors="ignore")
        has_key = "BINANCE_API_KEY=" in txt and "BINANCE_API_SECRET=" in txt
        if has_key:
            ok("backend/.env 존재 (BINANCE_API_KEY/SECRET 키 포함)")
        else:
            warn("backend/.env는 있으나 BINANCE_API_KEY/SECRET 항목이 없습니다.")
    else:
        warn("backend/.env가 없습니다. (다른 PC에서는 반드시 생성/수정 필요)")
        print("  해결: .env.example 참고하여 backend/.env 생성")


def check_frontend() -> None:
    headline("3) Node / Frontend(node_modules) 검사")

    code, out = run(["node", "-v"])
    if code == 0:
        ok(f"node {out}")
    else:
        bad("Node.js가 설치되어 있지 않습니다. (v16+ 권장)")

    code, out = run(["npm", "-v"])
    if code == 0:
        ok(f"npm {out}")
    else:
        bad("npm을 찾지 못했습니다.")

    nm = ROOT / "frontend" / "node_modules"
    if exists(nm):
        ok("frontend/node_modules 존재")
    else:
        warn("frontend/node_modules 없음")
        print("  해결: frontend 폴더에서 `npm install` 실행 또는 INSTALL.bat 실행")


def summary() -> None:
    headline("요약 / 다음 단계")
    print("- 다른 PC에서 모델이 안 로드되면: `git lfs install` + `git lfs pull`")
    print("- backend 오류가 많으면: `INSTALL.bat`(또는 `setup.bat`)로 venv/requirements 설치")
    print("- frontend 오류가 많으면: `frontend`에서 `npm install`")
    print("- API 키 오류면: `backend/.env`에 BINANCE_API_KEY/BINANCE_API_SECRET 설정")


def main() -> int:
    print(f"Project root: {ROOT}")
    check_git_lfs_and_models()
    check_python_backend()
    check_frontend()
    summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

