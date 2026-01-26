#!/usr/bin/env python3
"""
Create mock interview data for HR replay testing
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.interview_record import (
    InterviewRecord, InterviewRecordStatus,
    EvaluationReport, EvaluationDimension
)
from app.models.dialogue import DialogueEntry, DialogueRole, PhaseTransition
from app.models.interview_phase import InterviewPhase
from app.services.interview_storage import get_interview_storage

def create_mock_interview():
    """Create a complete mock interview for 陆志鹏"""

    storage = get_interview_storage()

    # Use the existing session or create new one
    session_id = "mock-interview-luzhipeng-001"
    resume_id = "5a1ba404-e2fb-4a3d-af27-e17c04e396b7"
    jd_id = "a4aaa479-c2f8-40e5-9f54-0dab260f0229"

    # Base timestamp
    base_time = datetime.now() - timedelta(hours=2)

    # Create interview record
    record = InterviewRecord(
        session_id=session_id,
        resume_id=resume_id,
        jd_id=jd_id,
        status=InterviewRecordStatus.COMPLETED,
        current_phase=InterviewPhase.CLOSING,
        current_round=0,
        created_at=base_time,
        started_at=base_time + timedelta(seconds=10),
        completed_at=base_time + timedelta(minutes=35),
        audio_dir=f"/data/interviews/{session_id}"
    )

    # Helper to create dialogue entry
    def add_dialogue(role: str, content: str, phase: str, round_num: int, offset_seconds: int):
        entry = DialogueEntry(
            id=f"{base_time.strftime('%Y%m%d%H%M%S')}{offset_seconds:06d}",
            role=DialogueRole(role),
            content=content,
            phase=phase,
            round_number=round_num,
            timestamp=base_time + timedelta(seconds=offset_seconds),
            duration_seconds=len(content) * 0.1  # Approximate duration
        )
        record.dialogues.append(entry)
        return entry

    offset = 10

    # ========== PHASE 1: OPENING ==========
    add_dialogue(
        "interviewer",
        "你好，我是本次面试的技术面试官。欢迎参加我们AI智能体工程师岗位的面试。今天的面试大约30-40分钟，我们会从你的背景、项目经验、技术能力等方面进行交流。你准备好了吗？",
        "opening", 0, offset
    )
    offset += 15

    add_dialogue(
        "candidate",
        "您好，我准备好了，感谢给我这次面试机会。",
        "opening", 0, offset
    )
    offset += 8

    record.phase_transitions.append(PhaseTransition(
        from_phase="opening",
        to_phase="self_intro",
        reason="max_rounds_reached",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 2: SELF_INTRO ==========
    add_dialogue(
        "interviewer",
        "好的，那请你先做一个简单的自我介绍吧，包括你的教育背景和主要的工作经历。",
        "self_intro", 0, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "好的。我叫陆志鹏，今年35岁，本科是测控技术与仪器专业。我有超过10年的独立项目开发经验，精通物联网软硬件整合。最近这一年多主要在做AI智能体相关的工作，包括在北京易诚互动负责开发公司的智能体平台，基于Coze开源版本进行二次开发，在银行场景落地了多个智能体应用。之前在高维智控做了三年多的全栈工程师，主要负责机器人应用程序框架的开发。我对AI和智能体领域非常感兴趣，一直在持续学习和实践。",
        "self_intro", 0, offset
    )
    offset += 45

    add_dialogue(
        "interviewer",
        "很好，你提到了智能体平台开发和银行场景落地，这些听起来很有意思。我们待会深入聊聊。",
        "self_intro", 1, offset
    )
    offset += 10

    record.phase_transitions.append(PhaseTransition(
        from_phase="self_intro",
        to_phase="project_deep",
        reason="llm_decision",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 3: PROJECT_DEEP ==========
    add_dialogue(
        "interviewer",
        "你刚才提到在北京易诚互动开发智能体平台，能详细介绍一下这个项目吗？你具体负责哪些模块？",
        "project_deep", 0, offset
    )
    offset += 12

    add_dialogue(
        "candidate",
        "这个项目是公司的低代码智能体平台，叫猎鹰智能体。用户可以通过在画布里添加不同的节点，通过拖拽连线的方式构建工作流。我主要负责几个核心模块：一是在Coze开源版本中添加企业相关功能节点，比如知识库检索、意图识别等；二是负责整个平台的部署和性能优化，我们要支持ARM和x86两种架构的国产机器，包括华为升腾和阿里PPU；三是基于Ragflow优化了知识库系统，替换了原来的检索逻辑，提升了检索准确率。",
        "project_deep", 0, offset
    )
    offset += 60

    add_dialogue(
        "interviewer",
        "你提到用Ragflow优化知识库系统，能具体说说你做了哪些优化？效果怎么样？",
        "project_deep", 1, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "原来Coze的知识库用的是比较简单的向量检索，对于复杂文档的理解不够好。我们引入Ragflow后，主要做了几个优化：第一是文档解析，Ragflow支持多种格式的文档解析，包括PDF、Word等，解析质量比原来好很多；第二是分块策略，我们根据银行文档的特点，定制了按章节和段落的分块规则；第三是混合检索，同时使用关键词和向量检索，然后做结果融合。优化后知识库的召回准确率从原来的60%左右提升到了85%以上。",
        "project_deep", 1, offset
    )
    offset += 55

    add_dialogue(
        "interviewer",
        "不错的提升。你们在银行场景落地智能体应用，遇到过什么技术挑战吗？是怎么解决的？",
        "project_deep", 2, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "银行场景最大的挑战是安全合规和数据隔离。首先是部署环境，银行要求私有化部署，不能用公有云，而且对国产化有要求，所以我们要支持多种国产硬件。我们用Docker进行环境隔离，然后针对不同架构做了适配和优化。其次是数据安全，银行数据不能出域，所以我们的知识库只能用内部数据训练，这就要求模型和检索能力要足够强才能在有限数据下有好的效果。我们用微调的方式优化了意图识别小模型，对标HiAgent的主Bot意图识别能力。",
        "project_deep", 2, offset
    )
    offset += 70

    add_dialogue(
        "interviewer",
        "你提到微调意图识别模型，能说说用什么方法？数据怎么准备的？",
        "project_deep", 3, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "我们用的是Qwen-2.5-7B作为基础模型，用LoRA方法进行微调。数据准备方面，我们收集了银行客服的历史对话记录，大概有几千条，然后用Claude和GPT-4进行数据清洗和标注，标注意图类别和槽位信息。训练时我们用了deepspeed做分布式训练，在2张A100上训练了大概一天。微调后的模型在银行场景的意图识别准确率达到了92%，比用通用大模型直接做意图识别要高10个百分点左右。",
        "project_deep", 3, offset
    )
    offset += 65

    record.phase_transitions.append(PhaseTransition(
        from_phase="project_deep",
        to_phase="tech_assess",
        reason="max_rounds_reached",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 4: TECH_ASSESS ==========
    add_dialogue(
        "interviewer",
        "好，我们来聊聊技术方面。你对大语言模型的提示工程有什么理解？在实际项目中是怎么优化prompt的？",
        "tech_assess", 0, offset
    )
    offset += 12

    add_dialogue(
        "candidate",
        "提示工程是让大模型输出符合预期的关键。我的经验是，首先要明确任务目标，把复杂任务拆解成小步骤，用Chain of Thought的方式引导模型思考。其次是Few-shot learning，给模型提供几个高质量的示例，特别是对于格式要求严格的任务。另外我们在智能体平台中大量使用了系统提示词模板，针对不同的Agent角色定义了不同的人设和能力边界。在银行场景中，我们还特别注意了提示词的安全性，防止prompt注入攻击。",
        "tech_assess", 0, offset
    )
    offset += 55

    add_dialogue(
        "interviewer",
        "你提到Agent，能说说你对多Agent协作的理解吗？你们是怎么实现Agent之间通信的？",
        "tech_assess", 1, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "多Agent协作我理解主要有几种模式：一种是主从模式，有一个控制器Agent负责任务分发和结果汇总，下面有多个专业Agent负责具体任务；另一种是对等模式，Agent之间可以直接通信协作。我们平台主要用的是第一种模式，通过一个意图识别主Bot来分发任务。Agent之间的通信我们用消息队列来实现，每个Agent有自己的消息订阅主题，控制器通过发布消息来调度。对于需要上下文共享的场景，我们用Redis存储会话状态，各Agent可以读写共享的会话数据。",
        "tech_assess", 1, offset
    )
    offset += 65

    add_dialogue(
        "interviewer",
        "你对RAG技术了解多少？如何评估RAG系统的效果？",
        "tech_assess", 2, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "RAG是检索增强生成，核心是把检索和生成结合起来，让模型能够利用外部知识。评估RAG效果主要看几个指标：检索阶段看召回率和准确率，我们会构建一个标注数据集，标注每个问题对应的正确文档，然后评估检索模块能不能把正确文档检索出来。生成阶段主要看答案质量，包括准确性、完整性和流畅性，可以用人工评估或者用大模型做自动评估。另外还有端到端的指标，比如用户满意度，我们会在银行客服场景中收集用户的反馈来持续优化。",
        "tech_assess", 2, offset
    )
    offset += 60

    add_dialogue(
        "interviewer",
        "假设你需要优化一个RAG系统的响应延迟，你会从哪些方面入手？",
        "tech_assess", 3, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "优化延迟我会从几个方面考虑：首先是检索层面，可以用向量数据库的ANN索引加速，比如HNSW或IVF索引，牺牲一点召回率换取速度。其次是embedding计算，可以用模型蒸馏得到更小的embedding模型，或者做embedding缓存。然后是生成层面，可以用更小的模型或者做模型量化，还可以用流式输出让用户更快看到结果。另外是架构层面，可以做预检索缓存，对高频问题缓存答案；还可以异步化，把检索和其他预处理并行做。我们在银行项目中综合用了这些方法，把端到端延迟从5秒降到了2秒以内。",
        "tech_assess", 3, offset
    )
    offset += 70

    record.phase_transitions.append(PhaseTransition(
        from_phase="tech_assess",
        to_phase="behavioral",
        reason="max_rounds_reached",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 5: BEHAVIORAL ==========
    add_dialogue(
        "interviewer",
        "好的，技术方面聊得差不多了。接下来我想了解一下你的工作方式。能分享一次你在项目中遇到重大技术难题，是怎么解决的吗？",
        "behavioral", 0, offset
    )
    offset += 12

    add_dialogue(
        "candidate",
        "印象最深的是去年在银行项目部署时，我们遇到一个内存泄漏问题。智能体平台在长时间运行后会占用越来越多内存，最后导致服务崩溃。我首先用Python的memory_profiler定位问题，发现是在处理大文档时，我们的向量缓存没有设置上限，而且有些对象没有正确释放。解决方案是引入LRU缓存限制大小，并且用弱引用处理某些临时对象。另外我还加了内存监控告警，当内存使用超过阈值时自动触发GC。最终问题解决后，服务可以稳定运行一个月以上不需要重启。",
        "behavioral", 0, offset
    )
    offset += 70

    add_dialogue(
        "interviewer",
        "不错的问题解决能力。你是怎么和团队成员协作的？有没有遇到过意见不一致的情况？",
        "behavioral", 1, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "我比较注重沟通和文档化。在技术方案讨论时，我会先把自己的想法写成文档，包括背景、方案对比、优缺点分析，然后组织技术评审。意见不一致是常有的，比如之前我们在选择向量数据库时，有同事倾向用Milvus，我倾向用Elasticsearch的向量功能。我们做了一次对比测试，从性能、运维成本、学习曲线等多个维度评估，最后选择了ES，因为团队更熟悉ES，而且我们的数据量不是特别大，ES完全能满足需求。关键是用数据说话，而不是争论。",
        "behavioral", 1, offset
    )
    offset += 65

    record.phase_transitions.append(PhaseTransition(
        from_phase="behavioral",
        to_phase="qa",
        reason="max_rounds_reached",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 6: QA ==========
    add_dialogue(
        "interviewer",
        "好，现在轮到你提问了。你对我们公司或者这个岗位有什么想了解的吗？",
        "qa", 0, offset
    )
    offset += 10

    add_dialogue(
        "candidate",
        "我想了解一下这个岗位主要负责什么方向的智能体开发？是面向内部效率提升还是面向客户的产品？另外团队目前有多少人，技术栈主要是什么？",
        "qa", 0, offset
    )
    offset += 25

    add_dialogue(
        "interviewer",
        "我们主要是做面向企业客户的AI面试助手产品，目前团队有5个人，后端主要用Python和FastAPI，前端用Vue。我们在做语音交互和多模态方面的探索，正好需要你这样有智能体经验的人。",
        "qa", 1, offset
    )
    offset += 20

    add_dialogue(
        "candidate",
        "听起来很有意思，和我之前做的智能体方向比较契合。我还想问一下，公司对技术选型有什么要求吗？比如是否有国产化要求？",
        "qa", 1, offset
    )
    offset += 20

    add_dialogue(
        "interviewer",
        "目前没有硬性的国产化要求，我们主要看技术效果和成本效益。但如果客户有要求，我们会配合适配。",
        "qa", 1, offset
    )
    offset += 15

    record.phase_transitions.append(PhaseTransition(
        from_phase="qa",
        to_phase="closing",
        reason="llm_decision",
        timestamp=base_time + timedelta(seconds=offset)
    ))

    # ========== PHASE 7: CLOSING ==========
    add_dialogue(
        "interviewer",
        "好的，今天的面试就到这里了。感谢你的时间，你的背景和经验都很不错，特别是在智能体平台和银行场景的落地经验。我们会在一周内给你反馈，请保持电话畅通。有任何问题可以随时联系我们HR。",
        "closing", 0, offset
    )
    offset += 20

    add_dialogue(
        "candidate",
        "好的，非常感谢您今天的面试，让我对这个岗位有了更深入的了解。期待您的好消息！",
        "closing", 0, offset
    )
    offset += 10

    # ========== EVALUATION ==========
    record.evaluation = EvaluationReport(
        overall_score=82,
        recommendation="recommend",
        dimensions=[
            EvaluationDimension(
                name="技术能力",
                score=8,
                weight=0.3,
                feedback="候选人具备扎实的AI智能体开发经验，对RAG、大模型微调、提示工程等技术有深入理解和实践经验。在知识库优化和模型微调方面展示了较强的技术能力。"
            ),
            EvaluationDimension(
                name="项目经验",
                score=9,
                weight=0.25,
                feedback="在智能体平台开发和银行场景落地方面有丰富经验，能独立负责核心模块开发和性能优化。项目描述清晰，对技术细节把握准确。"
            ),
            EvaluationDimension(
                name="沟通表达",
                score=8,
                weight=0.15,
                feedback="表达清晰有逻辑，能够准确理解问题并给出结构化的回答。在描述技术方案时能够说明背景、方案和效果。"
            ),
            EvaluationDimension(
                name="学习能力",
                score=8,
                weight=0.15,
                feedback="展现出对新技术的持续学习热情，从传统物联网开发转型到AI智能体领域，说明有较强的学习能力和适应能力。"
            ),
            EvaluationDimension(
                name="文化匹配",
                score=7,
                weight=0.15,
                feedback="注重团队协作和文档化，在意见分歧时能够用数据说话。但年龄稍大，需要关注团队融合情况。"
            )
        ],
        highlights=[
            "智能体平台开发经验丰富，有完整的从0到1经验",
            "银行场景落地经验，熟悉私有化部署和国产化适配",
            "具备模型微调能力，对RAG优化有实战经验",
            "问题解决能力强，能够系统性地分析和解决复杂问题"
        ],
        concerns=[
            "年龄35岁，在技术迭代快的AI领域需要关注持续学习动力",
            "之前主要是乙方项目经验，需要适应产品化开发模式",
            "期望薪资较高(25-40K)，需要评估预算匹配度"
        ],
        summary="陆志鹏具备扎实的AI智能体开发经验，在智能体平台和银行场景落地方面有丰富实践。技术能力和项目经验符合岗位要求，建议进入下一轮面试，重点考察产品思维和团队协作。",
        generated_at=base_time + timedelta(minutes=36)
    )

    # Save the record
    path = storage.save_record(record)
    print(f"Mock interview created successfully!")
    print(f"Session ID: {session_id}")
    print(f"Saved to: {path}")
    print(f"Total dialogues: {len(record.dialogues)}")
    print(f"Overall score: {record.evaluation.overall_score}")
    print(f"Recommendation: {record.evaluation.recommendation}")

    return record

if __name__ == "__main__":
    create_mock_interview()
