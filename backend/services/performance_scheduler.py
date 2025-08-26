"""
定时任务调度器
用于定期更新股票性能缓存
"""

import schedule
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any
from .performance_cache import performance_cache_service

logger = logging.getLogger(__name__)

class PerformanceScheduler:
    """性能缓存定时调度器"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self._stop_event = threading.Event()
        
    def start(self):
        """启动定时调度器"""
        if self.is_running:
            logger.warning("定时调度器已在运行中")
            return
            
        self.is_running = True
        self._stop_event.clear()
        
        # 配置定时任务
        # 每日收盘后更新（下午3:30）
        schedule.every().day.at("15:30").do(self._daily_update_job)
        
        # 每小时更新一次（交易时间内）
        schedule.every().hour.do(self._hourly_update_job)
        
        # 每周清理一次过期缓存（周日凌晨2点）
        schedule.every().sunday.at("02:00").do(self._weekly_cleanup_job)
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("性能缓存定时调度器已启动")
        
    def stop(self):
        """停止定时调度器"""
        if not self.is_running:
            return
            
        self.is_running = False
        self._stop_event.set()
        
        # 清空所有任务
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        logger.info("性能缓存定时调度器已停止")
        
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.is_running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行异常: {str(e)}")
                time.sleep(60)
                
    def _daily_update_job(self):
        """每日更新任务"""
        logger.info("开始执行每日性能缓存更新...")
        try:
            result = performance_cache_service.batch_update_performance()
            logger.info(f"每日更新完成: {result}")
        except Exception as e:
            logger.error(f"每日更新失败: {str(e)}")
            
    def _hourly_update_job(self):
        """每小时更新任务（仅在交易时间内）"""
        now = datetime.now()
        # 只在交易时间内执行（9:30-15:00，周一至周五）
        if (now.weekday() < 5 and  # 周一至周五
            ((9 <= now.hour < 15) or (now.hour == 9 and now.minute >= 30))):
            
            logger.info("开始执行小时性能缓存更新...")
            try:
                result = performance_cache_service.batch_update_performance()
                logger.info(f"小时更新完成: {result}")
            except Exception as e:
                logger.error(f"小时更新失败: {str(e)}")
                
    def _weekly_cleanup_job(self):
        """每周清理任务"""
        logger.info("开始执行每周缓存清理...")
        try:
            cleaned_count = performance_cache_service.clean_expired_cache()
            logger.info(f"每周清理完成，清理记录数: {cleaned_count}")
        except Exception as e:
            logger.error(f"每周清理失败: {str(e)}")
            
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "next_jobs": [
                {
                    "job": str(job.job_func.__name__),
                    "next_run": job.next_run.isoformat() if job.next_run else None
                }
                for job in schedule.jobs
            ],
            "cache_summary": performance_cache_service.get_performance_summary()
        }
        
    def trigger_manual_update(self, symbols=None) -> Dict[str, Any]:
        """手动触发更新"""
        logger.info(f"手动触发性能缓存更新: {symbols}")
        try:
            result = performance_cache_service.batch_update_performance(symbols)
            logger.info(f"手动更新完成: {result}")
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"手动更新失败: {str(e)}")
            return {"success": False, "error": str(e)}

# 全局调度器实例
performance_scheduler = PerformanceScheduler()