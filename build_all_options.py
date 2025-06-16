#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCalEditor 통합 빌드 스크립트
PyInstaller vs Nuitka 선택 가능
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Windows encoding fix
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def show_menu():
    """빌드 옵션 메뉴 표시"""
    print("=" * 50)
    print("AutoCalEditor 빌드 옵션 선택")
    print("=" * 50)
    print()
    print("1. 🚀 Nuitka 컴파일 (권장 - 최고 성능)")
    print("   - 실제 컴파일을 통한 네이티브 실행 파일")
    print("   - PyInstaller보다 2-5배 빠른 실행 속도")
    print("   - 더 작은 파일 크기")
    print("   - 소요 시간: 10-30분")
    print()
    print("2. 📦 PyInstaller 빌드 (빠른 빌드)")
    print("   - Python 인터프리터 번들링")
    print("   - 빠른 빌드 시간 (2-5분)")
    print("   - 안정적이고 검증된 방식")
    print("   - 더 큰 파일 크기")
    print()
    print("3. 🔧 Cython + PyInstaller (중간 성능)")
    print("   - Cython 최적화 + PyInstaller 패키징")
    print("   - 중간 수준의 성능 향상")
    print("   - 소요 시간: 5-10분")
    print()
    print("0. 종료")
    print()

def get_user_choice():
    """사용자 선택 입력"""
    while True:
        try:
            choice = input("선택하세요 (0-3): ").strip()
            if choice in ['0', '1', '2', '3']:
                return int(choice)
            else:
                print("❌ 잘못된 선택입니다. 0-3 중에서 선택해주세요.")
        except KeyboardInterrupt:
            print("\n\n종료합니다.")
            sys.exit(0)
        except Exception:
            print("❌ 잘못된 입력입니다. 숫자를 입력해주세요.")

def run_nuitka_build():
    """Nuitka 빌드 실행"""
    logging.info("🚀 Nuitka 컴파일 시작...")
    
    if not os.path.exists('build_nuitka.py'):
        logging.error("❌ build_nuitka.py 파일을 찾을 수 없습니다.")
        return False
    
    try:
        result = subprocess.run([sys.executable, 'build_nuitka.py'], 
                              timeout=1800)  # 30분 타임아웃
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logging.error("❌ Nuitka 빌드 타임아웃")
        return False
    except Exception as e:
        logging.error(f"❌ Nuitka 빌드 오류: {e}")
        return False

def run_pyinstaller_build():
    """PyInstaller 빌드 실행"""
    logging.info("📦 PyInstaller 빌드 시작...")
    
    if os.path.exists('build_simple.py'):
        script = 'build_simple.py'
    elif os.path.exists('build_all.py'):
        script = 'build_all.py'
    else:
        logging.error("❌ PyInstaller 빌드 스크립트를 찾을 수 없습니다.")
        return False
    
    try:
        result = subprocess.run([sys.executable, script], timeout=600)  # 10분 타임아웃
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logging.error("❌ PyInstaller 빌드 타임아웃")
        return False
    except Exception as e:
        logging.error(f"❌ PyInstaller 빌드 오류: {e}")
        return False

def run_cython_pyinstaller_build():
    """Cython + PyInstaller 빌드 실행"""
    logging.info("🔧 Cython + PyInstaller 빌드 시작...")
    
    # 1. Cython 빌드
    if os.path.exists('build_scripts/build_cython.py'):
        logging.info("1단계: Cython 모듈 컴파일...")
        try:
            result = subprocess.run([sys.executable, 'build_scripts/build_cython.py'], 
                                  timeout=300)
            if result.returncode != 0:
                logging.error("❌ Cython 빌드 실패")
                return False
        except Exception as e:
            logging.error(f"❌ Cython 빌드 오류: {e}")
            return False
    
    # 2. PyInstaller 빌드
    logging.info("2단계: PyInstaller 패키징...")
    return run_pyinstaller_build()

def check_project_root():
    """프로젝트 루트 확인"""
    if not os.path.exists('main.py'):
        logging.error("❌ main.py를 찾을 수 없습니다. 프로젝트 루트에서 실행해주세요.")
        return False
    return True

def show_performance_comparison():
    """성능 비교 정보 표시"""
    print()
    print("=" * 60)
    print("📊 빌드 방식별 성능 비교")
    print("=" * 60)
    print()
    print("┌─────────────────┬──────────┬──────────┬──────────┐")
    print("│ 빌드 방식       │ 실행속도 │ 파일크기 │ 빌드시간 │")
    print("├─────────────────┼──────────┼──────────┼──────────┤")
    print("│ Nuitka          │   ⭐⭐⭐⭐⭐ │   ⭐⭐⭐⭐   │   ⭐⭐     │")
    print("│ Cython+PyInst   │   ⭐⭐⭐⭐   │   ⭐⭐⭐     │   ⭐⭐⭐   │")
    print("│ PyInstaller     │   ⭐⭐⭐     │   ⭐⭐      │   ⭐⭐⭐⭐⭐ │")
    print("└─────────────────┴──────────┴──────────┴──────────┘")
    print()
    print("💡 성능이 중요하다면 Nuitka를 선택하세요!")
    print("💡 빠른 테스트가 필요하다면 PyInstaller를 선택하세요!")
    print()

def main():
    """메인 함수"""
    print("AutoCalEditor 통합 빌드 시스템")
    
    # 프로젝트 루트 확인
    if not check_project_root():
        return False
    
    # 성능 비교 정보 표시
    show_performance_comparison()
    
    while True:
        # 메뉴 표시
        show_menu()
        
        # 사용자 선택
        choice = get_user_choice()
        
        if choice == 0:
            print("종료합니다.")
            break
        elif choice == 1:
            print("\n🚀 Nuitka 컴파일을 시작합니다...")
            print("⏱️ 예상 소요 시간: 10-30분")
            print("📝 진행 상황은 nuitka_build.log에서 확인할 수 있습니다.")
            
            if run_nuitka_build():
                print("\n✅ Nuitka 컴파일 완료!")
                print("⚡ 최고 성능의 실행 파일이 생성되었습니다!")
            else:
                print("\n❌ Nuitka 컴파일 실패!")
            break
            
        elif choice == 2:
            print("\n📦 PyInstaller 빌드를 시작합니다...")
            print("⏱️ 예상 소요 시간: 2-5분")
            
            if run_pyinstaller_build():
                print("\n✅ PyInstaller 빌드 완료!")
                print("📁 dist/AutoCalEditor.exe 파일이 생성되었습니다!")
            else:
                print("\n❌ PyInstaller 빌드 실패!")
            break
            
        elif choice == 3:
            print("\n🔧 Cython + PyInstaller 빌드를 시작합니다...")
            print("⏱️ 예상 소요 시간: 5-10분")
            
            if run_cython_pyinstaller_build():
                print("\n✅ Cython + PyInstaller 빌드 완료!")
                print("⚡ 최적화된 실행 파일이 생성되었습니다!")
            else:
                print("\n❌ Cython + PyInstaller 빌드 실패!")
            break
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(0)
