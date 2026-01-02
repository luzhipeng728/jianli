from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.resume_parser import ResumeParser
from app.models.resume import ResumeData, ResumeUploadResponse

router = APIRouter(prefix="/api/resume", tags=["简历解析"])

parser = ResumeParser()

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """上传并解析单份简历"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB限制
        raise HTTPException(400, "文件大小超过10MB限制")

    try:
        resume = await parser.parse(file.filename, content)
        return ResumeUploadResponse(id=resume.id, status="success", data=resume)
    except Exception as e:
        return ResumeUploadResponse(id="", status="error", error=str(e))

@router.get("/list")
async def list_resumes(page: int = 1, size: int = 20):
    """获取简历列表"""
    resumes = parser.list_resumes(page, size)
    return {"data": resumes, "page": page, "size": size}

@router.get("/{resume_id}", response_model=ResumeData)
async def get_resume(resume_id: str):
    """获取简历详情"""
    resume = parser.get_resume(resume_id)
    if not resume:
        raise HTTPException(404, "简历不存在")
    return resume

@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """删除简历"""
    success = parser.delete_resume(resume_id)
    if not success:
        raise HTTPException(404, "简历不存在")
    return {"status": "deleted"}
