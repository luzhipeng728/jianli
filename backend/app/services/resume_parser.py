import uuid
import json
from app.services.file_processor import FileProcessor, FileType
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.models.resume import ResumeData, BasicInfo, Education, Experience, Skills, JobIntention, Warning

RESUME_INDEX = "resumes"

EXTRACT_PROMPT = """请从以下简历文本中提取结构化信息，以JSON格式返回。

要求提取的字段：
1. basic_info: name(姓名), phone(电话), email(邮箱), age(年龄), gender(性别)
2. education: 数组，每项包含 school(学校), degree(学历), major(专业), start_date, end_date
3. experience: 数组，每项包含 company(公司), title(职位), start_date, end_date, duties(职责)
4. skills: hard_skills(硬技能数组), soft_skills(软技能数组)
5. job_intention: position(期望职位), salary_min, salary_max, location(期望地点)
6. warnings: 检测到的问题，如时间矛盾、可疑信息等

简历文本：
{text}

请仅返回JSON，不要添加任何解释。"""

class ResumeParser:
    def __init__(self):
        self.file_processor = FileProcessor()
        self.llm_client = LLMClient()
        self.es_client = ESClient()

    async def parse(self, filename: str, content: bytes) -> ResumeData:
        # 1. 提取文本
        file_type, text = self.file_processor.process_file(filename, content)

        # 2. 如果是图片，使用OCR
        if file_type == FileType.IMAGE:
            # 需要先上传图片获取URL，这里简化处理
            # 实际实现需要将图片上传到OSS或本地服务
            text = "图片OCR暂未实现"

        # 3. 使用LLM提取结构化信息
        prompt = EXTRACT_PROMPT.format(text=text[:8000])  # 限制长度
        result = await self.llm_client.chat(prompt)

        # 4. 解析JSON结果
        resume_data = self._parse_llm_result(result, filename, file_type.value, text)

        # 5. 存储到ES
        self._save_to_es(resume_data)

        return resume_data

    def _parse_llm_result(
        self, result: str, filename: str, file_type: str, raw_text: str
    ) -> ResumeData:
        try:
            # 提取JSON部分
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            data = json.loads(result)
        except json.JSONDecodeError:
            data = {}

        resume_id = str(uuid.uuid4())

        return ResumeData(
            id=resume_id,
            file_name=filename,
            file_type=file_type,
            raw_text=raw_text,
            basic_info=BasicInfo(**data.get("basic_info", {})),
            education=[Education(**e) for e in data.get("education", [])],
            experience=[Experience(**e) for e in data.get("experience", [])],
            skills=Skills(**data.get("skills", {})),
            job_intention=JobIntention(**data.get("job_intention", {})),
            warnings=[Warning(**w) for w in data.get("warnings", [])],
        )

    def _save_to_es(self, resume: ResumeData):
        self.es_client.index_document(
            RESUME_INDEX,
            resume.id,
            resume.model_dump(mode="json")
        )

    def get_resume(self, resume_id: str) -> ResumeData | None:
        try:
            result = self.es_client.get_document(RESUME_INDEX, resume_id)
            return ResumeData(**result["_source"])
        except Exception:
            return None

    def list_resumes(self, page: int = 1, size: int = 20) -> list[ResumeData]:
        query = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }
        result = self.es_client.search(RESUME_INDEX, query)
        return [ResumeData(**hit["_source"]) for hit in result["hits"]["hits"]]

    def delete_resume(self, resume_id: str) -> bool:
        try:
            self.es_client.delete_document(RESUME_INDEX, resume_id)
            return True
        except Exception:
            return False
