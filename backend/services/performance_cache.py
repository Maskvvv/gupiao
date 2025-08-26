"""
股票性能缓存服务
用于高效计算和缓存股票的累计涨跌幅，解决性能问题
"""

import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from ..routes import SessionLocal, PerformanceCache, Watchlist, now_bj
from .data_fetcher import DataFetcher
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceCacheService:
    """性能缓存服务"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self._lock = threading.Lock()
    
    def get_or_calculate_performance(self, symbol: str, watchlist_added_date: datetime) -> Optional[Dict]:
        """
        获取或计算股票的累计涨跌幅
        
        Args:
            symbol: 股票代码
            watchlist_added_date: 加入自选股的日期
            
        Returns:
            包含累计涨跌幅信息的字典或None
        """
        with SessionLocal() as db:
            # 首先尝试从缓存获取
            cache = db.query(PerformanceCache).filter(
                PerformanceCache.symbol == symbol,
                PerformanceCache.watchlist_added_date == watchlist_added_date
            ).first()
            
            # 判断缓存是否需要更新（超过1小时或不存在）
            now = now_bj()
            cache_expired = (
                cache is None or 
                (now - cache.last_updated).total_seconds() > 3600
            )
            
            if cache_expired:
                # 重新计算并更新缓存
                performance_data = self._calculate_performance(symbol, watchlist_added_date)
                if performance_data is None:
                    return None
                
                if cache:
                    # 更新现有缓存
                    cache.current_price = performance_data['current_price']
                    cache.cumulative_return_pct = performance_data['cumulative_return_pct']
                    cache.cumulative_return_amount = performance_data['cumulative_return_amount']
                    cache.last_updated = now
                    db.commit()
                else:
                    # 创建新缓存
                    cache = PerformanceCache(
                        symbol=symbol,
                        watchlist_added_date=watchlist_added_date,
                        base_price=performance_data['base_price'],
                        current_price=performance_data['current_price'],
                        cumulative_return_pct=performance_data['cumulative_return_pct'],
                        cumulative_return_amount=performance_data['cumulative_return_amount'],
                        last_updated=now,
                        created_at=now
                    )
                    db.add(cache)
                    db.commit()
            
            return {
                'symbol': cache.symbol,
                'base_price': cache.base_price,
                'current_price': cache.current_price,
                'cumulative_return_pct': cache.cumulative_return_pct,
                'cumulative_return_amount': cache.cumulative_return_amount,
                'last_updated': cache.last_updated
            }
    
    def _calculate_performance(self, symbol: str, watchlist_added_date: datetime) -> Optional[Dict]:
        """
        计算股票的累计涨跌幅
        
        Args:
            symbol: 股票代码
            watchlist_added_date: 加入自选股的日期
            
        Returns:
            包含计算结果的字典或None
        """
        try:
            # 计算需要获取的数据周期
            now = now_bj()
            days_since_added = max(1, (now - watchlist_added_date).days)
            
            # 根据时间跨度选择合适的周期
            if days_since_added <= 7:
                period = "1mo"
            elif days_since_added <= 90:
                period = "6mo"
            elif days_since_added <= 365:
                period = "1y"
            elif days_since_added <= 730:
                period = "2y"
            else:
                period = "5y"
            
            # 获取股票数据
            df = self.data_fetcher.get_stock_data(symbol, period=period)
            if df is None or df.empty:
                logger.warning(f"无法获取股票 {symbol} 的数据")
                return None
            
            # 确保数据按日期排序
            df_sorted = df.sort_index()
            
            # 找到加入日期当天或之后的第一个交易日数据
            target_date = watchlist_added_date.date()
            available_dates = [idx.date() for idx in df_sorted.index]
            
            # 找到加入日期当天或之后的第一个有效数据
            base_date = None
            for date in available_dates:
                if date >= target_date:
                    base_date = date
                    break
            
            # 如果找不到加入日期之后的数据，使用最接近的前一个交易日
            if base_date is None:
                closest_dates = [date for date in available_dates if date < target_date]
                if closest_dates:
                    base_date = max(closest_dates)
                else:
                    # 如果连前面的数据都没有，使用最早的数据
                    base_date = min(available_dates)
            
            # 获取基准价格和当前价格
            base_price = None
            current_price = None
            
            for idx, row in df_sorted.iterrows():
                if idx.date() == base_date:
                    base_price = float(row['Close'])
                    break
            
            # 获取最新价格
            current_price = float(df_sorted['Close'].iloc[-1])
            
            if base_price is None or current_price is None or base_price <= 0:
                logger.warning(f"股票 {symbol} 的价格数据无效: base_price={base_price}, current_price={current_price}")
                return None
            
            # 计算累计涨跌幅
            cumulative_return_pct = round((current_price / base_price - 1.0) * 100.0, 2)
            cumulative_return_amount = round(current_price - base_price, 3)
            
            return {
                'base_price': base_price,
                'current_price': current_price,
                'cumulative_return_pct': cumulative_return_pct,
                'cumulative_return_amount': cumulative_return_amount
            }
            
        except Exception as e:
            logger.error(f"计算股票 {symbol} 累计涨跌幅失败: {str(e)}")
            return None
    
    def batch_update_performance(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        批量更新股票性能缓存
        
        Args:
            symbols: 要更新的股票代码列表，为None时更新所有自选股
            
        Returns:
            更新结果统计
        """
        with self._lock:
            with SessionLocal() as db:
                if symbols is None:
                    # 获取所有自选股
                    watchlist_items = db.query(Watchlist).all()
                    symbols = [item.symbol for item in watchlist_items]
                else:
                    # 获取指定的自选股
                    watchlist_items = db.query(Watchlist).filter(
                        Watchlist.symbol.in_(symbols)
                    ).all()
                
                success_count = 0
                error_count = 0
                updated_symbols = []
                
                for item in watchlist_items:
                    try:
                        result = self.get_or_calculate_performance(
                            item.symbol, 
                            item.created_at
                        )
                        if result:
                            success_count += 1
                            updated_symbols.append(item.symbol)
                        else:
                            error_count += 1
                            logger.warning(f"更新股票 {item.symbol} 性能缓存失败")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"更新股票 {item.symbol} 性能缓存异常: {str(e)}")
                
                return {
                    'total': len(watchlist_items),
                    'success': success_count,
                    'error': error_count,
                    'updated_symbols': updated_symbols
                }
    
    def clean_expired_cache(self, days: int = 30) -> int:
        """
        清理过期的缓存数据
        
        Args:
            days: 保留最近几天的缓存，默认30天
            
        Returns:
            清理的记录数
        """
        cutoff_date = now_bj() - timedelta(days=days)
        
        with SessionLocal() as db:
            # 清理不在自选股中的缓存
            expired_cache = db.query(PerformanceCache).filter(
                ~PerformanceCache.symbol.in_(
                    db.query(Watchlist.symbol).subquery()
                )
            )
            count = expired_cache.count()
            expired_cache.delete(synchronize_session=False)
            
            # 清理过期的缓存（可选）
            old_cache = db.query(PerformanceCache).filter(
                PerformanceCache.last_updated < cutoff_date
            )
            count += old_cache.count()
            old_cache.delete(synchronize_session=False)
            
            db.commit()
            return count
    
    def get_performance_summary(self) -> Dict:
        """
        获取性能缓存的统计信息
        
        Returns:
            缓存统计信息
        """
        with SessionLocal() as db:
            total_cache = db.query(PerformanceCache).count()
            
            # 最近1小时内更新的缓存
            recent_updated = db.query(PerformanceCache).filter(
                PerformanceCache.last_updated >= now_bj() - timedelta(hours=1)
            ).count()
            
            return {
                'total_cache_records': total_cache,
                'recently_updated': recent_updated,
                'cache_hit_rate': round(recent_updated / max(total_cache, 1) * 100, 2)
            }

# 全局实例
performance_cache_service = PerformanceCacheService()