# scripts/resource_path.py
# PyInstaller 패키징 및 일반 실행 모두에서 올바른 경로를 반환

import sys
import os

def resource_path(relative_path):
    """
    개발 환경과 PyInstaller .exe 패키징 환경 모두에서
    올바른 절대 경로를 반환한다.

    개발 환경 : 실행 파일(main.py) 기준 상대 경로
    패키징 후 : sys._MEIPASS (임시 압축 해제 폴더) 기준 경로
    """
    try:
        base = sys._MEIPASS          # PyInstaller 패키징 시
    except AttributeError:
        base = os.path.abspath(".")  # 일반 실행 시
    return os.path.join(base, relative_path)
