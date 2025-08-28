"""
流式推荐任务管理数据库模型
用于替代原有的推荐系统表结构，支持流式处理和任务管理
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, create_engine, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os
import json

# 北京时间时区
BJ_TZ = timezone(timedelta(hours=8))

def now_bj():
    """返回北京时间（UTC+8）的naive datetime"""
    return datetime.now(BJ_TZ).replace(tzinfo=None)

Base = declarative_base()

class RecommendationTask(Base):
    """统一的推荐任务表（取代原有的Recommendation表）"""
    __tablename__ = "recommendation_tasks"
    
    # 任务基本信息
    id = Column(String(32), primary_key=True)  # UUID
    task_type = Column(String(20), nullable=False)  # 'ai'|'keyword'|'market'
    status = Column(String(20), default='pending')  # 'pending'|'running'|'completed'|'failed'|'cancelled'
    priority = Column(Integer, default=5)  # 优先级 1-10
    
    # 时间戳
    created_at = Column(DateTime, default=now_bj, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=now_bj, onupdate=now_bj)
    
    # 任务参数(JSON)
    request_params = Column(Text)  # 原始请求参数
    ai_config = Column(Text)  # AI相关配置
    filter_config = Column(Text)  # 筛选配置
    weights_config = Column(Text)  # 权重配置
    
    # 执行状态
    total_symbols = Column(Integer, default=0)  # 总处理股票数
    completed_symbols = Column(Integer, default=0)  # 已完成股票数
    current_symbol = Column(String(16))  # 当前处理股票
    current_phase = Column(String(32))  # 当前阶段 'screening'|'analyzing'|'ranking'
    progress_percent = Column(Float, default=0.0)  # 进度百分比
    
    # 结果统计
    successful_count = Column(Integer, default=0)  # 成功分析数
    failed_count = Column(Integer, default=0)  # 失败分析数
    final_recommendations = Column(Integer, default=0)  # 最终推荐数
    
    # 错误处理
    error_message = Column(Text)
    error_details = Column(Text)  # 详细错误信息(JSON)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # 性能指标
    total_tokens_used = Column(Integer, default=0)  # AI Token消耗
    total_api_calls = Column(Integer, default=0)  # API调用次数
    execution_time_seconds = Column(Float)  # 执行时间
    
    # 用户详情字段（用于任务详情页面显示）
    user_input_summary = Column(Text)  # 用户输入摘要
    filter_summary = Column(Text)  # 筛选条件摘要
    ai_prompt_used = Column(Text)  # AI提示词（用于用户查看AI如何理解任务）
    execution_strategy = Column(Text)  # 执行策略说明
    candidate_stocks_info = Column(Text)  # 候选股票信息（JSON）
    
    @property
    def is_running(self):
        """计算属性：任务是否正在运行"""
        return self.status == 'running'
    
    # 关联关系
    results = relationship("RecommendationResult", back_populates="task", cascade="all, delete-orphan")
    progress_logs = relationship("TaskProgress", back_populates="task", cascade="all, delete-orphan")

class RecommendationResult(Base):
    """推荐结果表（替代原有的RecommendationItem）"""
    __tablename__ = "recommendation_results"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(32), ForeignKey("recommendation_tasks.id"), index=True)
    
    # 股票信息
    symbol = Column(String(16), index=True)
    name = Column(String(64))
    market = Column(String(16))  # 'A'|'US'|'HK'
    
    # 分析结果
    technical_score = Column(Float)  # 技术分数
    ai_score = Column(Float)  # AI分数
    fusion_score = Column(Float)  # 融合分数
    final_score = Column(Float)  # 最终分数
    action = Column(String(16))  # 建议动作 'buy'|'hold'|'sell'
    
    # AI分析内容
    ai_analysis = Column(Text)  # AI完整分析
    ai_confidence = Column(Float)  # AI信心度
    ai_reasoning = Column(Text)  # AI推理过程
    ai_risk_assessment = Column(Text)  # AI风险评估
    
    # 技术分析内容
    technical_indicators = Column(Text)  # 技术指标详情(JSON)
    support_resistance = Column(Text)  # 支撑阻力位(JSON)
    trend_analysis = Column(Text)  # 趋势分析(JSON)
    
    # 摘要信息
    summary = Column(Text)  # 简要描述
    key_factors = Column(Text)  # 关键因子(JSON)
    risk_factors = Column(Text)  # 风险因子(JSON)
    
    # 排序和筛选
    rank_in_task = Column(Integer)  # 在任务中的排名
    is_recommended = Column(Boolean, default=False)  # 是否被推荐
    recommendation_reason = Column(Text)  # 推荐理由
    
    # 市场数据快照
    current_price = Column(Float)  # 分析时价格
    price_change_pct = Column(Float)  # 价格变化百分比
    volume = Column(Float)  # 成交量
    market_cap = Column(Float)  # 市值
    
    # 时间戳
    analyzed_at = Column(DateTime, default=now_bj)
    data_date = Column(DateTime)  # 数据日期
    
    # 关联关系
    task = relationship("RecommendationTask", back_populates="results")

class TaskProgress(Base):
    """任务流式进度记录表"""
    __tablename__ = "task_progress"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(32), ForeignKey("recommendation_tasks.id"), index=True)
    timestamp = Column(DateTime, default=now_bj, index=True)
    
    # 进度信息
    event_type = Column(String(20))  # 'start'|'progress'|'ai_chunk'|'symbol_complete'|'phase_change'|'complete'|'error'
    symbol = Column(String(16))  # 当前处理的股票
    phase = Column(String(32))  # 当前阶段
    progress_data = Column(Text)  # 进度数据(JSON)
    
    # AI流式数据
    ai_chunk_content = Column(Text)  # AI流式返回的数据块
    ai_chunk_sequence = Column(Integer)  # AI数据块序号
    accumulated_content = Column(Text)  # 累积的AI内容
    
    # 状态和消息
    status = Column(String(20))  # 状态
    message = Column(Text)  # 消息内容
    
    # 性能数据
    processing_time_ms = Column(Integer)  # 处理时间（毫秒）
    memory_usage_mb = Column(Float)  # 内存使用（MB）
    
    # 关联关系
    task = relationship("RecommendationTask", back_populates="progress_logs")

class TaskSchedule(Base):
    """任务调度配置表"""
    __tablename__ = "task_schedules"
    
    id = Column(Integer, primary_key=True)
    schedule_name = Column(String(64), unique=True, index=True)  # 调度名称
    task_type = Column(String(20))  # 任务类型
    cron_expression = Column(String(32))  # Cron表达式
    is_enabled = Column(Boolean, default=True)  # 是否启用
    
    # 调度参数
    schedule_params = Column(Text)  # 调度参数(JSON)
    max_concurrent_tasks = Column(Integer, default=1)  # 最大并发任务数
    timeout_seconds = Column(Integer, default=3600)  # 超时时间
    
    # 状态信息
    last_run_time = Column(DateTime)  # 上次运行时间
    next_run_time = Column(DateTime)  # 下次运行时间
    last_task_id = Column(String(32))  # 最后一次创建的任务ID
    success_count = Column(Integer, default=0)  # 成功次数
    failure_count = Column(Integer, default=0)  # 失败次数
    
    # 时间戳
    created_at = Column(DateTime, default=now_bj)
    updated_at = Column(DateTime, default=now_bj, onupdate=now_bj)

class SystemMetrics(Base):
    """系统性能指标表"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True)
    metric_time = Column(DateTime, default=now_bj, index=True)
    
    # 任务统计
    pending_tasks = Column(Integer, default=0)
    running_tasks = Column(Integer, default=0)
    completed_tasks_today = Column(Integer, default=0)
    failed_tasks_today = Column(Integer, default=0)
    
    # 系统资源
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    disk_usage_percent = Column(Float)
    
    # API调用统计
    openai_calls_today = Column(Integer, default=0)
    deepseek_calls_today = Column(Integer, default=0)
    gemini_calls_today = Column(Integer, default=0)
    total_tokens_today = Column(Integer, default=0)
    
    # 错误统计
    api_errors_today = Column(Integer, default=0)
    system_errors_today = Column(Integer, default=0)
    
    # 性能指标
    avg_task_execution_time = Column(Float)  # 平均任务执行时间（秒）
    avg_symbol_analysis_time = Column(Float)  # 平均单股分析时间（秒）

# 创建数据库引擎和会话 - 使用原有项目数据库
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a_stock_analysis.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)

# MySQL 会话时区设置
if engine.url.get_backend_name().startswith("mysql"):
    @event.listens_for(engine, "connect")
    def _set_mysql_session_timezone(dbapi_conn, conn_record):
        try:
            with dbapi_conn.cursor() as cur:
                cur.execute("SET time_zone = '+08:00'")
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """创建所有表"""
    Base.metadata.create_all(engine)
    print("✅ 流式推荐任务数据库表创建完成")

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 数据迁移工具
class DatabaseMigrator:
    """数据库迁移工具类"""
    
    def __init__(self, engine):
        self.engine = engine
    
    def migrate_from_old_tables(self):
        """从旧的推荐表迁移数据到新表"""
        try:
            # 这里可以实现从 recommendations 和 recommendation_items 表迁移数据的逻辑
            # 由于用户要求可以舍弃历史数据，这里暂不实现
            print("📝 数据迁移：由于完全重构，历史数据将不会迁移")
            return True
        except Exception as e:
            print(f"❌ 数据迁移失败: {e}")
            return False
    
    def backup_old_tables(self):
        """备份旧表（可选）"""
        try:
            # 实现备份逻辑（如果需要的话）
            print("💾 旧表备份：暂不实现")
            return True
        except Exception as e:
            print(f"❌ 表备份失败: {e}")
            return False

if __name__ == "__main__":
    # 创建表
    create_tables()
    
    # 可选：迁移数据
    migrator = DatabaseMigrator(engine)
    migrator.migrate_from_old_tables()