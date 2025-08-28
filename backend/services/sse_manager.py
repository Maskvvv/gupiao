"""
Server-Sent Events (SSE) 流式推送管理器
用于实时推送任务进度和AI分析内容到前端
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set, Optional, AsyncGenerator
from fastapi import Request
from fastapi.responses import StreamingResponse
import weakref

# 导入数据库模型
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.streaming_models import TaskProgress, SessionLocal, now_bj

logger = logging.getLogger(__name__)

class SSEConnection:
    """SSE连接管理类"""
    
    def __init__(self, task_id: str, client_id: str):
        self.task_id = task_id
        self.client_id = client_id
        self.created_at = datetime.now()
        self.last_ping = datetime.now()
        self.queue = asyncio.Queue(maxsize=1000)  # 消息队列
        self.is_alive = True
        
    async def send_message(self, event_type: str, data: Dict[str, Any]):
        """发送消息到客户端"""
        if not self.is_alive:
            return
            
        try:
            message = {
                'event': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'task_id': self.task_id
            }
            
            # 非阻塞放入队列
            try:
                self.queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(f"⚠️ SSE队列已满，丢弃消息: {self.client_id}")
                
        except Exception as e:
            logger.error(f"❌ SSE发送消息失败: {e}")
            self.is_alive = False
    
    async def get_message_stream(self) -> AsyncGenerator[str, None]:
        """获取消息流"""
        try:
            while self.is_alive:
                try:
                    # 等待消息，超时检查连接状态
                    message = await asyncio.wait_for(self.queue.get(), timeout=30.0)
                    
                    # 格式化SSE消息
                    sse_data = f"event: {message['event']}\n"
                    sse_data += f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    
                    yield sse_data
                    
                except asyncio.TimeoutError:
                    # 发送心跳包
                    heartbeat = f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                    yield heartbeat
                    
                except Exception as e:
                    logger.error(f"❌ SSE消息流异常: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ SSE流异常: {e}")
        finally:
            self.is_alive = False

class SSEManager:
    """SSE连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, Set[SSEConnection]] = {}  # task_id -> connections
        self.client_connections: Dict[str, SSEConnection] = {}  # client_id -> connection
        self.connection_lock = asyncio.Lock()
        
    async def add_connection(self, task_id: str, client_id: str) -> SSEConnection:
        """添加SSE连接"""
        async with self.connection_lock:
            # 清理旧连接
            if client_id in self.client_connections:
                old_conn = self.client_connections[client_id]
                old_conn.is_alive = False
                await self._remove_connection_internal(old_conn)
            
            # 创建新连接
            connection = SSEConnection(task_id, client_id)
            
            # 添加到连接映射
            if task_id not in self.connections:
                self.connections[task_id] = set()
            self.connections[task_id].add(connection)
            self.client_connections[client_id] = connection
            
            logger.info(f"✅ 新增SSE连接: task={task_id}, client={client_id}")
            
            # 发送连接成功消息
            await connection.send_message('connected', {
                'message': '连接已建立',
                'task_id': task_id,
                'client_id': client_id
            })
            
            return connection
    
    async def remove_connection(self, client_id: str):
        """移除SSE连接"""
        async with self.connection_lock:
            if client_id in self.client_connections:
                connection = self.client_connections[client_id]
                connection.is_alive = False
                await self._remove_connection_internal(connection)
                logger.info(f"🔌 移除SSE连接: {client_id}")
    
    async def _remove_connection_internal(self, connection: SSEConnection):
        """内部移除连接方法"""
        task_id = connection.task_id
        client_id = connection.client_id
        
        # 从任务连接集合中移除
        if task_id in self.connections:
            self.connections[task_id].discard(connection)
            if not self.connections[task_id]:
                del self.connections[task_id]
        
        # 从客户端连接映射中移除
        if client_id in self.client_connections:
            del self.client_connections[client_id]
    
    async def broadcast_to_task(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """向指定任务的所有连接广播消息并保存进度到数据库"""
        # 始终记录到数据库，无论是否有SSE连接
        await self._save_progress_to_db(task_id, event_type, data)
        
        # 如果有活跃连接，广播到所有连接
        if task_id in self.connections:
            connections = list(self.connections[task_id])  # 创建副本避免并发修改
            
            for connection in connections:
                if connection.is_alive:
                    await connection.send_message(event_type, data)
                else:
                    # 清理死连接
                    await self._remove_connection_internal(connection)
    
    async def _save_progress_to_db(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """保存进度到数据库"""
        try:
            # 处理数据中的datetime对象，转换为字符串
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [serialize_datetime(item) for item in obj]
                else:
                    return obj
            
            # 清理数据
            clean_data = serialize_datetime(data)
            
            with SessionLocal() as db:
                progress = TaskProgress(
                    task_id=task_id,
                    event_type=event_type,
                    symbol=clean_data.get('symbol'),
                    phase=clean_data.get('phase'),
                    progress_data=json.dumps(clean_data),
                    ai_chunk_content=clean_data.get('chunk'),
                    accumulated_content=clean_data.get('accumulated'),
                    status=clean_data.get('status'),
                    message=clean_data.get('message')
                )
                db.add(progress)
                db.commit()
                logger.debug(f"✅ 进度已保存: {event_type} - {clean_data.get('symbol', '')}")
        except Exception as e:
            logger.error(f"❌ 保存进度到数据库失败: {e}")
    
    def get_connection_count(self, task_id: str = None) -> int:
        """获取连接数量"""
        if task_id:
            return len(self.connections.get(task_id, set()))
        else:
            return len(self.client_connections)
    
    def get_task_connection_counts(self) -> Dict[str, int]:
        """获取所有任务的连接数量"""
        return {task_id: len(connections) for task_id, connections in self.connections.items()}
    
    async def cleanup_dead_connections(self):
        """清理死连接"""
        async with self.connection_lock:
            dead_clients = []
            for client_id, connection in self.client_connections.items():
                if not connection.is_alive:
                    dead_clients.append(client_id)
            
            for client_id in dead_clients:
                connection = self.client_connections[client_id]
                await self._remove_connection_internal(connection)
                
            if dead_clients:
                logger.info(f"🧹 清理了 {len(dead_clients)} 个死连接")

class SSEStreamHandler:
    """SSE流处理器"""
    
    def __init__(self, sse_manager: SSEManager):
        self.sse_manager = sse_manager
    
    async def create_event_stream(self, task_id: str, client_id: str, request: Request) -> StreamingResponse:
        """创建事件流响应"""
        # 添加连接
        connection = await self.sse_manager.add_connection(task_id, client_id)
        
        async def event_generator():
            try:
                # 发送历史进度（如果有）
                await self._send_historical_progress(connection, task_id)
                
                # 开始流式传输
                async for message in connection.get_message_stream():
                    if await request.is_disconnected():
                        break
                    yield message
                    
            except Exception as e:
                logger.error(f"❌ SSE事件生成器异常: {e}")
            finally:
                # 清理连接
                await self.sse_manager.remove_connection(client_id)
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    
    async def _send_historical_progress(self, connection: SSEConnection, task_id: str):
        """发送历史进度"""
        try:
            with SessionLocal() as db:
                # 获取最近的进度记录
                recent_progress = db.query(TaskProgress).filter(
                    TaskProgress.task_id == task_id
                ).order_by(TaskProgress.timestamp.desc()).limit(10).all()
                
                # 逆序发送（从旧到新）
                for progress in reversed(recent_progress):
                    progress_data = {}
                    if progress.progress_data:
                        try:
                            progress_data = json.loads(progress.progress_data)
                        except:
                            pass
                    
                    await connection.send_message('historical_progress', {
                        'event_type': progress.event_type,
                        'symbol': progress.symbol,
                        'phase': progress.phase,
                        'data': progress_data,
                        'timestamp': progress.timestamp.isoformat() if progress.timestamp else None
                    })
                    
        except Exception as e:
            logger.error(f"❌ 发送历史进度失败: {e}")

# 全局SSE管理器实例
sse_manager = SSEManager()
sse_handler = SSEStreamHandler(sse_manager)

# 进度回调函数，用于与推荐引擎集成
async def progress_callback(progress_data: Dict[str, Any]):
    """进度回调函数，供推荐引擎调用"""
    task_id = progress_data.get('task_id')
    if not task_id:
        return
    
    event_type = progress_data.get('type', 'progress')
    
    # 广播进度更新
    await sse_manager.broadcast_to_task(task_id, event_type, progress_data)

# 在引擎启动时注册回调
def register_progress_callback():
    """注册进度回调"""
    from .streaming_ai_router import progress_manager
    
    # 为所有可能的任务注册回调
    # 这个会在引擎初始化时调用
    async def universal_callback(data):
        await progress_callback(data)
    
    return universal_callback