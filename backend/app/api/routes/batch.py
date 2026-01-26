"""批量简历处理API - 后台异步处理模式"""
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Depends
from typing import List
import json
import asyncio

from app.services.task_manager import task_manager, TaskStatus
from app.api.middleware.auth import require_auth, User

router = APIRouter(prefix="/api/batch", tags=["批量处理"])


@router.post("/upload")
async def create_batch_task(files: List[UploadFile] = File(...), user: User = Depends(require_auth)):
    """创建批量上传任务并自动开始后台处理 - 需要认证

    上传后立即返回任务ID，处理在后台进行
    通过 /status/{batch_id} 或 WebSocket 获取进度
    """
    if len(files) > 100:
        raise HTTPException(400, "单次最多上传100个文件")

    if len(files) == 0:
        raise HTTPException(400, "请选择要上传的文件")

    # 验证文件
    valid_extensions = {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    file_data = []
    skipped_files = []  # 记录跳过的文件

    for file in files:
        if not file.filename:
            continue

        # 检查文件扩展名
        ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in valid_extensions:
            skipped_files.append({"file": file.filename, "reason": f"不支持的文件格式"})
            continue

        content = await file.read()

        # 检查文件大小
        if len(content) > 10 * 1024 * 1024:
            skipped_files.append({"file": file.filename, "reason": "文件过大(最大10MB)"})
            continue

        # 检查空文件
        if len(content) == 0:
            skipped_files.append({"file": file.filename, "reason": "空文件"})
            continue

        file_data.append((file.filename, content))

    if not file_data:
        if skipped_files:
            reasons = "; ".join([f"{s['file']}: {s['reason']}" for s in skipped_files])
            raise HTTPException(400, f"没有有效的文件。跳过: {reasons}")
        raise HTTPException(400, "没有有效的文件")

    # 创建批量任务
    batch = await task_manager.create_batch([f[0] for f in file_data])

    # 存储文件内容到Redis
    for file_task in batch.files:
        # 找到对应的文件内容
        for fname, content in file_data:
            if fname == file_task.file_name:
                await task_manager.store_file_content(batch.batch_id, file_task.file_id, content)
                break

    # 将任务加入队列（后台Worker会自动处理）
    await task_manager.enqueue_batch(batch.batch_id)

    message = f"已创建批量任务，共 {batch.total_files} 个文件，正在后台处理"
    if skipped_files:
        message += f"（跳过 {len(skipped_files)} 个无效文件）"

    return {
        "batch_id": batch.batch_id,
        "total_files": batch.total_files,
        "status": batch.status.value,
        "files": [{"file_id": f.file_id, "file_name": f.file_name} for f in batch.files],
        "skipped": skipped_files,
        "message": message
    }


@router.get("/list")
async def list_batch_tasks():
    """获取所有批量任务列表"""
    batches = await task_manager.get_all_batches()

    return {
        "total": len(batches),
        "batches": [
            {
                "batch_id": b.batch_id,
                "status": b.status.value,
                "total": b.total_files,
                "completed": b.completed,
                "failed": b.failed,
                "progress": b.progress,
                "created_at": b.created_at.isoformat(),
                "updated_at": b.updated_at.isoformat()
            }
            for b in batches
        ]
    }


@router.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """获取批量任务详细状态"""
    batch = await task_manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "批量任务不存在")

    return {
        "batch_id": batch.batch_id,
        "status": batch.status.value,
        "total": batch.total_files,
        "completed": batch.completed,
        "failed": batch.failed,
        "progress": batch.progress,
        "processing": batch.processing_count,
        "files": [
            {
                "file_id": f.file_id,
                "file_name": f.file_name,
                "status": f.status.value,
                "status_detail": f.status_detail,  # 详细状态文字
                "progress": f.progress,
                "error": f.error,
                "result": f.result,
                "llm_output": f.llm_output,
                "retry_count": f.retry_count,
                "updated_at": f.updated_at.isoformat()
            }
            for f in batch.files
        ],
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat()
    }


@router.post("/retry/{batch_id}")
async def retry_failed_files(batch_id: str, file_id: str = None):
    """重试失败的文件

    如果指定file_id则重试单个文件，否则重试所有失败文件
    重试的文件会重新进入队列由后台Worker处理
    """
    batch = await task_manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "批量任务不存在")

    if file_id:
        # 检查文件内容是否还存在
        content = await task_manager.get_file_content(batch_id, file_id)
        if not content:
            raise HTTPException(400, "文件内容已过期，请重新上传")

        success = await task_manager.retry_file(batch_id, file_id)
        if not success:
            raise HTTPException(400, "文件不存在或已达到最大重试次数")

        # 重新入队
        await task_manager.enqueue_batch(batch_id)
        return {"message": "已将文件标记为重试", "file_id": file_id}
    else:
        count = await task_manager.retry_all_failed(batch_id)
        if count == 0:
            raise HTTPException(400, "没有可重试的文件")
        return {"message": f"已将 {count} 个文件标记为重试", "retry_count": count}


@router.delete("/{batch_id}")
async def delete_batch(batch_id: str, user: User = Depends(require_auth)):
    """删除批量任务 - 需要认证"""
    success = await task_manager.delete_batch(batch_id)
    if not success:
        raise HTTPException(404, "批量任务不存在")

    return {"status": "deleted", "batch_id": batch_id}


# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, batch_id: str):
        await websocket.accept()
        if batch_id not in self.active_connections:
            self.active_connections[batch_id] = []
        self.active_connections[batch_id].append(websocket)

    def disconnect(self, websocket: WebSocket, batch_id: str):
        if batch_id in self.active_connections:
            if websocket in self.active_connections[batch_id]:
                self.active_connections[batch_id].remove(websocket)
            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]

    async def broadcast(self, batch_id: str, message: dict):
        if batch_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[batch_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            # 清理断开的连接
            for conn in dead_connections:
                self.disconnect(conn, batch_id)


ws_manager = ConnectionManager()


@router.websocket("/ws/{batch_id}")
async def websocket_endpoint(websocket: WebSocket, batch_id: str):
    """WebSocket实时推送批量任务进度

    连接后会每隔1秒推送最新状态，直到任务完成
    """
    await ws_manager.connect(websocket, batch_id)

    try:
        # 发送初始状态
        batch = await task_manager.get_batch(batch_id)
        if not batch:
            await websocket.send_json({"error": "批量任务不存在"})
            await websocket.close()
            return

        await websocket.send_json({
            "type": "connected",
            "batch_id": batch_id,
            "status": batch.status.value
        })

        # 持续推送更新
        last_update = None
        while True:
            try:
                batch = await task_manager.get_batch(batch_id)
                if not batch:
                    await websocket.send_json({"type": "deleted"})
                    break

                # 构建更新消息
                update = {
                    "type": "update",
                    "batch_id": batch.batch_id,
                    "status": batch.status.value,
                    "total": batch.total_files,
                    "completed": batch.completed,
                    "failed": batch.failed,
                    "progress": batch.progress,
                    "processing": batch.processing_count,
                    "files": [
                        {
                            "file_id": f.file_id,
                            "file_name": f.file_name,
                            "status": f.status.value,
                            "status_detail": f.status_detail,  # 详细状态文字
                            "progress": f.progress,
                            "error": f.error,
                            "result": f.result,
                            "llm_output": f.llm_output[-500:] if f.llm_output else "",  # 只发送最后500字符
                            "retry_count": f.retry_count,
                            "updated_at": f.updated_at.isoformat()
                        }
                        for f in batch.files
                    ],
                    "updated_at": batch.updated_at.isoformat()
                }

                # 只在有变化时发送
                current_hash = f"{batch.status}{batch.completed}{batch.failed}{batch.updated_at}"
                if current_hash != last_update:
                    await websocket.send_json(update)
                    last_update = current_hash

                # 任务完成后发送完成消息
                if batch.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                    await websocket.send_json({
                        "type": "completed",
                        "status": batch.status.value,
                        "success": batch.completed,
                        "failed": batch.failed
                    })
                    # 完成后继续保持连接一段时间，以便客户端获取最终状态
                    await asyncio.sleep(5)
                    break

                # 等待1秒后再次检查
                await asyncio.sleep(1)

            except WebSocketDisconnect:
                break
            except asyncio.CancelledError:
                break

    finally:
        ws_manager.disconnect(websocket, batch_id)
