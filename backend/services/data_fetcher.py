import os
import re
import akshare as ak
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import pickle
import hashlib

class DataFetcher:
    def __init__(self, source: str = "akshare"):
        """
        初始化A股数据获取器
        
        Args:
            source: 数据源类型，固定为'akshare'专注A股
        """
        self.source = source
        # 简易文件缓存设置
        self.cache_dir = os.path.join(os.getcwd(), ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            self.cache_expiry = int(os.getenv("CACHE_EXPIRY", "3600"))
        except Exception:
            self.cache_expiry = 3600

    def _cache_key(self, symbol: str, period: str) -> str:
        raw = f"{symbol}:{period}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.pkl")

    def _load_cache(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        key = self._cache_key(symbol, period)
        path = self._cache_path(key)
        if not os.path.exists(path):
            return None
        try:
            mtime = os.path.getmtime(path)
            if (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds() > self.cache_expiry:
                return None
            with open(path, "rb") as f:
                df = pickle.load(f)
            return df
        except Exception:
            return None

    def _save_cache(self, symbol: str, period: str, df: pd.DataFrame) -> None:
        try:
            key = self._cache_key(symbol, period)
            path = self._cache_path(key)
            with open(path, "wb") as f:
                pickle.dump(df, f)
        except Exception:
            pass

    def normalize_stock_code(self, symbol: str) -> str:
        """
        标准化A股股票代码
        
        Args:
            symbol: 原始股票代码
            
        Returns:
            标准化后的6位股票代码
        """
        # 移除所有非数字字符
        clean_code = re.sub(r'[^\d]', '', symbol)
        
        # 确保是6位数字
        if len(clean_code) == 6 and clean_code.isdigit():
            return clean_code
        elif len(clean_code) < 6 and clean_code.isdigit():
            # 补齐前导零
            return clean_code.zfill(6)
        else:
            raise ValueError(f"无效的A股代码格式: {symbol}")
    
    def validate_a_stock_code(self, code: str) -> Tuple[bool, str]:
        """
        验证是否为有效的A股代码
        
        Args:
            code: 股票代码
            
        Returns:
            (是否有效, 市场信息)
        """
        try:
            normalized = self.normalize_stock_code(code)
            
            # A股代码规则
            first_digit = normalized[0]
            if first_digit in ['0', '3']:  # 深交所
                if first_digit == '0':
                    if normalized.startswith('000'):
                        return True, "深交所主板"
                    elif normalized.startswith('002'):
                        return True, "深交所中小板"
                elif first_digit == '3':
                    return True, "深交所创业板"
            elif first_digit == '6':  # 上交所
                return True, "上交所主板"
            elif first_digit == '8':  # 北交所
                return True, "北交所"
            
            return False, "非A股代码"
        except:
            return False, "代码格式错误"
    
    def get_stock_data(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        获取A股历史数据
        
        Args:
            symbol: 股票代码
            period: 时间周期
            
        Returns:
            包含股票数据的DataFrame或None
        """
        try:
            # 标准化股票代码
            normalized_code = self.normalize_stock_code(symbol)
            
            # 验证是否为A股代码
            is_valid, market_info = self.validate_a_stock_code(normalized_code)
            if not is_valid:
                raise ValueError(f"非A股代码: {symbol} ({market_info})")

            # 缓存命中
            cached = self._load_cache(normalized_code, period)
            if cached is not None and not cached.empty:
                return cached
            
            df = self._fetch_akshare_data(normalized_code, period)
            if df is not None and not df.empty:
                self._save_cache(normalized_code, period, df)
            return df
        except Exception as e:
            print(f"获取A股数据失败: {e}")
            return None
    
    def _fetch_akshare_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """使用akshare获取A股数据"""
        # 将period转换为具体的日期范围
        period_map = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825
        }
        
        days = period_map.get(period, 365)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        try:
            # 获取A股历史数据（前复权）
            data = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily", 
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if data is not None and not data.empty:
                # 重命名列以保持一致性
                column_mapping = {
                    '日期': 'Date',
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume',
                    '成交额': 'Amount',
                    '振幅': 'Amplitude',
                    '涨跌幅': 'Change_pct',
                    '涨跌额': 'Change_amount',
                    '换手率': 'Turnover'
                }
                
                # 只保留存在的列
                available_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
                data = data.rename(columns=available_columns)
                
                # 设置日期为索引
                data['Date'] = pd.to_datetime(data['Date'])
                data.set_index('Date', inplace=True)
                
                # 确保数值列为float类型
                numeric_columns = ['Open', 'Close', 'High', 'Low', 'Volume']
                for col in numeric_columns:
                    if col in data.columns:
                        data[col] = pd.to_numeric(data[col], errors='coerce')
                
                return data
        except Exception as e:
            print(f"akshare数据获取失败: {e}")
            
        return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取A股基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票基本信息字典
        """
        try:
            normalized_code = self.normalize_stock_code(symbol)
            is_valid, market_info = self.validate_a_stock_code(normalized_code)
            
            if not is_valid:
                return None
            
            # 获取股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=normalized_code)
            
            if stock_info is not None and not stock_info.empty:
                info_dict = dict(zip(stock_info['item'], stock_info['value']))
                info_dict['market'] = market_info
                info_dict['code'] = normalized_code
                return info_dict
            
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            
        return None