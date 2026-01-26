"""笔试题目生成Agent - 根据JD和简历生成个性化客观题"""

from app.services.llm_client import LLMClient
from app.models.interview import Question, QuestionType
from app.models.jd import JobDescription
from app.models.resume import ResumeData
from typing import AsyncGenerator
import json
import uuid

class QuestionGeneratorAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate_questions_stream(
        self,
        jd: JobDescription,
        resume: ResumeData,
        count: int = 5
    ) -> AsyncGenerator[dict, None]:
        """流式生成笔试题目，逐题返回"""

        # 先发送开始信号
        yield {"type": "start", "total": count, "message": "开始生成笔试题目..."}

        for i in range(count):
            # 确定本题类型
            if i == count - 2:
                question_type = "multiple"
                type_hint = "多选题"
            elif i == count - 1:
                question_type = "judgment"
                type_hint = "判断题"
            else:
                question_type = "single"
                type_hint = "单选题"

            yield {"type": "generating", "index": i + 1, "message": f"正在生成第 {i + 1}/{count} 题 ({type_hint})..."}

            # 为每道题单独调用LLM
            question = await self._generate_single_question(
                jd=jd,
                resume=resume,
                question_type=question_type,
                index=i + 1,
                total=count
            )

            if question:
                yield {"type": "question", "index": i + 1, "data": question.model_dump(mode="json")}
            else:
                yield {"type": "error", "index": i + 1, "message": f"第 {i + 1} 题生成失败"}

        yield {"type": "complete", "message": "题目生成完成！"}

    async def generate_question_stream(
        self,
        jd: JobDescription,
        resume: ResumeData,
        question_type: str,
        index: int,
        total: int
    ) -> AsyncGenerator[dict, None]:
        """流式生成单道题目，逐字段返回"""

        type_map = {
            "single": "单选题(4个选项，只有1个正确答案)",
            "multiple": "多选题(4个选项，有2-3个正确答案)",
            "judgment": "判断题(选项固定为 A.正确 B.错误)"
        }

        system_prompt = """你是一位专业的技术面试官。请生成一道高质量的笔试题目。

## 输出格式（严格按此格式）
[CONTENT]
题目内容
[/CONTENT]
[OPTION_A]选项A内容[/OPTION_A]
[OPTION_B]选项B内容[/OPTION_B]
[OPTION_C]选项C内容[/OPTION_C]
[OPTION_D]选项D内容[/OPTION_D]
[ANSWER]正确答案[/ANSWER]
[POINTS]分值[/POINTS]

注意：判断题只需要OPTION_A和OPTION_B"""

        user_prompt = f"""请生成第 {index}/{total} 道笔试题，题型要求：{type_map[question_type]}

## 岗位信息
- 岗位：{jd.title}
- 技能要求：{', '.join(jd.required_skills[:5])}
- 难度：{jd.interview_config.difficulty}

## 候选人背景
- 技能：{', '.join((resume.skills.hard_skills + resume.skills.soft_skills)[:8])}

要求：题目考察实际工作能力，难度适中。严格按格式输出，不要添加额外说明。"""

        question_data = {
            "id": str(uuid.uuid4()),
            "type": question_type,
            "content": "",
            "options": [],
            "correct_answer": "",
            "points": 10
        }

        # 使用缓冲区处理流式数据
        buffer = ""
        current_field = None

        try:
            async for chunk in self.llm.chat_stream(user_prompt, system_prompt):
                buffer += chunk

                # 检查是否有完整的标签
                while True:
                    # 查找开始标签
                    start_match = None
                    for tag in ["CONTENT", "OPTION_A", "OPTION_B", "OPTION_C", "OPTION_D", "ANSWER", "POINTS"]:
                        open_tag = f"[{tag}]"
                        close_tag = f"[/{tag}]"

                        if open_tag in buffer:
                            start_idx = buffer.index(open_tag)

                            # 先输出开始标签之前的内容
                            if start_idx > 0 and current_field:
                                before_content = buffer[:start_idx]
                                if before_content.strip():
                                    yield {"type": "chunk", "field": current_field, "value": before_content}
                                    self._append_field(question_data, current_field, before_content)

                            buffer = buffer[start_idx + len(open_tag):]
                            current_field = tag
                            yield {"type": "field_start", "field": tag}

                            # 检查是否有结束标签
                            if close_tag in buffer:
                                end_idx = buffer.index(close_tag)
                                content = buffer[:end_idx]
                                if content:
                                    yield {"type": "chunk", "field": tag, "value": content}
                                    self._append_field(question_data, tag, content)
                                buffer = buffer[end_idx + len(close_tag):]
                                current_field = None
                            start_match = True
                            break

                    if not start_match:
                        # 没有找到新标签，检查是否有结束标签
                        if current_field:
                            close_tag = f"[/{current_field}]"
                            if close_tag in buffer:
                                end_idx = buffer.index(close_tag)
                                content = buffer[:end_idx]
                                if content:
                                    yield {"type": "chunk", "field": current_field, "value": content}
                                    self._append_field(question_data, current_field, content)
                                buffer = buffer[end_idx + len(close_tag):]
                                current_field = None
                            else:
                                # 输出部分内容（保留可能的标签前缀）
                                if len(buffer) > 20 and "[" not in buffer[-15:]:
                                    output = buffer[:-15]
                                    yield {"type": "chunk", "field": current_field, "value": output}
                                    self._append_field(question_data, current_field, output)
                                    buffer = buffer[-15:]
                        break

            # 处理剩余缓冲区
            if buffer.strip() and current_field:
                close_tag = f"[/{current_field}]"
                if close_tag in buffer:
                    end_idx = buffer.index(close_tag)
                    content = buffer[:end_idx]
                else:
                    content = buffer
                if content.strip():
                    self._append_field(question_data, current_field, content)

            # 构建最终数据
            yield {"type": "complete", "data": question_data}

        except Exception as e:
            print(f"Stream generate question {index} error: {e}")
            yield {"type": "error", "message": str(e)}

    def _append_field(self, question_data: dict, field: str, value: str):
        """追加字段值"""
        clean_value = value.strip()
        if not clean_value:
            return

        if field == "CONTENT":
            question_data["content"] += clean_value
        elif field == "ANSWER":
            if "," in clean_value:
                question_data["correct_answer"] = [a.strip() for a in clean_value.split(",")]
            else:
                question_data["correct_answer"] = clean_value
        elif field == "POINTS":
            try:
                question_data["points"] = int(clean_value)
            except:
                pass
        elif field.startswith("OPTION_"):
            letter = field.split("_")[1]
            idx = ord(letter) - ord("A")
            while len(question_data["options"]) <= idx:
                question_data["options"].append("")
            question_data["options"][idx] += clean_value

    def _save_field(self, question_data: dict, field: str, value: str):
        """保存字段值到question_data"""
        field_map = {
            "TYPE": "type",
            "CONTENT": "content",
            "ANSWER": "correct_answer",
            "POINTS": "points"
        }

        if field in field_map:
            if field == "POINTS":
                try:
                    question_data["points"] = int(value)
                except:
                    question_data["points"] = 10
            elif field == "ANSWER":
                # 处理多选答案
                if "," in value:
                    question_data["correct_answer"] = [a.strip() for a in value.split(",")]
                else:
                    question_data["correct_answer"] = value.strip()
            else:
                question_data[field_map[field]] = value
        elif field.startswith("OPTION_"):
            option_letter = field.split("_")[1]
            question_data["options"].append(f"{option_letter}. {value}")

    async def _generate_single_question(
        self,
        jd: JobDescription,
        resume: ResumeData,
        question_type: str,
        index: int,
        total: int
    ) -> Question | None:
        """生成单道题目（非流式，兼容旧接口）"""

        type_map = {
            "single": "单选题(4个选项，只有1个正确答案)",
            "multiple": "多选题(4个选项，有2-3个正确答案)",
            "judgment": "判断题(选项固定为 A.正确 B.错误)"
        }

        system_prompt = """你是一位专业的技术面试官。请生成一道高质量的笔试题目。

## 输出格式
直接返回JSON对象（不要markdown代码块）：
{
  "type": "single|multiple|judgment",
  "content": "题目内容",
  "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
  "correct_answer": "A" 或 ["A", "B"],
  "explanation": "答案解析",
  "points": 10
}"""

        user_prompt = f"""请生成第 {index}/{total} 道笔试题，题型要求：{type_map[question_type]}

## 岗位信息
- 岗位：{jd.title}
- 技能要求：{', '.join(jd.required_skills[:5])}
- 难度：{jd.interview_config.difficulty}
- 考察重点：{', '.join(jd.interview_config.focus_areas[:3]) or '综合能力'}

## 候选人背景
- 技能：{', '.join((resume.skills.hard_skills + resume.skills.soft_skills)[:8])}

要求：题目要考察实际工作能力，难度适中，与岗位相关。直接返回JSON，不要其他内容。"""

        try:
            response = await self.llm.chat_async(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )

            # 清理响应
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()

            data = json.loads(response)
            return Question(
                id=str(uuid.uuid4()),
                type=QuestionType(data["type"]),
                content=data["content"],
                options=data["options"],
                correct_answer=data["correct_answer"],
                explanation=data.get("explanation", ""),
                points=data.get("points", 10)
            )
        except Exception as e:
            print(f"Generate question {index} error: {e}")
            return None

    async def generate_questions(
        self,
        jd: JobDescription,
        resume: ResumeData,
        count: int = 5
    ) -> list[Question]:
        """根据JD和简历生成笔试题目"""

        system_prompt = """你是一位专业的技术面试官，负责为候选人生成笔试题目。

## 要求
1. 根据岗位要求和候选人简历生成针对性题目
2. 题目类型包括：单选题(single)、多选题(multiple)、判断题(judgment)
3. 难度要与岗位匹配
4. 题目要考察实际工作能力，不是死记硬背

## 输出格式
返回JSON数组，每个题目格式：
{
  "type": "single|multiple|judgment",
  "content": "题目内容",
  "options": ["A. xxx", "B. xxx", "C. xxx", "D. xxx"],
  "correct_answer": "A" 或 ["A", "B"] (多选),
  "explanation": "答案解析",
  "points": 10
}

注意：判断题的options固定为 ["A. 正确", "B. 错误"]
"""

        user_prompt = f"""请为以下候选人生成 {count} 道笔试题目：

## 岗位信息
- 岗位名称：{jd.title}
- 岗位描述：{jd.description}
- 必需技能：{', '.join(jd.required_skills)}
- 任职要求：{chr(10).join(jd.requirements)}
- 难度要求：{jd.interview_config.difficulty}
- 重点考察：{', '.join(jd.interview_config.focus_areas) or '综合能力'}

## 候选人简历
- 姓名：{resume.basic_info.name}
- 技能：{', '.join(resume.skills.hard_skills + resume.skills.soft_skills)}
- 工作经验：
{chr(10).join([f"  - {exp.company} {exp.title}: {exp.duties[:100]}..." for exp in resume.experience[:3]])}

请生成 {count} 道题目，包含至少1道多选题和1道判断题。直接返回JSON数组，不要其他内容。"""

        response = await self.llm.chat_async(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )

        # 解析返回的JSON
        try:
            questions_data = json.loads(response)
            questions = []
            for q in questions_data:
                questions.append(Question(
                    id=str(uuid.uuid4()),
                    type=QuestionType(q["type"]),
                    content=q["content"],
                    options=q["options"],
                    correct_answer=q["correct_answer"],
                    explanation=q.get("explanation", ""),
                    points=q.get("points", 10)
                ))
            return questions
        except Exception as e:
            raise ValueError(f"Failed to parse questions: {e}")

question_generator = QuestionGeneratorAgent()
