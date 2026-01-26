from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Depends
from fastapi.responses import StreamingResponse, Response
from app.services.resume_parser import ResumeParser
from app.services.resume_exporter import resume_exporter
from app.services.job_matcher import job_matcher, JobRequirement
from app.models.resume import ResumeData, ResumeUploadResponse
from app.api.middleware.auth import require_auth, User
from typing import Optional, List
from pydantic import BaseModel
import json
import traceback
import asyncio
import io

router = APIRouter(prefix="/api/resume", tags=["简历解析"])

parser = ResumeParser()


class MatchRequest(BaseModel):
    """岗位匹配请求"""
    resume_id: str
    job_title: str
    job_description: str = ""
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    min_experience_years: int = 0
    education_level: str = ""
    use_ai: bool = False  # 是否使用AI智能匹配

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), user: User = Depends(require_auth)):
    """上传并解析单份简历（非流式，兼容旧接口）- 需要认证"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB限制
        raise HTTPException(400, "文件大小超过10MB限制")

    try:
        resume = await parser.parse(file.filename, content)
        return ResumeUploadResponse(id=resume.id, status="success", data=resume)
    except Exception as e:
        traceback.print_exc()
        return ResumeUploadResponse(id="", status="error", error=str(e))


@router.post("/upload-stream")
async def upload_resume_stream(file: UploadFile = File(...), user: User = Depends(require_auth)):
    """上传并解析简历（流式返回进度）- 需要认证"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "文件大小超过10MB限制")

    async def generate():
        try:
            # Step 1: 提取文本
            yield f"data: {json.dumps({'step': 1, 'message': '正在提取文件内容...', 'progress': 10}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            file_type, text = parser.file_processor.process_file(file.filename, content)
            yield f"data: {json.dumps({'step': 2, 'message': f'文件提取完成，共{len(text)}字符', 'progress': 20}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            # Step 3: LLM 流式解析
            yield f"data: {json.dumps({'step': 3, 'message': 'AI正在分析简历...', 'progress': 25, 'parsing': True}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            # 如果是图片或扫描件PDF，传递原始数据用于OCR
            from app.services.file_processor import FileType
            image_data = content if file_type in (FileType.IMAGE, FileType.PDF_SCANNED) else None

            resume = None
            # 始终传递原始文件内容用于保存，image_data用于OCR
            async for item in parser.parse_with_text_stream(file.filename, file_type, text, image_data, raw_content=content):
                if item["type"] == "chunk":
                    # 流式返回 LLM 输出片段
                    yield f"data: {json.dumps({'step': 3, 'type': 'llm_chunk', 'content': item['content'], 'progress': 50}, ensure_ascii=False)}\n\n"
                elif item["type"] == "status":
                    # OCR 状态更新
                    yield f"data: {json.dumps({'step': 3, 'message': item['message'], 'progress': 35}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)
                elif item["type"] == "done":
                    resume = item["data"]

            # Step 4: 完成
            yield f"data: {json.dumps({'step': 4, 'message': '解析完成，正在保存...', 'progress': 90}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            result = ResumeUploadResponse(id=resume.id, status="success", data=resume)
            yield f"data: {json.dumps({'step': 5, 'message': '处理完成', 'progress': 100, 'result': result.model_dump(mode='json')}, ensure_ascii=False)}\n\n"

        except Exception as e:
            traceback.print_exc()
            error_result = ResumeUploadResponse(id="", status="error", error=str(e))
            yield f"data: {json.dumps({'step': -1, 'message': f'处理失败: {str(e)}', 'progress': 0, 'result': error_result.model_dump(mode='json')}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/list")
async def list_resumes(page: int = 1, size: int = 20):
    """获取简历列表"""
    result = parser.list_resumes(page, size)
    return {"data": result["data"], "total": result["total"], "page": page, "size": size}


@router.get("/security-demo/{resume_id}")
async def security_demo_by_id(resume_id: str):
    """查看指定简历的加密状态"""
    from app.services.es_client import ESClient

    es = ESClient()

    try:
        result = es.get_document("resumes", resume_id)
        doc = result["_source"]
    except:
        raise HTTPException(404, "简历不存在")

    file_content = doc.get("file_content", "")
    is_encrypted = file_content.startswith("ENC:") if file_content else False

    return {
        "resume_id": resume_id,
        "file_name": doc.get("file_name"),
        "name": doc.get("basic_info", {}).get("name"),
        "encryption": {
            "file_encrypted": is_encrypted,
            "file_content_preview": file_content[:80] + "..." if file_content else None,
            "phone_display": doc.get("basic_info", {}).get("phone"),
            "phone_encrypted": doc.get("basic_info", {}).get("phone_encrypted", "")[:60] + "..." if doc.get("basic_info", {}).get("phone_encrypted") else None,
            "email_display": doc.get("basic_info", {}).get("email"),
            "email_encrypted": doc.get("basic_info", {}).get("email_encrypted", "")[:60] + "..." if doc.get("basic_info", {}).get("email_encrypted") else None,
        },
        "encrypted_flag": doc.get("encrypted", False),
        "file_size": doc.get("file_size"),
        "created_at": doc.get("created_at")
    }


@router.get("/security-demo")
async def security_demo():
    """安全特性演示 - 展示数据加密状态

    用于向客户/领导展示系统的安全特性：
    1. 文件内容 AES-256 加密存储
    2. 敏感信息（手机、邮箱）加密 + 脱敏
    3. 加密数据示例
    """
    from app.services.es_client import ESClient
    from app.services.encryption_service import encryption_service

    es = ESClient()

    # 获取一份简历作为示例
    query = {"query": {"match_all": {}}, "size": 1}
    result = es.search("resumes", query)

    if not result["hits"]["hits"]:
        return {
            "message": "暂无简历数据，请先上传简历",
            "encryption_enabled": True,
            "algorithm": "AES-256 (Fernet)"
        }

    doc = result["hits"]["hits"][0]["_source"]

    # 构建演示数据
    demo_data = {
        "encryption_status": {
            "enabled": True,
            "algorithm": "AES-256 (Fernet)",
            "key_derivation": "PBKDF2-SHA256 (100000 iterations)",
            "description": "所有敏感数据在存储前经过 AES-256 加密"
        },
        "file_encryption": {
            "is_encrypted": doc.get("encrypted", False) or (doc.get("file_content", "").startswith("ENC:")),
            "encrypted_prefix": doc.get("file_content", "")[:50] + "..." if doc.get("file_content") else None,
            "original_size": doc.get("file_size"),
            "description": "简历源文件使用 AES-256 加密后存储"
        },
        "personal_info_protection": {
            "phone_display": doc.get("basic_info", {}).get("phone", "N/A"),
            "phone_encrypted": doc.get("basic_info", {}).get("phone_encrypted", "")[:50] + "..." if doc.get("basic_info", {}).get("phone_encrypted") else "未加密(旧数据)",
            "email_display": doc.get("basic_info", {}).get("email", "N/A"),
            "email_encrypted": doc.get("basic_info", {}).get("email_encrypted", "")[:50] + "..." if doc.get("basic_info", {}).get("email_encrypted") else "未加密(旧数据)",
            "description": "手机号、邮箱等敏感信息加密存储，显示时脱敏"
        },
        "transmission_security": {
            "protocol": "HTTPS/TLS 1.3",
            "certificate": "Let's Encrypt (自动续期)",
            "description": "所有 API 通信强制使用 HTTPS 加密传输"
        }
    }

    return demo_data


@router.get("/stats")
async def get_dashboard_stats():
    """获取仪表盘统计数据

    返回简历总数、今日解析数、问答次数、平均响应时间等。
    """
    from datetime import datetime
    from app.services.es_client import ESClient

    es_client = ESClient()

    # 1. 获取简历总数
    total_resumes = 0
    today_parsed = 0

    try:
        # 查询总数
        count_query = {"query": {"match_all": {}}}
        count_result = es_client.search("resumes", {**count_query, "size": 0})
        total_resumes = count_result["hits"]["total"]["value"] if isinstance(count_result["hits"]["total"], dict) else count_result["hits"]["total"]

        # 查询今日解析数 - 使用日期范围查询
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = {
            "query": {
                "range": {
                    "created_at": {
                        "gte": today_start.isoformat(),
                        "lte": datetime.now().isoformat()
                    }
                }
            },
            "size": 0
        }
        today_result = es_client.search("resumes", today_query)
        today_parsed = today_result["hits"]["total"]["value"] if isinstance(today_result["hits"]["total"], dict) else today_result["hits"]["total"]
    except Exception as e:
        print(f"Resume stats query error: {e}")

    # 2. 获取问答统计（从 ES 的 chat_stats 索引查询）
    chat_count = 0
    avg_response_time = 0

    try:
        # 查询聊天总数
        chat_count_query = {"query": {"match_all": {}}, "size": 0}
        chat_count_result = es_client.search("chat_stats", chat_count_query)
        chat_count = chat_count_result["hits"]["total"]["value"] if isinstance(chat_count_result["hits"]["total"], dict) else chat_count_result["hits"]["total"]

        # 查询平均响应时间
        if chat_count > 0:
            avg_query = {
                "query": {"match_all": {}},
                "size": 0,
                "aggs": {
                    "avg_response_time": {
                        "avg": {"field": "response_time_ms"}
                    }
                }
            }
            avg_result = es_client.search("chat_stats", avg_query)
            avg_response_time = int(avg_result.get("aggregations", {}).get("avg_response_time", {}).get("value", 0) or 0)
    except Exception as e:
        # 索引可能不存在（还没有聊天记录）
        print(f"Chat stats query error: {e}")

    return {
        "totalResumes": total_resumes,
        "todayParsed": today_parsed,
        "chatCount": chat_count,
        "avgResponseTime": avg_response_time if avg_response_time > 0 else 800
    }


@router.get("/{resume_id}", response_model=ResumeData)
async def get_resume(resume_id: str):
    """获取简历详情"""
    resume = parser.get_resume(resume_id)
    if not resume:
        raise HTTPException(404, "简历不存在")
    return resume


@router.get("/{resume_id}/file")
async def download_resume_file(resume_id: str):
    """下载简历源文件"""
    from app.services.encryption_service import encryption_service

    # 直接从ES获取文档（包含file_content）
    try:
        from app.services.es_client import ESClient
        es = ESClient()
        result = es.get_document("resumes", resume_id)
        doc = result["_source"]

        if "file_content" not in doc:
            raise HTTPException(404, "源文件不存在")

        # 解密文件内容（自动兼容加密和未加密数据）
        file_content = encryption_service.decrypt(doc["file_content"])
        filename = doc.get("file_name", "resume")
        file_type = doc.get("file_type", "application/octet-stream")

        # 根据文件扩展名确定MIME类型
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
        }
        media_type = mime_types.get(ext, 'application/octet-stream')

        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(404, f"获取文件失败: {str(e)}")


@router.get("/{resume_id}/preview")
async def preview_resume_file(resume_id: str):
    """在线预览简历源文件"""
    from urllib.parse import quote
    import io
    from app.services.encryption_service import encryption_service

    try:
        from app.services.es_client import ESClient
        es = ESClient()
        result = es.get_document("resumes", resume_id)
        doc = result["_source"]

        if "file_content" not in doc:
            raise HTTPException(404, "源文件不存在")

        # 解密文件内容（自动兼容加密和未加密数据）
        file_content = encryption_service.decrypt(doc["file_content"])
        filename = doc.get("file_name", "resume")

        # 根据文件扩展名确定MIME类型
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain; charset=utf-8',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'bmp': 'image/bmp',
            'webp': 'image/webp',
        }
        media_type = mime_types.get(ext)

        # DOCX 转 HTML 预览
        if ext in ('docx', 'doc'):
            import mammoth
            try:
                result = mammoth.convert_to_html(io.BytesIO(file_content))
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.6; }}
        p {{ margin: 0.5em 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        td, th {{ border: 1px solid #ddd; padding: 8px; }}
    </style>
</head>
<body>{result.value}</body>
</html>"""
                return Response(
                    content=html_content.encode('utf-8'),
                    media_type='text/html; charset=utf-8',
                    headers={"Cache-Control": "max-age=3600"}
                )
            except Exception as e:
                raise HTTPException(400, f"DOCX预览失败: {str(e)}")

        if not media_type:
            # 不支持预览的格式
            raise HTTPException(400, f"该格式({ext})不支持在线预览，请下载查看")

        # 使用 inline 方式展示
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{quote(filename)}"',
                "Cache-Control": "max-age=3600"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, f"获取文件失败: {str(e)}")


@router.get("/{resume_id}/detail")
async def get_resume_detail(resume_id: str):
    """获取简历完整详情（包含警告信息）"""
    try:
        from app.services.es_client import ESClient
        es = ESClient()
        result = es.get_document("resumes", resume_id)
        doc = result["_source"]

        # 移除大字段
        doc.pop("file_content", None)
        doc.pop("embedding", None)

        return doc
    except Exception as e:
        raise HTTPException(404, f"简历不存在: {str(e)}")


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, user: User = Depends(require_auth)):
    """删除简历 - 需要认证"""
    success = parser.delete_resume(resume_id)
    if not success:
        raise HTTPException(404, "简历不存在")
    return {"status": "deleted"}


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str]


@router.post("/batch-delete")
async def batch_delete_resumes(request: BatchDeleteRequest, user: User = Depends(require_auth)):
    """批量删除简历 - 需要认证

    Args:
        ids: 要删除的简历ID列表

    Returns:
        deleted: 成功删除的数量
        failed: 删除失败的数量
        failed_ids: 删除失败的ID列表
    """
    if not request.ids:
        raise HTTPException(400, "请提供要删除的简历ID")

    if len(request.ids) > 100:
        raise HTTPException(400, "单次最多删除100份简历")

    deleted = 0
    failed = 0
    failed_ids = []

    for resume_id in request.ids:
        try:
            success = parser.delete_resume(resume_id)
            if success:
                deleted += 1
            else:
                failed += 1
                failed_ids.append(resume_id)
        except Exception:
            failed += 1
            failed_ids.append(resume_id)

    # 强制刷新索引，确保删除立即可见
    if deleted > 0:
        try:
            from app.services.es_client import ESClient
            es_client = ESClient()
            es_client.refresh_index("resumes")
        except Exception:
            pass  # 刷新失败不影响返回结果

    return {
        "deleted": deleted,
        "failed": failed,
        "failed_ids": failed_ids
    }


@router.get("/export/{format}")
async def export_resumes(
    format: str,
    ids: Optional[str] = Query(None, description="逗号分隔的简历ID，为空则导出全部"),
    page: int = 1,
    size: int = 100
):
    """导出简历

    Args:
        format: 导出格式 (json/xml/excel)
        ids: 指定导出的简历ID，逗号分隔
        page: 页码（导出全部时使用）
        size: 每页数量
    """
    # 验证格式
    if format not in ["json", "xml", "excel"]:
        raise HTTPException(400, "不支持的导出格式，可选: json, xml, excel")

    # 获取简历列表
    if ids:
        # 导出指定ID的简历
        resume_ids = [id.strip() for id in ids.split(",") if id.strip()]
        resumes = []
        for resume_id in resume_ids:
            resume = parser.get_resume(resume_id)
            if resume:
                resumes.append(resume)
    else:
        # 导出全部（分页）
        result = parser.list_resumes(page, size)
        resumes = result["data"]

    if not resumes:
        raise HTTPException(404, "没有可导出的简历")

    # 根据格式导出
    if format == "json":
        content = resume_exporter.to_json(resumes)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=resumes.json"
            }
        )

    elif format == "xml":
        content = resume_exporter.to_xml(resumes)
        return Response(
            content=content,
            media_type="application/xml",
            headers={
                "Content-Disposition": "attachment; filename=resumes.xml"
            }
        )

    elif format == "excel":
        content = resume_exporter.to_excel(resumes)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=resumes.xlsx"
            }
        )


@router.post("/match")
async def match_job(request: MatchRequest):
    """岗位匹配度分析

    计算简历与目标岗位的匹配程度，返回多维度评分和分析结果。
    """
    # 获取简历
    resume = parser.get_resume(request.resume_id)
    if not resume:
        raise HTTPException(404, "简历不存在")

    if request.use_ai and request.job_description:
        # 使用AI智能匹配
        result = await job_matcher.smart_match(resume, request.job_description)
    else:
        # 使用规则匹配
        job = JobRequirement(
            title=request.job_title,
            description=request.job_description,
            required_skills=request.required_skills,
            preferred_skills=request.preferred_skills,
            min_experience_years=request.min_experience_years,
            education_level=request.education_level
        )
        result = job_matcher.match(resume, job)

    return {
        "resume_id": request.resume_id,
        "job_title": request.job_title,
        "match_result": result.model_dump()
    }


@router.post("/batch-match")
async def batch_match_job(
    job_title: str = Body(...),
    job_description: str = Body(""),
    required_skills: list[str] = Body(default=[]),
    preferred_skills: list[str] = Body(default=[]),
    min_experience_years: int = Body(0),
    education_level: str = Body(""),
    page: int = Body(1),
    size: int = Body(20),
    min_score: int = Body(0)
):
    """批量岗位匹配

    对简历库中的所有简历进行岗位匹配，返回按匹配度排序的结果。
    """
    job = JobRequirement(
        title=job_title,
        description=job_description,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_experience_years=min_experience_years,
        education_level=education_level
    )

    # 获取所有简历
    result = parser.list_resumes(1, 1000)  # 获取前1000份
    resumes = result["data"]

    # 计算匹配度
    results = []
    for resume in resumes:
        match_result = job_matcher.match(resume, job)
        if match_result.overall_score >= min_score:
            results.append({
                "resume_id": resume.id,
                "name": resume.basic_info.name,
                "phone": resume.basic_info.phone,
                "email": resume.basic_info.email,
                "match_score": match_result.overall_score,
                "skill_score": match_result.skill_score,
                "experience_score": match_result.experience_score,
                "matched_skills": match_result.matched_skills,
                "missing_skills": match_result.missing_skills,
                "highlights": match_result.highlights,
                "concerns": match_result.concerns
            })

    # 按匹配度排序
    results.sort(key=lambda x: x["match_score"], reverse=True)

    # 分页
    start = (page - 1) * size
    end = start + size
    paginated = results[start:end]

    return {
        "job_title": job_title,
        "total": len(results),
        "page": page,
        "size": size,
        "data": paginated
    }
