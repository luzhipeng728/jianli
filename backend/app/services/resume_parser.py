import uuid
import json
from app.services.file_processor import FileProcessor, FileType
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.services.university_service import university_service, UniversityVerification
from app.services.enhanced_school_verifier import verify_school_with_context
from app.models.resume import ResumeData, BasicInfo, Education, Experience, Skills, JobIntention, Warning, EducationWarning, RecommendedJD

RESUME_INDEX = "resumes"

EXTRACT_PROMPT = """你是一个专业的简历解析和风险检测助手。请仔细阅读以下简历文本，完成两项任务：
1. 提取所有结构化信息
2. 识别潜在的虚假信息和逻辑矛盾

**重要规则：**
1. 请完整提取所有工作经历，不要遗漏任何一段工作经验！
2. **所有输出内容必须使用中文**，如果简历是英文的，请翻译成中文后输出
3. 技能名称可以保留英文原名（如Python、Java），但描述性文字必须是中文
4. 风险警告(warnings)必须认真检测，不要遗漏任何可疑之处
5. **【重点】学历造假检测是最重要的任务，必须严格审查！**

## 要求提取的字段：

### 1. basic_info（基本信息）
   - name: 姓名
   - phone: 电话号码（验证格式是否合理）
   - email: 邮箱地址（验证格式是否合理）
   - age: 年龄（数字，如30）或根据出生年份计算
   - gender: 性别

### 2. education（教育经历）数组，包含所有教育经历
   - school: 学校名称
   - degree: 学历（如：本科、硕士、博士）
   - major: 专业
   - start_date: 开始时间（如：2015.09）
   - end_date: 结束时间（如：2019.06）

### 3. experience（工作经历）数组，**必须包含所有工作经历，按时间倒序排列**
   - company: 公司名称
   - title: 职位名称
   - start_date: 入职时间
   - end_date: 离职时间（在职则填"至今"）
   - duties: 工作职责和成就（完整描述，可以较长）

### 4. skills（技能）
   - hard_skills: 技术技能数组（如：Python, Java, 机器学习, 数据分析）
   - soft_skills: 软技能数组（如：团队协作, 项目管理, 沟通能力）

### 5. job_intention（求职意向）
   - position: 期望职位
   - salary_min: 最低期望薪资（数字，单位元）
   - salary_max: 最高期望薪资（数字，单位元）
   - location: 期望工作地点

### 6. education_warnings（学历造假风险）数组 - **请注意：学校真实验证将由系统自动完成**

系统会自动使用教育部官方数据验证学校是否正规，你只需检测以下逻辑问题：

**risk_level 风险等级：**
- high: 高风险（强烈建议核实）
- medium: 中风险（建议核实）
- low: 低风险（可关注）

**需要检测的学历造假类型（不包含学校真伪，系统会自动验证）：**

1. **diploma_mill** - 文凭工厂/买卖学历
   - 学习时间异常短（如1年完成本科、6个月完成硕士）
   - 在职期间全日制读书（时间明显冲突）
   - 短时间内获得多个学位

2. **degree_inflation** - 学历注水/夸大
   - 将培训证书描述为正规学历
   - 将结业证书说成毕业证书
   - 将专科说成本科

3. **timeline_fraud** - 时间线造假
   - 学历时间与年龄不符（如18岁硕士毕业）
   - 教育时间段重叠
   - 毕业时间在入学时间之前

4. **overseas_fake** - 海外学历可疑
   - 学习时间过短（如3个月海外硕士）
   - 学校名称表述模糊

5. **info_missing** - 关键信息缺失
   - 只写学校不写专业
   - 只写学历不写时间
   - 教育经历描述模糊

### 7. warnings（其他风险警告）数组

请检查以下非学历相关的问题（每个问题包含type和message字段）：

**时间相关问题：**
- time_overlap: 工作经历时间重叠（同时在两家公司工作）
- time_gap: 工作经历之间存在较大空档（超过6个月未说明）
- duration_mismatch: 任职时间与职级不匹配（如工作1年就当上总监）

**经历相关问题：**
- experience_exaggerated: 经历夸大（初级职位描述高管职责）
- skill_mismatch: 技能与工作经历不匹配（声称精通但工作中未体现）
- company_suspicious: 公司信息可疑（无法查证的公司名）
- responsibility_unrealistic: 职责描述不切实际

**信息缺失问题：**
- missing_contact: 缺少联系方式
- missing_experience: 缺少工作经历（有工作年限声明但无详细经历）

## 简历文本：
{text}

## 输出要求：
1. 请直接返回JSON格式，不要添加```json标记或任何解释文字
2. **所有字段值必须是中文**（技能名称除外）
3. 如果原文是英文，必须翻译成中文
4. **education_warnings 用于检测逻辑问题**（学校真伪由系统自动验证）：
   - risk_level: 风险等级（high/medium/low）
   - type: 问题类型（使用上述英文标识）
   - message: 具体问题描述（中文，详细说明发现的可疑之处）
5. 每个warning必须包含：
   - type: 问题类型（使用上述英文标识）
   - message: 具体问题描述（中文，详细说明发现的问题和可疑之处）
6. 如果学历信息完整且无可疑之处，education_warnings返回空数组[]"""

class ResumeParser:
    def __init__(self):
        self.file_processor = FileProcessor()
        self.llm_client = LLMClient()
        self.es_client = ESClient()

    async def parse(self, filename: str, content: bytes) -> ResumeData:
        # 1. 提取文本
        file_type, text = self.file_processor.process_file(filename, content)

        # 2. 如果是扫描件或图片，需要OCR
        if file_type in (FileType.IMAGE, FileType.PDF_SCANNED):
            if file_type == FileType.PDF_SCANNED:
                # 提取PDF页面为图片进行OCR
                images = self.file_processor.extract_images_from_pdf(content)
                ocr_texts = []
                for img_data in images[:5]:  # 最多处理5页
                    ocr_text = await self.llm_client.ocr(img_data, "page.png")
                    if ocr_text:
                        ocr_texts.append(ocr_text)
                text = "\n\n".join(ocr_texts) if ocr_texts else text
            else:
                # 图片直接OCR
                text = await self.llm_client.ocr(content, filename)

        return await self.parse_with_text(filename, file_type, text, content)

    async def parse_with_text(self, filename: str, file_type: FileType, text: str, raw_content: bytes = None) -> ResumeData:
        """使用已提取的文本解析简历（供流式接口使用）"""
        # 1. 如果是图片且没有文本，使用OCR
        if file_type == FileType.IMAGE and not text and raw_content:
            text = await self.llm_client.ocr(raw_content, filename)
            if not text:
                raise ValueError("OCR识别失败，无法提取文字内容")

        # 2. 检查提取的文本是否有效
        clean_text = text.strip() if text else ""
        if len(clean_text) < 20:
            raise ValueError(f"文件内容为空或无法识别有效文字（提取到{len(clean_text)}字符）")

        # 3. 使用LLM提取结构化信息（增加限制到20000字符）
        prompt = EXTRACT_PROMPT.format(text=text[:20000])
        result = await self.llm_client.chat(prompt)

        # 3. 解析JSON结果
        resume_data = await self._parse_llm_result(result, filename, file_type.value, text)

        # 4. 创建向量嵌入
        embedding_text = self._create_embedding_text(resume_data)
        embedding = await self.llm_client.get_embedding(embedding_text, text_type="document")

        # 5. 存储到ES（包含embedding）
        self._save_to_es(resume_data, embedding, raw_content)

        return resume_data

    async def parse_with_text_stream(self, filename: str, file_type: FileType, text: str, image_data: bytes = None, raw_content: bytes = None):
        """流式解析简历 - 边解析边返回进度"""
        from typing import AsyncGenerator

        # 保存原始文件内容用于后续存储
        file_content = raw_content or image_data

        # 1. 如果是图片或扫描件PDF，使用OCR
        if file_type == FileType.IMAGE and image_data:
            yield {"type": "status", "message": "正在进行OCR识别..."}
            text = await self.llm_client.ocr(image_data, filename)
            if not text:
                raise ValueError("OCR识别失败，无法提取文字内容")
            yield {"type": "status", "message": f"OCR完成，提取到{len(text)}字符"}

        elif file_type == FileType.PDF_SCANNED and image_data:
            yield {"type": "status", "message": "检测到扫描件PDF，正在进行OCR识别..."}
            # 提取PDF页面为图片
            images = self.file_processor.extract_images_from_pdf(image_data)
            ocr_texts = []
            for i, img_data in enumerate(images[:5]):  # 最多处理5页
                yield {"type": "status", "message": f"正在OCR第{i+1}页..."}
                ocr_text = await self.llm_client.ocr(img_data, f"page_{i+1}.png")
                if ocr_text:
                    ocr_texts.append(ocr_text)
            text = "\n\n".join(ocr_texts) if ocr_texts else ""
            yield {"type": "status", "message": f"OCR完成，共处理{len(images)}页，提取到{len(text)}字符"}

        # 2. 检查提取的文本是否有效
        clean_text = text.strip() if text else ""
        if len(clean_text) < 20:
            raise ValueError(f"文件内容为空或无法识别有效文字（提取到{len(clean_text)}字符）")

        # 3. 使用LLM流式提取结构化信息（增加文本长度限制到20000字符）
        prompt = EXTRACT_PROMPT.format(text=text[:20000])
        full_result = ""

        async for chunk in self.llm_client.chat_stream(prompt):
            full_result += chunk
            yield {"type": "chunk", "content": chunk}

        # 3. 解析JSON结果（需要使用 await，但生成器中不能直接用，需要特殊处理）
        # 先解析JSON
        import json
        result = full_result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        data = json.loads(result)

        # 创建 ResumeData 对象（不包含学校验证）
        resume_data = self._parse_llm_result_basic(data, filename, file_type.value, text)

        # 4. 创建向量嵌入
        yield {"type": "status", "message": "正在创建语义向量..."}
        embedding_text = self._create_embedding_text(resume_data)
        embedding = await self.llm_client.get_embedding(embedding_text, text_type="document")

        # 5. 存储到ES（包含embedding和原始文件）
        self._save_to_es(resume_data, embedding, file_content)

        # 6. 更新ES，添加学校验证结果
        await self._update_school_verification(resume_data)

        yield {"type": "done", "data": resume_data}

    def _create_embedding_text(self, resume: ResumeData) -> str:
        """创建用于生成向量的文本摘要"""
        parts = []

        # 基本信息
        if resume.basic_info.name:
            parts.append(f"姓名: {resume.basic_info.name}")

        # 技能
        if resume.skills.hard_skills:
            parts.append(f"技能: {', '.join(resume.skills.hard_skills)}")

        # 工作经历
        for exp in resume.experience[:3]:
            parts.append(f"工作: {exp.company} {exp.title} {exp.duties[:200]}")

        # 教育背景
        for edu in resume.education[:2]:
            parts.append(f"教育: {edu.school} {edu.degree} {edu.major}")

        return "\n".join(parts)

    async def _parse_llm_result(
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

        # 清理基本信息中的字段
        basic_info_data = data.get("basic_info", {}) or {}

        # 确保字符串字段不是None
        for str_field in ["name", "phone", "email", "gender"]:
            if str_field in basic_info_data and basic_info_data[str_field] is None:
                basic_info_data[str_field] = ""

        # 如果 age 为空字符串或 None，先移除
        if "age" in basic_info_data and not basic_info_data["age"]:
            basic_info_data["age"] = None
        elif "age" in basic_info_data and basic_info_data["age"]:
            age_val = basic_info_data["age"]

            # 如果已经是合理的整数
            if isinstance(age_val, int) and 16 <= age_val <= 100:
                basic_info_data["age"] = age_val
            else:
                age_str = str(age_val)
                # 尝试提取合理的年龄
                import re

                # 匹配 "XX岁" 格式
                match = re.search(r'(\d{1,2})\s*岁', age_str)
                if match:
                    age = int(match.group(1))
                    basic_info_data["age"] = age if 16 <= age <= 100 else None
                # 匹配 "出生于XXXX年" 或 "XXXX年生"，计算年龄
                elif re.search(r'(19|20)\d{2}', age_str):
                    year_match = re.search(r'((?:19|20)\d{2})', age_str)
                    if year_match:
                        birth_year = int(year_match.group(1))
                        from datetime import datetime
                        current_year = datetime.now().year
                        age = current_year - birth_year
                        basic_info_data["age"] = age if 16 <= age <= 100 else None
                    else:
                        basic_info_data["age"] = None
                # 尝试直接解析数字
                else:
                    digits = ''.join(filter(str.isdigit, age_str))
                    if digits:
                        age = int(digits)
                        # 只接受合理范围的年龄
                        basic_info_data["age"] = age if 16 <= age <= 100 else None
                    else:
                        basic_info_data["age"] = None

        # 清理工作经历中的字段
        experience_list = []
        for exp in data.get("experience", []):
            # duties 可能是列表
            if "duties" in exp and isinstance(exp["duties"], list):
                exp["duties"] = "\n".join(exp["duties"])
            # 确保字符串字段不是None
            for str_field in ["company", "title", "duties", "start_date", "end_date"]:
                if str_field in exp and exp[str_field] is None:
                    exp[str_field] = ""
            experience_list.append(exp)

        # 清理教育经历中的字段 + 学校真实验证（使用增强服务）
        education_list = []
        education_warnings_list = []  # 初始化警告列表（包含学校验证警告）

        # 构建简历上下文用于学校验证
        resume_context_for_verification = {"education": data.get("education", [])}

        for edu in data.get("education", []):
            # 确保字符串字段不是None
            for str_field in ["school", "degree", "major", "start_date", "end_date"]:
                if str_field in edu and edu[str_field] is None:
                    edu[str_field] = ""

            # 使用增强的学校验证服务（智能体 + ES上下文 + LLM分析）
            school_name = edu.get("school", "").strip()
            if school_name:
                try:
                    enhanced_result = await verify_school_with_context(
                        school_name,
                        resume_context_for_verification
                    )

                    # 添加验证结果到教育经历中
                    edu["school_verified"] = enhanced_result.get("is_verified", False)
                    edu["school_verification_source"] = enhanced_result.get("source", "未知")
                    edu["school_verification_message"] = enhanced_result.get("analysis", "")

                    # 从权威数据中提取详细信息
                    authority_data = enhanced_result.get("authority_data", {})
                    if authority_data.get("moe_data"):
                        moe = authority_data["moe_data"]
                        edu["school_level"] = moe.get("level", "")
                        edu["school_department"] = moe.get("department", "")
                    else:
                        edu["school_level"] = ""
                        edu["school_department"] = ""

                    # 如果学校未验证，添加到 warnings
                    if not enhanced_result.get("is_verified", False):
                        suggestions = enhanced_result.get("suggestions", [])
                        message = f"学校 '{school}' 验证失败：{enhanced_result.get('analysis', '')}"
                        if suggestions:
                            message += f" 建议：{'; '.join(suggestions[:2])}"

                        education_warnings_list.append(EducationWarning(
                            risk_level="high" if enhanced_result.get("confidence") == "high" else "medium",
                            type="fake_university",
                            message=message
                        ))

                except Exception as verify_error:
                    print(f"[ResumeParser] 学校验证失败，使用基础验证: {verify_error}")
                    # 回退到基础验证
                    verification = university_service.verify(school_name)
                    edu["school_verified"] = verification.is_verified
                    edu["school_verification_source"] = verification.source
                    edu["school_verification_message"] = "; ".join(verification.warnings) if verification.warnings else verification.source
                    if verification.university:
                        edu["school_level"] = verification.university.level
                        edu["school_department"] = verification.university.department
                    else:
                        edu["school_level"] = ""
                        edu["school_department"] = ""

            education_list.append(edu)

        # 清理求职意向中的字段
        job_intention_data = data.get("job_intention", {}) or {}

        # 确保字符串字段不是None
        for str_field in ["position", "location"]:
            if str_field in job_intention_data and job_intention_data[str_field] is None:
                job_intention_data[str_field] = ""

        # 清理薪资字段
        for field in ["salary_min", "salary_max"]:
            if field in job_intention_data and job_intention_data[field]:
                val_str = str(job_intention_data[field]).upper()
                # 移除K/k后缀，乘以1000
                if "K" in val_str:
                    val_str = val_str.replace("K", "")
                    digits = ''.join(filter(str.isdigit, val_str))
                    job_intention_data[field] = int(digits) * 1000 if digits else None
                else:
                    digits = ''.join(filter(str.isdigit, val_str))
                    job_intention_data[field] = int(digits) if digits else None

        # 处理 LLM 返回的 education_warnings - 逻辑问题检测
        for w in data.get("education_warnings", []):
            if isinstance(w, str):
                education_warnings_list.append(EducationWarning(risk_level="medium", type="general", message=w))
            elif isinstance(w, dict):
                # 确保必需字段存在
                w.setdefault("risk_level", "medium")
                w.setdefault("type", "general")
                education_warnings_list.append(EducationWarning(**w))

        # 处理 warnings - LLM 可能返回字符串数组或对象数组
        warnings_list = []
        for w in data.get("warnings", []):
            if isinstance(w, str):
                warnings_list.append(Warning(type="general", message=w))
            elif isinstance(w, dict):
                warnings_list.append(Warning(**w))

        return ResumeData(
            id=resume_id,
            file_name=filename,
            file_type=file_type,
            raw_text=raw_text,
            basic_info=BasicInfo(**basic_info_data),
            education=[Education(**e) for e in education_list],
            experience=[Experience(**e) for e in experience_list],
            skills=Skills(**data.get("skills", {})),
            job_intention=JobIntention(**job_intention_data),
            education_warnings=education_warnings_list,
            warnings=warnings_list,
        )

    def _parse_llm_result_basic(
        self, data: dict, filename: str, file_type: str, raw_text: str
    ) -> ResumeData:
        """
        基础版本的LLM结果解析（同步，不包含学校验证）
        用于parse_with_text_stream生成器中，先返回基本数据
        """
        import uuid
        resume_id = str(uuid.uuid4())

        # 清理基本信息中的字段
        basic_info_data = data.get("basic_info", {}) or {}

        # 确保字符串字段不是None
        for str_field in ["name", "phone", "email", "gender"]:
            if str_field in basic_info_data and basic_info_data[str_field] is None:
                basic_info_data[str_field] = ""

        # 处理age字段
        if "age" in basic_info_data and not basic_info_data["age"]:
            basic_info_data["age"] = None
        elif "age" in basic_info_data and basic_info_data["age"]:
            age_val = basic_info_data["age"]
            if isinstance(age_val, int) and 16 <= age_val <= 100:
                basic_info_data["age"] = age_val
            else:
                import re
                age_str = str(age_val)
                match = re.search(r'(\d{1,2})\s*岁', age_str)
                if match:
                    age = int(match.group(1))
                    basic_info_data["age"] = age if 16 <= age <= 100 else None
                elif re.search(r'(19|20)\d{2}', age_str):
                    year_match = re.search(r'((?:19|20)\d{2})', age_str)
                    if year_match:
                        birth_year = int(year_match.group(1))
                        from datetime import datetime
                        basic_info_data["age"] = datetime.now().year - birth_year
                    else:
                        basic_info_data["age"] = None
                else:
                    digits = ''.join(filter(str.isdigit, age_str))
                    if digits:
                        age = int(digits)
                        basic_info_data["age"] = age if 16 <= age <= 100 else None
                    else:
                        basic_info_data["age"] = None

        # 清理工作经历
        experience_list = []
        for exp in data.get("experience", []):
            if "duties" in exp and isinstance(exp["duties"], list):
                exp["duties"] = "\n".join(exp["duties"])
            for str_field in ["company", "title", "duties", "start_date", "end_date"]:
                if str_field in exp and exp[str_field] is None:
                    exp[str_field] = ""
            experience_list.append(exp)

        # 清理教育经历（不包含学校验证）
        education_list = []
        for edu in data.get("education", []):
            for str_field in ["school", "degree", "major", "start_date", "end_date"]:
                if str_field in edu and edu[str_field] is None:
                    edu[str_field] = ""
            # 初始化验证字段为空
            edu["school_verified"] = False
            edu["school_verification_source"] = ""
            edu["school_verification_message"] = ""
            edu["school_level"] = ""
            edu["school_department"] = ""
            education_list.append(edu)

        # 清理求职意向
        job_intention_data = data.get("job_intention", {}) or {}
        for str_field in ["position", "location"]:
            if str_field in job_intention_data and job_intention_data[str_field] is None:
                job_intention_data[str_field] = ""

        # 处理薪资
        for field in ["salary_min", "salary_max"]:
            if field in job_intention_data and job_intention_data[field]:
                val_str = str(job_intention_data[field]).upper()
                if "K" in val_str:
                    val_str = val_str.replace("K", "")
                    digits = ''.join(filter(str.isdigit, val_str))
                    job_intention_data[field] = int(digits) * 1000 if digits else None
                else:
                    digits = ''.join(filter(str.isdigit, val_str))
                    job_intention_data[field] = int(digits) if digits else None

        # 处理warnings
        education_warnings_list = []
        for w in data.get("education_warnings", []):
            if isinstance(w, str):
                education_warnings_list.append(EducationWarning(risk_level="medium", type="general", message=w))
            elif isinstance(w, dict):
                w.setdefault("risk_level", "medium")
                w.setdefault("type", "general")
                education_warnings_list.append(EducationWarning(**w))

        warnings_list = []
        for w in data.get("warnings", []):
            if isinstance(w, str):
                warnings_list.append(Warning(type="general", message=w))
            elif isinstance(w, dict):
                warnings_list.append(Warning(**w))

        return ResumeData(
            id=resume_id,
            file_name=filename,
            file_type=file_type,
            raw_text=raw_text,
            basic_info=BasicInfo(**basic_info_data),
            education=[Education(**e) for e in education_list],
            experience=[Experience(**e) for e in experience_list],
            skills=Skills(**data.get("skills", {})),
            job_intention=JobIntention(**job_intention_data),
            education_warnings=education_warnings_list,
            warnings=warnings_list,
        )

    async def _update_school_verification(self, resume: ResumeData) -> None:
        """
        异步更新学校验证结果并保存到ES
        在ES保存后调用，更新学校验证信息
        """
        from app.models.resume import Education
        education_list = []
        education_warnings_list = list(resume.education_warnings)  # 复制现有警告

        # 构建简历上下文
        resume_context = {
            "education": [e.model_dump() for e in resume.education]
        }

        for edu in resume.education:
            edu_dict = edu.model_dump()
            school_name = edu.school.strip()

            if school_name:
                try:
                    # 使用增强的学校验证服务
                    enhanced_result = await verify_school_with_context(
                        school_name,
                        resume_context
                    )

                    edu_dict["school_verified"] = enhanced_result.get("is_verified", False)
                    edu_dict["school_verification_source"] = enhanced_result.get("source", "未知")
                    edu_dict["school_verification_message"] = enhanced_result.get("analysis", "")

                    authority_data = enhanced_result.get("authority_data", {})
                    if authority_data.get("moe_data"):
                        moe = authority_data["moe_data"]
                        edu_dict["school_level"] = moe.get("level", "")
                        edu_dict["school_department"] = moe.get("department", "")
                    else:
                        edu_dict["school_level"] = ""
                        edu_dict["school_department"] = ""

                    # 未验证通过则添加警告
                    if not enhanced_result.get("is_verified", False):
                        suggestions = enhanced_result.get("suggestions", [])
                        message = f"学校 '{school}' 验证失败：{enhanced_result.get('analysis', '')}"
                        if suggestions:
                            message += f" 建议：{'; '.join(suggestions[:2])}"
                        education_warnings_list.append(EducationWarning(
                            risk_level="high" if enhanced_result.get("confidence") == "high" else "medium",
                            type="fake_university",
                            message=message
                        ))

                except Exception as verify_error:
                    print(f"[ResumeParser] 学校验证失败: {verify_error}")
                    # 回退到基础验证
                    verification = university_service.verify(school_name)
                    edu_dict["school_verified"] = verification.is_verified
                    edu_dict["school_verification_source"] = verification.source
                    edu_dict["school_verification_message"] = "; ".join(verification.warnings) if verification.warnings else verification.source
                    if verification.university:
                        edu_dict["school_level"] = verification.university.level
                        edu_dict["school_department"] = verification.university.department
                    else:
                        edu_dict["school_level"] = ""
                        edu_dict["school_department"] = ""

            education_list.append(Education(**edu_dict))

        # 更新resume对象
        resume.education = education_list
        resume.education_warnings = education_warnings_list

        # 更新ES文档
        try:
            doc = resume.model_dump(mode="json")
            # 只更新验证相关字段，不影响其他数据
            update_doc = {
                "education": doc.get("education", []),
                "education_warnings": doc.get("education_warnings", [])
            }
            self.es_client.update_document(RESUME_INDEX, resume.id, update_doc)
        except Exception as e:
            print(f"[ResumeParser] 更新ES学校验证失败: {e}")

    def _match_all_jds(self, resume: ResumeData) -> list[RecommendedJD]:
        """匹配所有JD，返回推荐列表（按匹配度排序）"""
        from app.services.jd_service import JDService
        from app.services.job_matcher import job_matcher, JobRequirement

        recommended = []
        try:
            jd_service = JDService()
            jd_result = jd_service.list(1, 100)  # 获取所有JD
            jds = jd_result.get("data", [])

            for jd in jds:
                job_req = JobRequirement(
                    title=jd.title,
                    description=jd.description,
                    required_skills=jd.required_skills,
                    preferred_skills=jd.preferred_skills,
                )
                match_result = job_matcher.match(resume, job_req)

                # 只保留匹配度 >= 40 的
                if match_result.overall_score >= 40:
                    recommended.append(RecommendedJD(
                        jd_id=jd.id,
                        jd_title=jd.title,
                        match_score=match_result.overall_score,
                        matched_skills=match_result.matched_skills[:5]
                    ))

            # 按匹配度排序
            recommended.sort(key=lambda x: x.match_score, reverse=True)
        except Exception as e:
            print(f"Match JDs error: {e}")

        return recommended[:5]  # 最多返回5个推荐

    def _save_to_es(self, resume: ResumeData, embedding: list[float] = None, raw_content: bytes = None):
        from datetime import datetime
        from app.services.encryption_service import encryption_service

        # 自动匹配JD
        resume.recommended_jds = self._match_all_jds(resume)

        doc = resume.model_dump(mode="json")
        if embedding:
            doc["embedding"] = embedding

        # 存储原始文件内容（AES加密）
        if raw_content:
            doc["file_content"] = encryption_service.encrypt(raw_content)
            doc["file_size"] = len(raw_content)
            doc["encrypted"] = True  # 标记已加密

        # 加密敏感个人信息
        if doc.get("basic_info"):
            basic = doc["basic_info"]
            if basic.get("phone"):
                basic["phone_encrypted"] = encryption_service.encrypt_string(basic["phone"])
                basic["phone"] = basic["phone"][:3] + "****" + basic["phone"][-4:] if len(basic["phone"]) >= 7 else "****"
            if basic.get("email"):
                basic["email_encrypted"] = encryption_service.encrypt_string(basic["email"])
                # 邮箱脱敏：显示前2个字符和@后面的域名
                if "@" in basic["email"]:
                    local, domain = basic["email"].split("@", 1)
                    basic["email"] = local[:2] + "***@" + domain
                else:
                    basic["email"] = "***"

        # 添加创建时间
        doc["created_at"] = datetime.now().isoformat()

        self.es_client.index_document(RESUME_INDEX, resume.id, doc)

    def get_resume(self, resume_id: str) -> ResumeData | None:
        try:
            result = self.es_client.get_document(RESUME_INDEX, resume_id)
            return ResumeData(**result["_source"])
        except Exception:
            return None

    def list_resumes(self, page: int = 1, size: int = 20) -> dict:
        query = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }
        result = self.es_client.search(RESUME_INDEX, query)
        total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
        data = [ResumeData(**hit["_source"]) for hit in result["hits"]["hits"]]
        return {"data": data, "total": total}

    def delete_resume(self, resume_id: str) -> bool:
        try:
            self.es_client.delete_document(RESUME_INDEX, resume_id)
            return True
        except Exception:
            return False
