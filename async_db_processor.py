"""
Phase 3: 비동기 DB → C 코드 변환 프로세서
asyncio + aiosqlite를 이용한 비동기 처리 구현
"""

import asyncio
import aiosqlite
import time
import gc
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

@dataclass
class AsyncConfig:
    """비동기 처리 설정"""
    batch_size: int = 500
    chunk_size: int = 1000
    gc_interval: int = 4
    max_concurrent_dbs: int = 8
    max_concurrent_sheets: int = 16
    connection_timeout: float = 30.0
    query_timeout: float = 10.0
    enable_connection_pooling: bool = True
    pool_size: int = 20

class AsyncConnectionPool:
    """비동기 DB 연결 풀"""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.connections = {}
        self.semaphore = asyncio.Semaphore(max_connections)
        self.logger = logging.getLogger(__name__)
    
    async def get_connection(self, db_path: str) -> aiosqlite.Connection:
        """비동기 연결 가져오기"""
        async with self.semaphore:
            if db_path not in self.connections:
                try:
                    conn = await aiosqlite.connect(db_path)
                    # SQLite 최적화 설정
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.execute("PRAGMA synchronous=NORMAL")
                    await conn.execute("PRAGMA cache_size=10000")
                    await conn.execute("PRAGMA temp_store=MEMORY")
                    
                    self.connections[db_path] = conn
                    self.logger.info(f"비동기 DB 연결 생성: {Path(db_path).name}")
                except Exception as e:
                    self.logger.error(f"비동기 DB 연결 실패 {db_path}: {e}")
                    raise
            
            return self.connections[db_path]
    
    async def close_all(self):
        """모든 연결 해제"""
        for db_path, conn in self.connections.items():
            try:
                await conn.close()
                self.logger.info(f"비동기 DB 연결 해제: {Path(db_path).name}")
            except Exception as e:
                self.logger.error(f"비동기 DB 연결 해제 실패 {db_path}: {e}")
        
        self.connections.clear()

class AsyncDBProcessor:
    """비동기 DB → C 코드 변환 프로세서"""
    
    def __init__(self, config: AsyncConfig = None):
        self.config = config or AsyncConfig()
        self.connection_pool = AsyncConnectionPool(self.config.pool_size) if self.config.enable_connection_pooling else None
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_files_processed': 0,
            'total_items_processed': 0,
            'total_execution_time': 0,
            'concurrent_operations': 0
        }
    
    async def get_sheets_async(self, conn: aiosqlite.Connection) -> List[Dict[str, Any]]:
        """비동기 시트 목록 조회"""
        query = """
        SELECT id, name, source_file, is_dollar_sheet 
        FROM sheets 
        WHERE is_dollar_sheet = 1
        ORDER BY id
        """
        
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            
        return [
            {
                'id': row[0],
                'name': row[1],
                'source_file': row[2],
                'is_dollar_sheet': bool(row[3])
            }
            for row in rows
        ]
    
    async def get_sheet_data_async(self, conn: aiosqlite.Connection, sheet_id: int) -> List[tuple]:
        """비동기 시트 데이터 조회"""
        query = """
        SELECT row, col, value
        FROM cells
        WHERE sheet_id = ?
        ORDER BY row, col
        """

        async with conn.execute(query, (sheet_id,)) as cursor:
            rows = await cursor.fetchall()

        return rows
    
    async def process_sheet_async(self, conn: aiosqlite.Connection, sheet: Dict[str, Any]) -> int:
        """비동기 시트 처리"""
        try:
            sheet_data = await self.get_sheet_data_async(conn, sheet['id'])
            if not sheet_data:
                return 0
            
            self.logger.debug(f"비동기 시트 처리: {sheet['name']} ({len(sheet_data)}개 셀)")
            
            # Ultra 최적화된 Cython 모듈 사용
            from cython_extensions.code_generator_v2 import ultra_fast_write_cal_list_processing
            
            total_processed_items = 0
            
            # 청크 단위로 비동기 처리
            for chunk_start in range(0, len(sheet_data), self.config.chunk_size):
                chunk_end = min(chunk_start + self.config.chunk_size, len(sheet_data))
                chunk_data = sheet_data[chunk_start:chunk_end]
                
                # 배치 단위로 코드 생성
                batch_count = 0
                for batch_start in range(0, len(chunk_data), self.config.batch_size):
                    batch_end = min(batch_start + self.config.batch_size, len(chunk_data))
                    batch_data = chunk_data[batch_start:batch_end]
                    
                    # 코드 아이템 생성
                    code_items = []
                    for row_data in batch_data:
                        if len(row_data) >= 3:
                            code_items.append([
                                "DEFINE", "CONST", "FLOAT32",
                                f"VAL_{row_data[0]}_{row_data[1]}", 
                                str(row_data[2]) if row_data[2] else "",
                                f"Generated from {sheet['name']}"
                            ])
                    
                    # Ultra 최적화된 Cython 코드 생성
                    if code_items:
                        processed_code = ultra_fast_write_cal_list_processing(code_items)
                        total_processed_items += len(processed_code)
                    
                    # 배치 간 메모리 정리
                    del code_items
                    if 'processed_code' in locals():
                        del processed_code
                    
                    batch_count += 1
                    
                    # 주기적 가비지 컬렉션
                    if batch_count % self.config.gc_interval == 0:
                        gc.collect()
                    
                    # 비동기 양보 (다른 코루틴에게 실행 기회 제공)
                    if batch_count % 10 == 0:
                        await asyncio.sleep(0)
            
            return total_processed_items
            
        except Exception as e:
            self.logger.error(f"비동기 시트 처리 실패 {sheet['name']}: {e}")
            return 0
    
    async def process_single_db_async(self, db_file: Path) -> Dict[str, Any]:
        """비동기 단일 DB 처리"""
        start_time = time.perf_counter()
        file_name = db_file.name
        
        try:
            self.logger.info(f"비동기 DB 처리 시작: {file_name}")
            
            # 비동기 연결 풀 사용
            if self.connection_pool:
                conn = await self.connection_pool.get_connection(str(db_file))
            else:
                conn = await aiosqlite.connect(str(db_file))
            
            # $ 시트 찾기
            sheets = await self.get_sheets_async(conn)
            
            if not sheets:
                self.logger.warning(f"$ 시트가 없음: {file_name}")
                return {
                    'success': True,
                    'file_name': file_name,
                    'execution_time': time.perf_counter() - start_time,
                    'processed_items': 0,
                    'warning': 'No dollar sheets found'
                }
            
            # 시트들을 동시에 비동기 처리
            semaphore = asyncio.Semaphore(self.config.max_concurrent_sheets)
            
            async def process_sheet_with_semaphore(sheet):
                async with semaphore:
                    return await self.process_sheet_async(conn, sheet)
            
            # 모든 시트를 동시에 처리
            tasks = [process_sheet_with_semaphore(sheet) for sheet in sheets]
            sheet_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 집계
            total_processed_items = 0
            for result in sheet_results:
                if isinstance(result, int):
                    total_processed_items += result
                else:
                    self.logger.error(f"시트 처리 오류: {result}")
            
            # 연결 풀을 사용하지 않는 경우에만 연결 해제
            if not self.connection_pool:
                await conn.close()
            
            execution_time = time.perf_counter() - start_time
            
            self.logger.info(f"비동기 DB 처리 완료: {file_name} ({execution_time:.3f}초, {total_processed_items:,}개 항목)")
            
            return {
                'success': True,
                'file_name': file_name,
                'execution_time': execution_time,
                'processed_items': total_processed_items,
                'sheets_processed': len(sheets)
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            error_msg = f"비동기 DB 처리 실패: {file_name} - {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'file_name': file_name,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    async def process_batch_async(self, db_files: List[Path]) -> Dict[str, Any]:
        """비동기 일괄 처리"""
        start_time = time.perf_counter()
        
        self.logger.info(f"비동기 일괄 처리 시작: {len(db_files)}개 파일")
        
        # DB 파일들을 동시에 비동기 처리
        semaphore = asyncio.Semaphore(self.config.max_concurrent_dbs)
        
        async def process_db_with_semaphore(db_file):
            async with semaphore:
                return await self.process_single_db_async(db_file)
        
        # 모든 DB 파일을 동시에 처리
        tasks = [process_db_with_semaphore(db_file) for db_file in db_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for result in results:
            if isinstance(result, dict):
                processed_results.append(result)
            else:
                self.logger.error(f"DB 처리 오류: {result}")
                processed_results.append({
                    'success': False,
                    'error': str(result)
                })
        
        execution_time = time.perf_counter() - start_time
        
        # 통계 업데이트
        successful_results = [r for r in processed_results if r['success']]
        total_processed_items = sum(r.get('processed_items', 0) for r in successful_results)
        
        self.stats['total_files_processed'] += len(successful_results)
        self.stats['total_items_processed'] += total_processed_items
        self.stats['total_execution_time'] += execution_time
        
        self.logger.info(f"비동기 일괄 처리 완료: {execution_time:.3f}초, {total_processed_items:,}개 항목")
        
        return {
            'success': True,
            'execution_time': execution_time,
            'total_processed_items': total_processed_items,
            'files_processed': len(successful_results),
            'files_failed': len(processed_results) - len(successful_results),
            'results': processed_results,
            'processing_mode': 'async'
        }
    
    async def cleanup(self):
        """리소스 정리"""
        self.logger.info("비동기 리소스 정리 시작")
        
        if self.connection_pool:
            await self.connection_pool.close_all()
        
        gc.collect()
        self.logger.info("비동기 리소스 정리 완료")

async def main():
    """비동기 메인 실행 함수"""
    print("🚀 Phase 3: 비동기 DB → C 코드 변환 프로세서")
    print("=" * 80)
    
    # 설정
    config = AsyncConfig(
        batch_size=500,
        chunk_size=1000,
        gc_interval=4,
        max_concurrent_dbs=8,
        max_concurrent_sheets=16,
        enable_connection_pooling=True,
        pool_size=20
    )
    
    # DB 파일 수집
    db_dir = Path('database')
    if not db_dir.exists():
        print("❌ Database 디렉토리가 존재하지 않습니다.")
        return
    
    db_files = [f for f in db_dir.glob('*.db') if f.stat().st_size > 50000]
    
    if not db_files:
        print("❌ 처리할 DB 파일이 없습니다.")
        return
    
    print(f"📁 처리 대상: {len(db_files)}개 파일")
    
    # 비동기 프로세서 생성 및 실행
    processor = AsyncDBProcessor(config)
    
    try:
        # 비동기 일괄 처리 실행
        result = await processor.process_batch_async(db_files)
        
        # 결과 출력
        print(f"\n📊 비동기 처리 결과:")
        print(f"   실행 시간: {result['execution_time']:.3f}초")
        print(f"   처리 항목: {result['total_processed_items']:,}개")
        print(f"   성공 파일: {result['files_processed']}개")
        print(f"   실패 파일: {result['files_failed']}개")
        print(f"   처리 모드: {result['processing_mode']}")
        
        # 처리 속도 계산
        if result['execution_time'] > 0:
            items_per_second = result['total_processed_items'] / result['execution_time']
            print(f"   처리 속도: {items_per_second:,.0f} 항목/초")
        
        # 결과 저장
        with open('async_processing_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'result': result,
                'config': config.__dict__
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 결과가 'async_processing_results.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 비동기 처리 실패: {e}")
        logging.error(f"비동기 처리 실패: {e}")
    
    finally:
        await processor.cleanup()
    
    print("=" * 80)

if __name__ == "__main__":
    # aiosqlite 설치 확인
    try:
        import aiosqlite
    except ImportError:
        print("❌ aiosqlite가 설치되지 않았습니다.")
        print("설치 명령: pip install aiosqlite")
        sys.exit(1)
    
    asyncio.run(main())
