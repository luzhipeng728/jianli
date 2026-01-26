"""JD Analyzer Service - Pre-processes JD and resume to generate interview strategy

Uses Qwen-Plus (stronger model) to:
1. Analyze JD and extract key requirements
2. Match resume skills with JD requirements
3. Generate targeted question directions for each phase
"""

import os
import sys
import json
import httpx
from typing import Optional, Dict, List, AsyncGenerator, Callable, Awaitable, Union
from pydantic import BaseModel

# Type alias for async progress callback
ProgressCallback = Callable[[str], Awaitable[None]]


class InterviewStrategy(BaseModel):
    """面试策略，包含各阶段的提问方向"""
    # JD 核心要求
    core_requirements: List[str]  # 核心技术要求
    nice_to_have: List[str]  # 加分项

    # 简历与JD匹配分析
    matched_skills: List[str]  # 简历中匹配的技能
    gaps: List[str]  # 可能的差距/需要深入考察的点
    highlights: List[str]  # 简历亮点

    # 各阶段提问方向
    self_intro_focus: str  # 自我介绍时关注什么
    project_questions: List[str]  # 项目深挖的具体问题（必须5个不同话题）
    tech_questions: List[str]  # 技术评估的具体问题（必须5个不同话题）
    behavioral_questions: List[str]  # 行为面试问题（必须3个不同话题）

    # 面试官开场白建议
    opening_script: str


class JDAnalyzer:
    """JD分析器 - 使用更强的模型进行预分析"""

    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        # 使用 Qwen-Plus 进行分析（比 Flash 更强，适合复杂分析任务）
        self.model = "qwen-plus"

    async def analyze(
        self,
        jd_text: str,
        resume_summary: str,
        position_name: str = "",
        on_progress: Optional[ProgressCallback] = None
    ) -> InterviewStrategy:
        """分析JD和简历，生成面试策略（支持流式进度回调）

        Args:
            jd_text: 岗位JD原文
            resume_summary: 简历摘要
            position_name: 岗位名称
            on_progress: 异步进度回调函数，接收分析过程的文字

        Returns:
            InterviewStrategy: 面试策略
        """
        print(f"[JDAnalyzer] analyze() called", flush=True)
        print(f"[JDAnalyzer] API key: {self.api_key[:10]}..." if self.api_key else "[JDAnalyzer] No API key!", flush=True)
        print(f"[JDAnalyzer] on_progress callback: {on_progress is not None}", flush=True)

        # 重置进度状态
        self._reset_progress_state()

        # 发送分析开始提示
        if on_progress:
            print("[JDAnalyzer] Calling on_progress for first message", flush=True)
            await on_progress(f"🔍 正在分析 {position_name or '技术岗位'} 岗位需求...\n")
            print("[JDAnalyzer] First progress message sent", flush=True)

        prompt = f"""你是一位资深的技术面试官和人才评估专家。请分析以下岗位JD和候选人简历，生成一份详细的面试策略。

## 岗位名称
{position_name or "技术岗位"}

## 岗位JD
{jd_text or "暂无详细JD"}

## 候选人简历
{resume_summary or "暂无简历信息"}

## 你的任务
请深入分析JD和简历，生成JSON格式的面试策略。

【核心原则 - 必须严格遵守】
根据JD需求，从简历中抽取相关工作经验，生成针对性问题。

问题生成逻辑：
1. 看JD要求什么技能/经验
2. 在简历中找到候选人相关的项目/工作经历
3. 生成问题：针对【简历中的具体项目】问【JD要求的技能点】

示例：
- JD要求"Agent开发" + 简历有"AI智能体银行项目"
  → 问题："你在AI智能体银行项目中是如何设计Agent架构的？"
- JD要求"RAG技术" + 简历有"知识库问答系统"
  → 问题："你在知识库问答系统中是如何实现RAG检索增强的？"
- JD要求"Prompt工程" + 简历有"大模型应用开发"
  → 问题："你在大模型应用开发中做过哪些Prompt优化？效果如何？"

【绝对禁止】
- 不要问简历中没有的项目
- 不要问JD没要求的技术
- 不要问泛泛的通用问题（如"介绍一个项目"）

每个问题必须：JD要求 + 简历中的具体项目名 = 针对性问题

请严格按照以下JSON格式输出：
```json
{{
  "core_requirements": ["JD中的核心技术要求1", "核心要求2", ...],
  "nice_to_have": ["加分项1", "加分项2", ...],
  "matched_skills": ["候选人简历中匹配JD的技能1", "技能2", ...],
  "gaps": ["可能的差距或需要深入考察的点1", "点2", ...],
  "highlights": ["简历亮点1", "亮点2", ...],
  "self_intro_focus": "自我介绍时应该关注的重点，一句话描述",
  "project_questions": [
    "你在【简历项目A】中是如何实现【JD要求的技术X】的？",
    "【简历项目B】中涉及到【JD要求Y】吗？具体是怎么做的？",
    "关于【JD核心要求Z】，你在【简历项目C】中有哪些实践？",
    "你在【简历项目D】中遇到的【JD相关技术】难点是什么？怎么解决的？",
    "【简历项目E】的【JD要求的能力】方面，取得了什么成果？"
  ],
  "tech_questions": [
    "关于【JD技术要求1】，你在实际项目中是怎么应用的？",
    "JD要求【技术2】，请结合你的【相关项目】详细说明",
    "针对【JD技术3】，你的理解和实践经验是什么？",
    "JD提到【技术4】，你在【简历相关经历】中是如何使用的？",
    "关于【JD技术5】，请分享你的最佳实践"
  ],
  "behavioral_questions": [
    "JD要求【软技能1】，请结合【简历经历】举例说明",
    "关于【JD软技能2】，你在【具体项目】中是如何体现的？",
    "针对【JD要求3】，分享一个你的实际案例"
  ],
  "opening_script": "面试官开场白，介绍自己并说明面试流程，2-3句话"
}}
```

请直接输出JSON，不要有其他内容。"""

        try:
            if on_progress:
                await on_progress("📋 正在分析岗位要求和简历匹配度...\n\n")

            # 使用流式API调用，实时显示分析过程
            full_content = ""
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "stream": True,  # 启用流式输出
                        "response_format": {"type": "json_object"}
                    }
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        print(f"[JDAnalyzer] API error: {response.status_code} - {error_text}", flush=True)
                        if on_progress:
                            await on_progress("⚠️ 分析遇到问题，使用默认策略\n")
                        return self._get_default_strategy(position_name)

                    # 流式读取响应，并实时显示有意义的内容
                    chunk_count = 0
                    last_sent_len = 0
                    in_array = False  # 跟踪是否在数组中
                    array_key = ""  # 当前数组的key

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})
                            content_chunk = delta.get("content", "")

                            if content_chunk:
                                full_content += content_chunk
                                chunk_count += 1

                                # 尝试实时解析并显示有意义的内容
                                if on_progress:
                                    # 每50个字符检查一次是否有新的完整字段
                                    if len(full_content) - last_sent_len > 50:
                                        # 提取已完成的数组内容
                                        extracted = self._extract_readable_progress(full_content)
                                        if extracted:
                                            await on_progress(extracted)
                                            last_sent_len = len(full_content)

                        except json.JSONDecodeError:
                            continue

                    print(f"[JDAnalyzer] Received {chunk_count} chunks, content length: {len(full_content)}", flush=True)

            if on_progress:
                await on_progress("\n\n🎯 正在生成面试问题...\n")

            # 解析JSON
            try:
                # 尝试直接解析
                strategy_dict = json.loads(full_content)
            except json.JSONDecodeError:
                # 尝试提取JSON块
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', full_content, re.DOTALL)
                if json_match:
                    strategy_dict = json.loads(json_match.group(1))
                else:
                    print(f"[JDAnalyzer] Failed to parse JSON: {full_content[:200]}", flush=True)
                    if on_progress:
                        await on_progress("⚠️ 解析失败，使用默认策略\n")
                    return self._get_default_strategy(position_name)

            strategy = InterviewStrategy(**strategy_dict)

            # 发送分析结果摘要
            if on_progress:
                summary = f"""
✅ 分析完成！

📌 核心要求: {', '.join(strategy.core_requirements[:3])}
💡 候选人亮点: {', '.join(strategy.highlights[:2]) if strategy.highlights else '待发现'}
🔎 重点考察: {', '.join(strategy.gaps[:2]) if strategy.gaps else '全面了解'}

📝 已生成 {len(strategy.project_questions)} 个项目问题、{len(strategy.tech_questions)} 个技术问题
"""
                await on_progress(summary)

            print(f"[JDAnalyzer] Generated strategy with {len(strategy.project_questions)} project questions", flush=True)
            return strategy

        except Exception as e:
            import traceback
            print(f"[JDAnalyzer] Error: {e}", flush=True)
            traceback.print_exc()
            sys.stdout.flush()
            if on_progress:
                await on_progress(f"⚠️ 分析出错: {str(e)[:50]}，使用默认策略\n")
            return self._get_default_strategy(position_name)

    def _extract_readable_progress(self, partial_json: str) -> str:
        """从部分JSON中提取可读的进度信息"""
        import re

        # 定义要提取的字段及其显示名称
        field_patterns = [
            (r'"core_requirements"\s*:\s*\[([^\]]*)', "📌 核心要求: "),
            (r'"nice_to_have"\s*:\s*\[([^\]]*)', "✨ 加分项: "),
            (r'"matched_skills"\s*:\s*\[([^\]]*)', "✅ 匹配技能: "),
            (r'"gaps"\s*:\s*\[([^\]]*)', "🔍 考察重点: "),
            (r'"highlights"\s*:\s*\[([^\]]*)', "💡 候选人亮点: "),
            (r'"self_intro_focus"\s*:\s*"([^"]*)', "👤 自我介绍关注: "),
            (r'"project_questions"\s*:\s*\[([^\]]*)', "📝 项目问题: "),
            (r'"tech_questions"\s*:\s*\[([^\]]*)', "🔧 技术问题: "),
            (r'"behavioral_questions"\s*:\s*\[([^\]]*)', "🤝 行为问题: "),
        ]

        # 记录已显示的字段（使用类属性来跨调用保持状态）
        if not hasattr(self, '_shown_fields'):
            self._shown_fields = set()

        result = []
        for pattern, prefix in field_patterns:
            match = re.search(pattern, partial_json, re.DOTALL)
            if match and prefix not in self._shown_fields:
                content = match.group(1).strip()
                # 只提取完整的字符串项
                items = re.findall(r'"([^"]+)"', content)
                if items:
                    # 只显示前2-3项
                    display_items = items[:3]
                    if display_items:
                        self._shown_fields.add(prefix)
                        result.append(f"{prefix}{', '.join(display_items)}")

        if result:
            return "\n" + "\n".join(result)
        return ""

    def _reset_progress_state(self):
        """重置进度状态"""
        if hasattr(self, '_shown_fields'):
            self._shown_fields.clear()

    def _get_default_strategy(self, position_name: str = "") -> InterviewStrategy:
        """返回默认面试策略"""
        return InterviewStrategy(
            core_requirements=["技术能力", "项目经验", "问题解决能力"],
            nice_to_have=["团队协作", "沟通能力"],
            matched_skills=[],
            gaps=["需要在面试中进一步了解"],
            highlights=[],
            self_intro_focus="关注候选人的核心技能和最近的项目经验",
            project_questions=[
                "请详细介绍你最近参与的一个项目，你在其中承担什么角色？",
                "这个项目中遇到的最大技术挑战是什么？你是如何解决的？",
                "这个项目的技术架构是怎样的？你负责哪部分？",
                "这个项目取得了什么成果？有没有可量化的数据？",
                "在这个项目中你和团队是如何协作的？"
            ],
            tech_questions=[
                "请介绍一下你对分布式系统的理解",
                "在你的项目中是如何保证系统稳定性的？",
                "请描述一个你解决过的复杂技术问题",
                "如何设计一个高可用的系统？你有什么经验？",
                "在性能优化方面你做过哪些工作？"
            ],
            behavioral_questions=[
                "请分享一次你与团队成员意见不一致的经历，你是如何处理的？",
                "描述一次你在紧急情况下需要快速做出技术决策的经历",
                "你是如何学习新技术的？能举个例子吗？"
            ],
            opening_script=f"你好，我是XX公司的技术面试官，今天由我来主持{position_name or '这个岗位'}的面试。整个过程大约30-40分钟，我会围绕你的项目经验和技术能力进行提问。你准备好了吗？"
        )


# 单例
_jd_analyzer: Optional[JDAnalyzer] = None

def get_jd_analyzer() -> JDAnalyzer:
    global _jd_analyzer
    if _jd_analyzer is None:
        _jd_analyzer = JDAnalyzer()
    return _jd_analyzer
