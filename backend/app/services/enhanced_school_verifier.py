"""
增强的学校验证服务 - 使用智能体+ES上下文进行分析

流程：
1. 智能体提取学校名称
2. ES搜索获取教育部等权威数据源的上下文
3. 带上下文让LLM进行准确分析
"""
import json
from typing import Optional, List, Dict
from app.services.llm_client import LLMClient
from app.services.es_client import ESClient
from app.services.university_service import university_service


class EnhancedSchoolVerifier:
    """增强的学校验证器"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.es_client = ESClient()
        self.university_service = university_service

    async def verify_with_context(
        self,
        school_name: str,
        resume_context: Optional[dict] = None
    ) -> dict:
        """
        带上下文的学校验证

        Args:
            school_name: 学校名称
            resume_context: 简历上下文（用于更准确的分析）

        Returns:
            验证结果，包含：
            - is_verified: 是否通过验证
            - source: 数据来源
            - confidence: 匹配度
            - analysis: 详细分析
            - suggestions: 建议
        """
        # 步骤1: 用智能体提取标准化的学校名称
        extracted_name = await self._extract_school_name(school_name)

        # 步骤2: 获取权威数据源的上下文
        context = await self._get_authority_context(extracted_name)

        # 步骤3: 带上下文进行LLM分析
        analysis = await self._analyze_with_llm(
            original_name=school_name,
            extracted_name=extracted_name,
            context=context,
            resume_context=resume_context
        )

        return {
            "original_name": school_name,
            "extracted_name": extracted_name,
            "is_verified": analysis.get("is_verified", False),
            "source": analysis.get("source", "未知"),
            "confidence": analysis.get("confidence", "low"),
            "analysis": analysis.get("analysis", ""),
            "suggestions": analysis.get("suggestions", []),
            "authority_data": context
        }

    async def _extract_school_name(self, raw_name: str) -> str:
        """使用智能体提取标准化的学校名称"""
        prompt = f"""请从以下文本中提取学校的标准名称，去除多余的描述词。

原始文本: "{raw_name}"

要求：
1. 只返回学校名称，不要返回其他内容
2. 去除"学院"、"大学"后的地域修饰词如"进修"、"研修"等非正规学历字样
3. 如果是分校，请标注主校区，如"中国石油大学（北京）"
4. 如果是知名院校的简称，请还原全称

学校名称:"""

        try:
            result = await self.llm_client.chat(prompt)
            # 清理结果
            result = result.strip().strip('"').strip("'").strip("：")
            # 移除可能的"学校名称:"前缀
            if "学校名称" in result:
                result = result.split("学校名称")[-1].strip()
            return result if result else raw_name
        except Exception as e:
            print(f"[SchoolVerifier] 提取学校名称失败: {e}")
            return raw_name

    async def _get_authority_context(self, school_name: str) -> dict:
        """获取权威数据源的上下文信息"""
        context = {
            "moe_data": None,  # 教育部数据
            "es_records": [],  # ES中相似的学校记录
            "is_blacklisted": False  # 是否在黑名单
        }

        # 1. 查询教育部官方数据
        verification = self.university_service.verify(school_name)
        if verification.university:
            context["moe_data"] = {
                "name": verification.university.name,
                "code": verification.university.code,
                "level": verification.university.level,
                "department": verification.university.department,
                "location": verification.university.location,
                "is_private": verification.university.is_private
            }
        elif not verification.is_verified and "黑名单" in verification.source:
            context["is_blacklisted"] = True

        # 2. 在ES中搜索相似的学校名称（用于别名匹配）
        try:
            # 使用模糊搜索
            search_query = {
                "query": {
                    "multi_match": {
                        "query": school_name,
                        "fields": ["education.school^3", "basic_info.name"],
                        "fuzziness": "AUTO"
                    }
                },
                "size": 5,
                "_source": ["education.school", "education.degree", "basic_info.name"]
            }
            result = self.es_client.search("resumes", search_query)

            for hit in result.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                for edu in source.get("education", []):
                    if edu.get("school") and edu["school"] != school_name:
                        context["es_records"].append({
                            "school": edu["school"],
                            "degree": edu.get("degree", "")
                        })
        except Exception as e:
            print(f"[SchoolVerifier] ES搜索失败: {e}")

        return context

    async def _analyze_with_llm(
        self,
        original_name: str,
        extracted_name: str,
        context: dict,
        resume_context: Optional[dict] = None
    ) -> dict:
        """带上下文进行LLM分析"""
        # 构建上下文描述
        context_parts = []

        if context.get("moe_data"):
            moe = context["moe_data"]
            context_parts.append(f"""
**教育部官方数据**:
- 正规院校: 是
- 学校名称: {moe['name']}
- 学校代码: {moe['code']}
- 办学层次: {moe['level']}
- 主管部门: {moe['department']}
- 所在地: {moe['location']}
- 性质: {'民办' if moe['is_private'] else '公立'}
""")

        if context.get("is_blacklisted"):
            context_parts.append("**风险提示**: 此名称匹配已知的虚假院校关键词")

        if context.get("es_records"):
            similar = context["es_records"][:3]
            schools = ", ".join([s["school"] for s in similar])
            context_parts.append(f"**相似的学校名称**: {schools}")

        context_text = "\n".join(context_parts) if context_parts else "未找到权威数据"

        # 简历上下文（用于更准确的判断）
        resume_info = ""
        if resume_context:
            education = resume_context.get("education", [])
            if education:
                edu_strs = [f"{e.get('school', '')} {e.get('degree', '')}" for e in education[:3]]
                resume_info = f"\n候选人其他教育经历: {', '.join(edu_strs)}"

        prompt = f"""你是一个专业的学历认证专家。请对以下学校进行验证分析。

## 待验证学校
- 原始填写: {original_name}
- 提取名称: {extracted_name}
{resume_info}

## 权威数据源上下文
{context_text}

## 分析要求
请根据权威数据源判断该学校的真实性，并返回JSON：
{{
  "is_verified": true/false（是否为正规院校）,
  "source": "数据来源说明",
  "confidence": "high/medium/low",
  "analysis": "详细分析说明",
  "suggestions": ["建议1", "建议2"]
}}

判断标准：
- 在教育部官方名单中 → is_verified=true, source="教育部官方名单"
- 匹配黑名单关键词 → is_verified=false, source="黑名单数据库"
- 与知名院校高度相似但有差异 → is_verified=false, source="相似度分析"
- 无法确认但无负面信息 → is_verified=false, confidence="low"

只返回JSON，不要其他内容。"""

        try:
            result = await self.llm_client.chat(prompt)
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(result.strip())
        except Exception as e:
            print(f"[SchoolVerifier] LLM分析失败: {e}")
            # 回退到基础验证
            if context.get("moe_data"):
                return {
                    "is_verified": True,
                    "source": "教育部官方名单",
                    "confidence": "high",
                    "analysis": "该学校在教育部官方名单中",
                    "suggestions": []
                }
            elif context.get("is_blacklisted"):
                return {
                    "is_verified": False,
                    "source": "黑名单数据库",
                    "confidence": "high",
                    "analysis": "该名称匹配已知虚假院校关键词",
                    "suggestions": ["请核实学历证书的真实性"]
                }
            else:
                return {
                    "is_verified": False,
                    "source": "未知",
                    "confidence": "low",
                    "analysis": "未在权威数据源中找到该学校",
                    "suggestions": ["可能是海外院校或新成立院校", "请提供更多证明材料"]
                }


# 全局实例
enhanced_school_verifier = EnhancedSchoolVerifier()


async def verify_school_with_context(school_name: str, resume_context: Optional[dict] = None) -> dict:
    """便捷函数：带上下文的学校验证"""
    return await enhanced_school_verifier.verify_with_context(school_name, resume_context)
