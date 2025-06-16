#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subprocess Helper for Windows Console Window Hiding
Windows에서 subprocess 실행 시 콘솔창이 나타나는 것을 방지
"""

import subprocess
import sys
import os
import logging

def get_subprocess_kwargs():
    """Windows에서 콘솔창을 숨기는 subprocess 설정 반환"""
    kwargs = {
        'encoding': 'utf-8',
        'errors': 'replace',
        'timeout': 30
    }
    
    # Windows에서 콘솔창 숨김 설정
    if sys.platform == "win32":
        # CREATE_NO_WINDOW 플래그로 콘솔창 생성 방지
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # 추가 환경변수 설정
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        kwargs['env'] = env
    
    return kwargs

def run_hidden_subprocess(cmd, cwd=None, capture_output=True, text=True, **additional_kwargs):
    """콘솔창을 숨기고 subprocess 실행"""
    try:
        # 기본 설정 가져오기
        kwargs = get_subprocess_kwargs()
        
        # 추가 설정 병합
        kwargs.update(additional_kwargs)
        
        # 기본 매개변수 설정
        if cwd:
            kwargs['cwd'] = cwd
        if capture_output:
            kwargs['capture_output'] = capture_output
        if text:
            kwargs['text'] = text
        
        # subprocess 실행
        result = subprocess.run(cmd, **kwargs)
        return result
        
    except subprocess.TimeoutExpired:
        logging.warning(f"Subprocess timeout: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        raise
    except Exception as e:
        logging.error(f"Subprocess error: {e}")
        raise

def run_git_command(git_executable, git_args, cwd=None, timeout=30):
    """Git 명령어를 콘솔창 없이 실행"""
    cmd = [git_executable] + git_args
    
    kwargs = get_subprocess_kwargs()
    kwargs['timeout'] = timeout
    if cwd:
        kwargs['cwd'] = cwd
    kwargs['capture_output'] = True
    kwargs['text'] = True
    
    try:
        result = subprocess.run(cmd, **kwargs)
        return result
    except subprocess.TimeoutExpired:
        logging.warning(f"Git command timeout: {' '.join(cmd)}")
        raise
    except Exception as e:
        logging.error(f"Git command error: {e}")
        raise

def run_excel_command(cmd, cwd=None, timeout=60):
    """Excel 관련 명령어를 콘솔창 없이 실행"""
    kwargs = get_subprocess_kwargs()
    kwargs['timeout'] = timeout
    if cwd:
        kwargs['cwd'] = cwd
    kwargs['capture_output'] = True
    kwargs['text'] = True
    
    try:
        result = subprocess.run(cmd, **kwargs)
        return result
    except subprocess.TimeoutExpired:
        logging.warning(f"Excel command timeout: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        raise
    except Exception as e:
        logging.error(f"Excel command error: {e}")
        raise

# Windows 전용 상수
if sys.platform == "win32":
    # subprocess 생성 플래그
    CREATE_NO_WINDOW = 0x08000000
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    
    # 권장 설정: 콘솔창 완전 숨김
    RECOMMENDED_CREATION_FLAGS = CREATE_NO_WINDOW
else:
    # 다른 플랫폼에서는 기본값
    RECOMMENDED_CREATION_FLAGS = 0
