from fastapi import APIRouter, HTTPException, Query
from app.services.jd_service import JDService
from app.models.jd import JobDescription, JDCreateRequest, JDUpdateRequest
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/jd", tags=["岗位描述管理"])


class ScreeningRequest(BaseModel):
    min_score: int = 0  # 最低匹配分数过滤

jd_service = JDService()


@router.post("", response_model=JobDescription)
async def create_jd(request: JDCreateRequest):
    """创建岗位描述"""
    try:
        jd = jd_service.create(request)
        return jd
    except Exception as e:
        raise HTTPException(500, f"创建JD失败: {str(e)}")


@router.get("", response_model=dict)
async def list_jd(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（标题）")
):
    """获取岗位描述列表

    支持分页和按标题搜索
    """
    try:
        if keyword:
            result = jd_service.search_by_title(keyword, page, size)
        else:
            result = jd_service.list(page, size)

        return {
            "data": result["data"],
            "total": result["total"],
            "page": page,
            "size": size
        }
    except Exception as e:
        raise HTTPException(500, f"获取JD列表失败: {str(e)}")


@router.get("/{jd_id}", response_model=JobDescription)
async def get_jd(jd_id: str):
    """获取岗位描述详情"""
    jd = jd_service.get(jd_id)
    if not jd:
        raise HTTPException(404, "JD不存在")
    return jd


@router.put("/{jd_id}", response_model=JobDescription)
async def update_jd(jd_id: str, request: JDUpdateRequest):
    """更新岗位描述"""
    jd = jd_service.update(jd_id, request)
    if not jd:
        raise HTTPException(404, "JD不存在")
    return jd


@router.delete("/{jd_id}")
async def delete_jd(jd_id: str):
    """删除岗位描述"""
    success = jd_service.delete(jd_id)
    if not success:
        raise HTTPException(404, "JD不存在")
    return {"status": "deleted", "id": jd_id}


@router.get("/{jd_id}/resumes")
async def get_jd_resumes(
    jd_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    min_score: int = Query(0, ge=0, le=100, description="最低匹配分数")
):
    """获取推荐给该JD的简历列表（按匹配度排序）"""
    from app.services.es_client import ESClient
    from app.services.job_matcher import job_matcher, JobRequirement

    # 验证 JD 存在
    jd = jd_service.get(jd_id)
    if not jd:
        raise HTTPException(404, "JD不存在")

    es_client = ESClient()

    # 方法1：查询所有简历中 recommended_jds 包含该 jd_id 的
    # 方法2：实时计算所有简历与该JD的匹配度（更准确但更慢）
    # 这里用方法2确保准确性

    try:
        # 获取所有简历
        query = {
            "query": {"match_all": {}},
            "size": 1000,
            "_source": ["id", "basic_info", "skills", "education", "experience", "job_intention", "warnings", "created_at"]
        }
        result = es_client.search("resumes", query)

        job_req = JobRequirement(
            title=jd.title,
            description=jd.description,
            required_skills=jd.required_skills,
            preferred_skills=jd.preferred_skills,
        )

        matched_resumes = []
        for hit in result["hits"]["hits"]:
            source = hit["_source"]
            # 简化的匹配计算
            resume_skills = source.get("skills", {}).get("hard_skills", []) + source.get("skills", {}).get("soft_skills", [])
            resume_skills_lower = [s.lower() for s in resume_skills]

            # 计算技能匹配
            matched_skills = []
            for skill in jd.required_skills + jd.preferred_skills:
                if any(skill.lower() in rs or rs in skill.lower() for rs in resume_skills_lower):
                    matched_skills.append(skill)

            # 简单匹配分计算
            total_skills = len(jd.required_skills) + len(jd.preferred_skills)
            if total_skills > 0:
                match_score = int(len(matched_skills) / total_skills * 100)
            else:
                match_score = 50

            if match_score >= min_score:
                basic_info = source.get("basic_info", {})
                education = source.get("education", [])
                experience = source.get("experience", [])

                matched_resumes.append({
                    "resume_id": source.get("id"),
                    "name": basic_info.get("name", "未知"),
                    "phone": basic_info.get("phone", ""),
                    "email": basic_info.get("email", ""),
                    "match_score": match_score,
                    "matched_skills": matched_skills[:5],
                    "education": f"{education[0].get('school', '')} {education[0].get('degree', '')}" if education else "",
                    "latest_company": experience[0].get("company", "") if experience else "",
                    "latest_title": experience[0].get("title", "") if experience else "",
                    "created_at": source.get("created_at", "")
                })

        # 按匹配度排序
        matched_resumes.sort(key=lambda x: x["match_score"], reverse=True)

        # 分页
        total = len(matched_resumes)
        start = (page - 1) * size
        end = start + size
        paginated = matched_resumes[start:end]

        return {
            "jd_id": jd_id,
            "jd_title": jd.title,
            "total": total,
            "page": page,
            "size": size,
            "data": paginated
        }
    except Exception as e:
        raise HTTPException(500, f"获取推荐简历失败: {str(e)}")


@router.post("/{jd_id}/screen")
async def start_screening(jd_id: str, request: ScreeningRequest = None):
    """启动AI筛选任务

    创建后台任务，对所有简历进行AI匹配度分析
    支持增量分析（已分析过的简历会跳过）
    """
    from app.services.screening_task_manager import screening_task_manager
    from app.services.es_client import ESClient

    # 验证 JD 存在
    jd = jd_service.get(jd_id)
    if not jd:
        raise HTTPException(404, "JD不存在")

    # 检查是否已有进行中的任务
    existing_batch = await screening_task_manager.get_active_batch_for_jd(jd_id)
    if existing_batch:
        return {
            "batch_id": existing_batch.batch_id,
            "status": existing_batch.status.value,
            "message": "该JD已有进行中的筛选任务",
            "total": existing_batch.total_resumes,
            "completed": existing_batch.completed,
            "progress": existing_batch.progress
        }

    min_score = request.min_score if request else 0

    # 获取所有简历
    es_client = ESClient()
    query = {
        "query": {"match_all": {}},
        "size": 10000,  # 最多处理10000份简历
        "_source": ["id", "basic_info.name"]
    }
    result = es_client.search("resumes", query)

    resumes = []
    for hit in result["hits"]["hits"]:
        source = hit["_source"]
        resumes.append({
            "id": source.get("id"),
            "name": source.get("basic_info", {}).get("name", "未知")
        })

    if not resumes:
        raise HTTPException(400, "没有简历可供筛选")

    # 创建筛选任务
    batch = await screening_task_manager.create_batch(
        jd_id=jd_id,
        jd_title=jd.title,
        resumes=resumes,
        min_score=min_score
    )

    # 如果所有简历都已有分数，直接返回完成
    if batch.skipped == batch.total_resumes:
        return {
            "batch_id": batch.batch_id,
            "status": "success",
            "message": f"所有 {batch.total_resumes} 份简历已有分析结果",
            "total": batch.total_resumes,
            "completed": batch.completed,
            "skipped": batch.skipped,
            "progress": 100
        }

    # 将任务加入队列
    await screening_task_manager.enqueue_batch(batch.batch_id)

    return {
        "batch_id": batch.batch_id,
        "status": batch.status.value,
        "message": f"已创建筛选任务，共 {batch.total_resumes} 份简历，其中 {batch.skipped} 份已有分析结果",
        "total": batch.total_resumes,
        "completed": batch.completed,
        "skipped": batch.skipped,
        "progress": batch.progress
    }


@router.get("/{jd_id}/screen/status")
async def get_screening_status(jd_id: str, batch_id: str = None):
    """获取AI筛选任务状态

    如果不指定batch_id，返回最近的活跃任务
    """
    from app.services.screening_task_manager import screening_task_manager

    # 验证 JD 存在
    jd = jd_service.get(jd_id)
    if not jd:
        raise HTTPException(404, "JD不存在")

    if batch_id:
        batch = await screening_task_manager.get_batch(batch_id)
    else:
        batch = await screening_task_manager.get_active_batch_for_jd(jd_id)

    if not batch:
        # 没有活跃任务，返回已完成的匹配结果统计
        matches = await screening_task_manager.get_jd_all_matches(jd_id)
        return {
            "jd_id": jd_id,
            "status": "idle",
            "message": "无进行中的筛选任务",
            "analyzed_count": len(matches),
            "has_results": len(matches) > 0
        }

    return {
        "batch_id": batch.batch_id,
        "jd_id": batch.jd_id,
        "jd_title": batch.jd_title,
        "status": batch.status.value,
        "total": batch.total_resumes,
        "completed": batch.completed,
        "failed": batch.failed,
        "skipped": batch.skipped,
        "processing": batch.processing_count,
        "progress": batch.progress,
        "resumes": [
            {
                "resume_id": r.resume_id,
                "resume_name": r.resume_name,
                "status": r.status.value,
                "status_detail": r.status_detail,
                "progress": r.progress,
                "match_score": r.match_score,
                "skill_score": r.skill_score,
                "experience_score": r.experience_score,
                "education_score": r.education_score,
                "matched_skills": r.matched_skills[:5] if r.matched_skills else [],
                "error": r.error,
                "updated_at": r.updated_at.isoformat()
            }
            for r in batch.resumes
        ],
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat()
    }


@router.get("/{jd_id}/screen/results")
async def get_screening_results(
    jd_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    min_score: int = Query(0, ge=0, le=100)
):
    """获取AI筛选结果（按匹配度排序）

    返回已保存的所有匹配分析结果
    """
    from app.services.screening_task_manager import screening_task_manager
    from app.services.es_client import ESClient

    # 验证 JD 存在
    jd = jd_service.get(jd_id)
    if not jd:
        raise HTTPException(404, "JD不存在")

    # 获取所有匹配结果
    matches = await screening_task_manager.get_jd_all_matches(jd_id, min_score)

    # 获取简历详细信息
    es_client = ESClient()
    results = []
    for match in matches:
        try:
            resume = es_client.get_document("resumes", match["resume_id"])
            source = resume["_source"]
            basic_info = source.get("basic_info", {})
            education = source.get("education", [])
            experience = source.get("experience", [])

            results.append({
                "resume_id": match["resume_id"],
                "name": basic_info.get("name", match.get("resume_name", "未知")),
                "phone": basic_info.get("phone", ""),
                "email": basic_info.get("email", ""),
                "match_score": match.get("match_score", 0),
                "skill_score": match.get("skill_score", 0),
                "experience_score": match.get("experience_score", 0),
                "education_score": match.get("education_score", 0),
                "matched_skills": match.get("matched_skills", [])[:5],
                "missing_skills": match.get("missing_skills", [])[:3],
                "highlights": match.get("highlights", [])[:3],
                "concerns": match.get("concerns", [])[:3],
                "education": f"{education[0].get('school', '')} {education[0].get('degree', '')}" if education else "",
                "latest_company": experience[0].get("company", "") if experience else "",
                "latest_title": experience[0].get("title", "") if experience else "",
                "analyzed_at": match.get("created_at", "")
            })
        except Exception:
            # 简历可能已被删除
            continue

    # 分页
    total = len(results)
    start = (page - 1) * size
    end = start + size
    paginated = results[start:end]

    return {
        "jd_id": jd_id,
        "jd_title": jd.title,
        "total": total,
        "page": page,
        "size": size,
        "data": paginated
    }
