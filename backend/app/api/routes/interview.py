from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from app.services.interview_service import InterviewService
from app.agents.question_generator import question_generator
from app.models.interview import (
    InterviewSession,
    InterviewStatus,
    WrittenTest,
    VoiceInterview,
    Evaluation,
    Question,
    QuestionType,
    Answer
)

router = APIRouter(prefix="/api/interview", tags=["面试管理"])

interview_service = InterviewService()


class CreateInterviewRequest(BaseModel):
    """创建面试请求"""
    resume_id: str
    jd_id: str


class UpdateStatusRequest(BaseModel):
    """更新状态请求"""
    status: InterviewStatus


class SaveWrittenTestRequest(BaseModel):
    """保存笔试结果请求"""
    written_test: WrittenTest


class SaveVoiceInterviewRequest(BaseModel):
    """保存语音面试请求"""
    voice_interview: VoiceInterview


class SaveEvaluationRequest(BaseModel):
    """保存评估报告请求"""
    evaluation: Evaluation


class CancelInterviewRequest(BaseModel):
    """取消面试请求"""
    reason: str = ""


class GenerateQuestionsRequest(BaseModel):
    """生成笔试题目请求"""
    resume_id: str
    jd_id: str
    count: int = 5


@router.post("/create")
async def create_interview(request: CreateInterviewRequest) -> dict:
    """创建面试邀请

    Args:
        request: 包含 resume_id 和 jd_id 的请求体

    Returns:
        创建的面试会话信息，包含唯一的 token
    """
    try:
        session = interview_service.create_session(
            resume_id=request.resume_id,
            jd_id=request.jd_id
        )
        return {
            "status": "success",
            "data": session.model_dump(mode="json")
        }
    except Exception as e:
        raise HTTPException(500, f"创建面试失败: {str(e)}")


@router.get("/list")
async def list_interviews(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[InterviewStatus] = Query(None, description="按状态筛选")
) -> dict:
    """获取面试列表

    Args:
        page: 页码
        size: 每页数量
        status: 状态筛选（可选）

    Returns:
        分页的面试列表，包含候选人姓名和岗位名称
    """
    from app.services.jd_service import JDService
    from app.services.resume_parser import ResumeParser

    try:
        result = interview_service.list_sessions(
            page=page,
            size=size,
            status_filter=status
        )

        # Load resume and JD services for name lookup
        jd_service = JDService()
        resume_parser = ResumeParser()

        # Cache for resume and JD lookups
        resume_cache: dict = {}
        jd_cache: dict = {}

        enriched_data = []
        for session in result["data"]:
            data = session.model_dump(mode="json")

            # Get candidate name from resume
            if session.resume_id:
                if session.resume_id not in resume_cache:
                    resume = resume_parser.get_resume(session.resume_id)
                    if resume and hasattr(resume, 'basic_info') and resume.basic_info:
                        resume_cache[session.resume_id] = resume.basic_info.name or "未知"
                    else:
                        resume_cache[session.resume_id] = "未知"
                data["candidate_name"] = resume_cache[session.resume_id]

            # Get JD title
            if session.jd_id:
                if session.jd_id not in jd_cache:
                    jd = jd_service.get(session.jd_id)
                    jd_cache[session.jd_id] = jd.title if jd else "未知岗位"
                data["jd_title"] = jd_cache[session.jd_id]

            enriched_data.append(data)

        return {
            "status": "success",
            "data": enriched_data,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"]
        }
    except Exception as e:
        raise HTTPException(500, f"获取列表失败: {str(e)}")


@router.get("/{interview_id}")
async def get_interview(interview_id: str) -> dict:
    """获取面试详情

    Args:
        interview_id: 面试会话ID

    Returns:
        面试会话详细信息
    """
    session = interview_service.get_session(interview_id)
    if not session:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "data": session.model_dump(mode="json")
    }


@router.get("/by-token/{token}")
async def get_interview_by_token(token: str) -> dict:
    """根据token获取面试会话（候选人端使用）

    Args:
        token: 面试邀请令牌

    Returns:
        面试会话信息（包含候选人和职位详情）
    """
    from app.services.jd_service import JDService
    from app.services.resume_parser import ResumeParser

    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    # 加载简历和JD信息
    jd_service = JDService()
    resume_parser = ResumeParser()

    jd = jd_service.get(session.jd_id)
    resume = resume_parser.get_resume(session.resume_id)

    # 提取候选人姓名
    candidate_name = "候选人"
    if resume and hasattr(resume, 'basic_info') and resume.basic_info:
        candidate_name = resume.basic_info.name or "候选人"

    # 提取职位信息
    position = "未知职位"
    company = ""
    if jd:
        position = jd.title
        company = jd.department or ""

    # 构建简历摘要（用于AI面试官）
    resume_summary = ""
    if resume:
        parts = []
        if hasattr(resume, 'basic_info') and resume.basic_info:
            bi = resume.basic_info
            parts.append(f"姓名: {bi.name or '未知'}")
            if bi.phone:
                parts.append(f"电话: {bi.phone}")
            if bi.email:
                parts.append(f"邮箱: {bi.email}")
        if hasattr(resume, 'education') and resume.education:
            edu_str = ", ".join([f"{e.school}({e.degree}, {e.major})" for e in resume.education[:2]])
            parts.append(f"教育背景: {edu_str}")
        if hasattr(resume, 'work_experience') and resume.work_experience:
            work_str = ", ".join([f"{w.company}({w.position})" for w in resume.work_experience[:3]])
            parts.append(f"工作经历: {work_str}")
        if hasattr(resume, 'skills') and resume.skills:
            # Skills是一个对象，包含hard_skills和soft_skills
            all_skills = []
            if hasattr(resume.skills, 'hard_skills') and resume.skills.hard_skills:
                all_skills.extend(resume.skills.hard_skills[:8])
            if hasattr(resume.skills, 'soft_skills') and resume.skills.soft_skills:
                all_skills.extend(resume.skills.soft_skills[:4])
            if all_skills:
                skills_str = ", ".join(all_skills)
                parts.append(f"技能: {skills_str}")
        if hasattr(resume, 'projects') and resume.projects:
            proj_str = ", ".join([p.name for p in resume.projects[:3]])
            parts.append(f"项目经验: {proj_str}")
        resume_summary = "\n".join(parts)

    # 构建岗位信息（用于AI面试官）
    job_info = ""
    if jd:
        jd_parts = []
        jd_parts.append(f"职位名称: {jd.title}")
        if jd.department:
            jd_parts.append(f"部门: {jd.department}")
        if hasattr(jd, 'requirements') and jd.requirements:
            jd_parts.append(f"岗位要求: {jd.requirements}")
        if hasattr(jd, 'responsibilities') and jd.responsibilities:
            jd_parts.append(f"工作职责: {jd.responsibilities}")
        if hasattr(jd, 'skills') and jd.skills:
            skills = ", ".join(jd.skills) if isinstance(jd.skills, list) else jd.skills
            jd_parts.append(f"技能要求: {skills}")
        job_info = "\n".join(jd_parts)

    # 构建笔试摘要（用于AI面试官）
    written_test_summary = ""
    if session.written_test and session.written_test.questions:
        wt = session.written_test
        total = len(wt.questions)
        correct = sum(1 for a in wt.answers if a.is_correct)
        score = wt.score

        wt_parts = [f"笔试成绩: {score:.0f}分 ({correct}/{total}题正确)"]

        # 列出答错的题目（包含AI解析）
        wrong_questions = []
        for q in wt.questions:
            ans = next((a for a in wt.answers if a.question_id == q.id), None)
            if ans and not ans.is_correct:
                wrong_questions.append({
                    "content": q.content[:80] + "..." if len(q.content) > 80 else q.content,
                    "correct_answer": q.correct_answer,
                    "user_answer": ans.answer,
                    "ai_evaluation": getattr(ans, 'ai_evaluation', '') or ''
                })

        if wrong_questions:
            wt_parts.append(f"\n答错的题目 ({len(wrong_questions)}道):")
            for i, wq in enumerate(wrong_questions[:5], 1):  # 最多显示5道
                wt_parts.append(f"  {i}. {wq['content']}")
                wt_parts.append(f"     正确答案: {wq['correct_answer']}, 候选人答案: {wq['user_answer']}")
                if wq['ai_evaluation']:
                    # 截取AI评估的前100个字符，让面试官了解错误原因
                    eval_text = wq['ai_evaluation'][:100] + "..." if len(wq['ai_evaluation']) > 100 else wq['ai_evaluation']
                    wt_parts.append(f"     AI分析: {eval_text}")

        written_test_summary = "\n".join(wt_parts)

    data = session.model_dump(mode="json")
    data["candidate_name"] = candidate_name
    data["position"] = position
    data["company"] = company
    data["resume_summary"] = resume_summary
    data["job_info"] = job_info
    data["written_test_summary"] = written_test_summary

    return {
        "status": "success",
        "data": data
    }


@router.get("/by-token/{token}/written/questions")
async def get_written_questions_by_token(token: str) -> dict:
    """根据token获取笔试题目（候选人端使用）

    Args:
        token: 面试邀请令牌

    Returns:
        生成的笔试题目列表
    """
    from app.services.jd_service import JDService
    from app.services.resume_parser import ResumeParser

    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    jd_service = JDService()
    resume_parser = ResumeParser()

    jd = jd_service.get(session.jd_id)
    resume = resume_parser.get_resume(session.resume_id)

    if not jd:
        raise HTTPException(404, "JD不存在")
    if not resume:
        raise HTTPException(404, "简历不存在")

    # 更新状态为笔试中
    interview_service.update_status(session.id, InterviewStatus.WRITTEN_TEST)

    # 从JD配置获取题目数量
    question_count = jd.interview_config.written_question_count if jd.interview_config else 5

    # 生成题目
    questions = await question_generator.generate_questions(
        jd=jd,
        resume=resume,
        count=question_count
    )

    return {
        "status": "success",
        "data": [q.model_dump(mode="json") for q in questions]
    }


@router.get("/by-token/{token}/written/questions/stream")
async def get_written_questions_stream(token: str):
    """流式生成笔试题目（SSE），逐字段实时推送

    Args:
        token: 面试邀请令牌

    Returns:
        SSE流式响应，题目内容逐字段实时推送
    """
    from app.services.jd_service import JDService
    from app.services.resume_parser import ResumeParser

    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    jd_service = JDService()
    resume_parser = ResumeParser()

    jd = jd_service.get(session.jd_id)
    resume = resume_parser.get_resume(session.resume_id)

    if not jd:
        raise HTTPException(404, "JD不存在")
    if not resume:
        raise HTTPException(404, "简历不存在")

    # 更新状态为笔试中
    interview_service.update_status(session.id, InterviewStatus.WRITTEN_TEST)

    # 从JD配置获取题目数量
    question_count = jd.interview_config.written_question_count if jd.interview_config else 5

    async def generate_stream():
        """SSE流式生成器 - 逐字段输出"""
        count = question_count
        yield f"data: {json.dumps({'type': 'start', 'total': count}, ensure_ascii=False)}\n\n"

        for i in range(count):
            # 确定题型：最后两道题分别为多选和判断，其余为单选
            if i == count - 2:
                question_type = "multiple"
            elif i == count - 1:
                question_type = "judgment"
            else:
                question_type = "single"

            # 发送题目开始信号
            yield f"data: {json.dumps({'type': 'question_start', 'index': i + 1, 'question_type': question_type}, ensure_ascii=False)}\n\n"

            try:
                # 流式生成这道题
                async for event in question_generator.generate_question_stream(
                    jd=jd,
                    resume=resume,
                    question_type=question_type,
                    index=i + 1,
                    total=count
                ):
                    event['index'] = i + 1
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'index': i + 1, 'message': str(e)}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'all_complete'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{interview_id}/start")
async def start_interview(interview_id: str) -> dict:
    """开始面试

    Args:
        interview_id: 面试会话ID

    Returns:
        更新后的状态
    """
    success = interview_service.update_status(
        interview_id,
        InterviewStatus.WRITTEN_TEST
    )

    if not success:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "message": "面试已开始"
    }


@router.put("/{interview_id}/status")
async def update_interview_status(
    interview_id: str,
    request: UpdateStatusRequest
) -> dict:
    """更新面试状态

    Args:
        interview_id: 面试会话ID
        request: 包含新状态的请求体

    Returns:
        更新结果
    """
    success = interview_service.update_status(interview_id, request.status)

    if not success:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "message": "状态已更新"
    }


class SubmitWrittenTestRequest(BaseModel):
    """提交笔试答案请求（候选人端）"""
    sessionId: str
    answers: list[dict]
    questions: list[dict] = []  # 题目信息（含正确答案）
    submittedAt: str


def _score_written_test(questions: list[dict], answers: list[dict]) -> tuple[list, float, int, int]:
    """评分笔试答案

    Returns:
        (scored_answers, score_percentage, correct_count, total_points)
    """
    from app.models.interview import Answer

    # 构建答案映射
    answer_map = {a["questionId"]: a["answer"] for a in answers}
    question_map = {q["id"]: q for q in questions}

    scored_answers = []
    total_points = 0
    earned_points = 0
    correct_count = 0

    for q in questions:
        q_id = q["id"]
        correct_answer = q.get("correctAnswer", "")
        user_answer = answer_map.get(q_id, "")
        points = q.get("points", 10)
        total_points += points

        # 判断正确性
        is_correct = False
        if user_answer and correct_answer:
            # 处理多选题（答案可能是列表或逗号分隔字符串）
            if isinstance(correct_answer, list):
                correct_set = set(correct_answer)
                if isinstance(user_answer, list):
                    user_set = set(user_answer)
                else:
                    user_set = set(user_answer.split(",")) if "," in str(user_answer) else {str(user_answer)}
                is_correct = correct_set == user_set
            else:
                # 单选题/判断题
                is_correct = str(user_answer).strip().upper() == str(correct_answer).strip().upper()

        if is_correct:
            earned_points += points
            correct_count += 1

        scored_answers.append(Answer(
            question_id=q_id,
            answer=user_answer,
            is_correct=is_correct
        ))

    # 计算得分百分比
    score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0

    return scored_answers, score_percentage, correct_count, total_points


@router.post("/{token}/written/submit")
async def submit_written_test_by_token(token: str, request: SubmitWrittenTestRequest) -> dict:
    """候选人提交笔试答案（使用token）

    Args:
        token: 面试邀请令牌
        request: 包含答案和题目的请求体

    Returns:
        提交结果（含评分）
    """
    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    from datetime import datetime

    try:
        submitted_time = datetime.fromisoformat(request.submittedAt.replace("Z", "+00:00"))
    except:
        submitted_time = datetime.now()

    # 评分笔试答案
    scored_answers, score, correct_count, total_points = _score_written_test(
        request.questions,
        request.answers
    )

    # 构建题目列表
    questions_list = []
    for q in request.questions:
        questions_list.append(Question(
            id=q["id"],
            type=QuestionType(q["type"]),
            content=q["content"],
            options=q["options"],
            correct_answer=q["correctAnswer"],
            points=q.get("points", 10)
        ))

    written_test = WrittenTest(
        questions=questions_list,
        answers=scored_answers,
        score=score,
        started_at=session.started_at or submitted_time,
        completed_at=submitted_time
    )

    success = interview_service.save_written_test(session.id, written_test)
    if not success:
        raise HTTPException(500, "保存笔试结果失败")

    # 更新状态为语音面试阶段
    interview_service.update_status(session.id, InterviewStatus.VOICE_INTERVIEW)

    return {
        "status": "success",
        "message": "笔试答案已提交",
        "score": score,
        "correct_count": correct_count,
        "total_questions": len(request.questions)
    }


@router.post("/{token}/written/submit/stream")
async def submit_written_test_stream(token: str, request: SubmitWrittenTestRequest):
    """流式提交笔试答案 - 逐题打分并AI评估错题

    Args:
        token: 面试邀请令牌
        request: 包含答案和题目的请求体

    Returns:
        SSE流式响应，逐题展示打分过程和错题评估
    """
    from app.services.llm_client import LLMClient
    from datetime import datetime

    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    try:
        submitted_time = datetime.fromisoformat(request.submittedAt.replace("Z", "+00:00"))
    except:
        submitted_time = datetime.now()

    async def evaluate_stream():
        """SSE流式评估生成器 - 逐题打分并立即评估错题"""
        import asyncio
        llm = LLMClient()

        # 构建答案映射
        answer_map = {a["questionId"]: a["answer"] for a in request.answers}
        questions = request.questions
        total = len(questions)

        # 发送开始信号
        yield f"data: {json.dumps({'type': 'start', 'total': total}, ensure_ascii=False)}\n\n"

        scored_answers = []
        correct_count = 0
        total_points = 0
        earned_points = 0
        wrong_count = 0

        # 逐题评分 + 即时AI评估
        for i, q in enumerate(questions):
            q_id = q["id"]
            correct_answer = q.get("correctAnswer", "")
            user_answer = answer_map.get(q_id, "")
            points = q.get("points", 10)
            total_points += points

            # 发送正在检查信号
            yield f"data: {json.dumps({'type': 'checking', 'index': i + 1, 'total': total, 'question_id': q_id}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(0.2)

            # 判断正确性
            is_correct = False
            if user_answer and correct_answer:
                if isinstance(correct_answer, list):
                    correct_set = set(correct_answer)
                    if isinstance(user_answer, list):
                        user_set = set(user_answer)
                    else:
                        user_set = set(user_answer.split(",")) if "," in str(user_answer) else {str(user_answer)}
                    is_correct = correct_set == user_set
                else:
                    is_correct = str(user_answer).strip().upper() == str(correct_answer).strip().upper()

            if is_correct:
                earned_points += points
                correct_count += 1

            # 发送单题结果
            result_data = {
                'type': 'question_result',
                'index': i + 1,
                'question_id': q_id,
                'is_correct': is_correct,
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'points': points,
                'earned': points if is_correct else 0
            }
            yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

            ai_evaluation = ''

            # 如果答错，立即进行AI评估（流式）
            if not is_correct:
                wrong_count += 1
                # 发送开始评估信号
                yield f"data: {json.dumps({'type': 'evaluating', 'index': i + 1, 'question_id': q_id}, ensure_ascii=False)}\n\n"

                # 构建评估提示
                system_prompt = "你是技术面试评估专家，用Markdown格式简洁分析错题，80字以内。"
                prompt = f"""分析这道错题：

**题目**：{q['content']}
**选项**：{', '.join(q.get('options', [])) if q.get('options') else '无'}
**用户答案**：{user_answer}
**正确答案**：{correct_answer}

请简要说明：1）正确答案为什么对 2）用户可能的理解偏差"""

                try:
                    eval_text = ""
                    async for chunk in llm.chat_stream(prompt, system_prompt):
                        eval_text += chunk
                        # 立即发送每个chunk
                        yield f"data: {json.dumps({'type': 'evaluation_chunk', 'index': i + 1, 'question_id': q_id, 'chunk': chunk}, ensure_ascii=False)}\n\n"

                    ai_evaluation = eval_text
                    # 发送单题评估完成
                    yield f"data: {json.dumps({'type': 'evaluation_done', 'index': i + 1, 'question_id': q_id, 'evaluation': eval_text}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    print(f"[WrittenTest] AI evaluation error: {e}")
                    yield f"data: {json.dumps({'type': 'evaluation_error', 'index': i + 1, 'question_id': q_id, 'error': str(e)}, ensure_ascii=False)}\n\n"

            scored_answers.append({
                'question_id': q_id,
                'answer': user_answer,
                'is_correct': is_correct,
                'ai_evaluation': ai_evaluation
            })

        # 计算最终得分
        score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0

        # 保存笔试结果
        questions_list = []
        answers_list = []

        for q in questions:
            questions_list.append(Question(
                id=q["id"],
                type=QuestionType(q["type"]),
                content=q["content"],
                options=q["options"],
                correct_answer=q["correctAnswer"],
                points=q.get("points", 10)
            ))

        for sa in scored_answers:
            answers_list.append(Answer(
                question_id=sa['question_id'],
                answer=sa['answer'],
                is_correct=sa['is_correct'],
                ai_evaluation=sa.get('ai_evaluation', '')
            ))

        written_test = WrittenTest(
            questions=questions_list,
            answers=answers_list,
            score=score_percentage,
            started_at=session.started_at or submitted_time,
            completed_at=submitted_time
        )

        interview_service.save_written_test(session.id, written_test)
        interview_service.update_status(session.id, InterviewStatus.VOICE_INTERVIEW)

        # 发送全部完成信号
        yield f"data: {json.dumps({'type': 'all_complete', 'score': score_percentage, 'correct_count': correct_count, 'total': total, 'wrong_count': wrong_count}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        evaluate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{interview_id}/written-test")
async def save_written_test(
    interview_id: str,
    request: SaveWrittenTestRequest
) -> dict:
    """保存笔试结果

    Args:
        interview_id: 面试会话ID
        request: 笔试结果数据

    Returns:
        保存结果
    """
    success = interview_service.save_written_test(
        interview_id,
        request.written_test
    )

    if not success:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "message": "笔试结果已保存"
    }


class VoiceMessageRequest(BaseModel):
    """语音消息请求"""
    message: str


@router.post("/{token}/voice/start")
async def start_voice_interview_by_token(token: str) -> dict:
    """开始语音面试（候选人端）

    Args:
        token: 面试邀请令牌

    Returns:
        语音面试会话信息
    """
    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    # 更新状态
    interview_service.update_status(session.id, InterviewStatus.VOICE_INTERVIEW)

    return {
        "status": "success",
        "data": {
            "sessionId": session.id,
            "status": "active",
            "messages": [],
            "startedAt": session.started_at.isoformat() if session.started_at else None
        }
    }


@router.post("/{token}/voice/message")
async def send_voice_message_by_token(token: str, request: VoiceMessageRequest) -> dict:
    """发送语音面试消息（候选人端）

    Args:
        token: 面试邀请令牌
        request: 包含消息内容的请求

    Returns:
        AI回复
    """
    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    # TODO: 接入AI面试官进行对话
    # 暂时返回模拟回复
    from datetime import datetime
    import uuid

    return {
        "status": "success",
        "data": {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": f"收到您的回答。请继续回答下一个问题：请介绍一下您在上一份工作中最有挑战性的项目经历。",
            "timestamp": datetime.now().isoformat()
        }
    }


@router.post("/{token}/voice/end")
async def end_voice_interview_by_token(token: str) -> dict:
    """结束语音面试（候选人端）

    Args:
        token: 面试邀请令牌

    Returns:
        结束确认
    """
    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    # 更新状态为已完成
    interview_service.update_status(session.id, InterviewStatus.COMPLETED)

    return {
        "status": "success",
        "message": "语音面试已结束"
    }


@router.get("/{token}/voice/history")
async def get_voice_history_by_token(token: str) -> dict:
    """获取语音面试历史记录（候选人端）

    Args:
        token: 面试邀请令牌

    Returns:
        历史消息列表
    """
    session = interview_service.get_by_token(token)
    if not session:
        raise HTTPException(404, "无效的面试令牌")

    messages = []
    if session.voice_interview and session.voice_interview.transcript:
        for msg in session.voice_interview.transcript:
            messages.append({
                "id": str(hash(msg.timestamp.isoformat())),
                "role": "assistant" if msg.role == "interviewer" else "user",
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })

    return {
        "status": "success",
        "data": messages
    }


@router.post("/{interview_id}/voice-interview")
async def save_voice_interview(
    interview_id: str,
    request: SaveVoiceInterviewRequest
) -> dict:
    """保存语音面试记录

    Args:
        interview_id: 面试会话ID
        request: 语音面试数据

    Returns:
        保存结果
    """
    success = interview_service.save_voice_interview(
        interview_id,
        request.voice_interview
    )

    if not success:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "message": "语音面试记录已保存"
    }


@router.get("/{interview_id}/evaluation")
async def get_evaluation(interview_id: str) -> dict:
    """获取评估报告

    Args:
        interview_id: 面试会话ID

    Returns:
        评估报告详情
    """
    session = interview_service.get_session(interview_id)
    if not session:
        raise HTTPException(404, "面试会话不存在")

    if not session.evaluation:
        raise HTTPException(404, "评估报告尚未生成")

    return {
        "status": "success",
        "data": session.evaluation.model_dump(mode="json")
    }


@router.post("/{interview_id}/evaluation")
async def save_evaluation(
    interview_id: str,
    request: SaveEvaluationRequest
) -> dict:
    """保存评估报告

    Args:
        interview_id: 面试会话ID
        request: 评估报告数据

    Returns:
        保存结果
    """
    success = interview_service.save_evaluation(
        interview_id,
        request.evaluation
    )

    if not success:
        raise HTTPException(404, "面试会话不存在")

    return {
        "status": "success",
        "message": "评估报告已保存"
    }


@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: str,
    permanent: bool = False,
    request: Optional[CancelInterviewRequest] = None
) -> dict:
    """删除或取消面试

    Args:
        interview_id: 面试会话ID
        permanent: 是否永久删除（默认为False，仅取消）
        request: 取消原因（可选，仅在取消时使用）

    Returns:
        操作结果
    """
    if permanent:
        # 永久删除面试数据
        success = interview_service.delete_session(interview_id)
        if not success:
            raise HTTPException(404, "面试会话不存在")
        return {
            "status": "success",
            "message": "面试已永久删除"
        }
    else:
        # 仅取消面试
        reason = request.reason if request else ""
        success = interview_service.cancel_session(interview_id, reason)
        if not success:
            raise HTTPException(404, "面试会话不存在")
        return {
            "status": "success",
            "message": "面试已取消"
        }


@router.post("/generate-questions")
async def generate_questions(request: GenerateQuestionsRequest) -> dict:
    """根据JD和简历生成笔试题目

    Args:
        request: 包含 resume_id, jd_id 和题目数量的请求体

    Returns:
        生成的题目列表
    """
    try:
        # 加载JD和简历数据
        from app.services.jd_service import JDService
        from app.services.resume_parser import ResumeParser

        jd_service = JDService()
        resume_parser = ResumeParser()

        jd = jd_service.get(request.jd_id)
        resume = resume_parser.get_resume(request.resume_id)

        if not jd:
            raise HTTPException(404, "JD不存在")
        if not resume:
            raise HTTPException(404, "简历不存在")

        # 生成题目
        questions = await question_generator.generate_questions(
            jd=jd,
            resume=resume,
            count=request.count
        )

        return {
            "status": "success",
            "data": [q.model_dump(mode="json") for q in questions]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"生成题目失败: {str(e)}")
