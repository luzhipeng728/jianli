from enum import Enum
from pydantic import BaseModel
from typing import Dict

class InterviewPhase(str, Enum):
    OPENING = "opening"
    SELF_INTRO = "self_intro"
    PROJECT_DEEP = "project_deep"
    TECH_ASSESS = "tech_assess"
    BEHAVIORAL = "behavioral"
    QA = "qa"
    CLOSING = "closing"

class PhaseConfig(BaseModel):
    """Configuration for each interview phase"""
    phase: InterviewPhase
    order: int
    min_rounds: int
    max_rounds: int
    description: str
    prompt_hint: str

PHASE_CONFIGS: Dict[InterviewPhase, PhaseConfig] = {
    InterviewPhase.OPENING: PhaseConfig(
        phase=InterviewPhase.OPENING,
        order=1,
        min_rounds=1,
        max_rounds=1,
        description="开场寒暄",
        prompt_hint="友好问候，让候选人放松"
    ),
    InterviewPhase.SELF_INTRO: PhaseConfig(
        phase=InterviewPhase.SELF_INTRO,
        order=2,
        min_rounds=1,
        max_rounds=2,
        description="自我介绍",
        prompt_hint="请候选人介绍自己，可以适当追问"
    ),
    InterviewPhase.PROJECT_DEEP: PhaseConfig(
        phase=InterviewPhase.PROJECT_DEEP,
        order=3,
        min_rounds=3,
        max_rounds=5,
        description="项目深挖",
        prompt_hint="深入了解候选人的项目经验，追问技术细节和个人贡献"
    ),
    InterviewPhase.TECH_ASSESS: PhaseConfig(
        phase=InterviewPhase.TECH_ASSESS,
        order=4,
        min_rounds=3,
        max_rounds=5,
        description="技术评估",
        prompt_hint="考察岗位相关的技术能力，可以出具体问题"
    ),
    InterviewPhase.BEHAVIORAL: PhaseConfig(
        phase=InterviewPhase.BEHAVIORAL,
        order=5,
        min_rounds=2,
        max_rounds=3,
        description="行为面试",
        prompt_hint="了解候选人的软技能、团队协作、问题解决能力"
    ),
    InterviewPhase.QA: PhaseConfig(
        phase=InterviewPhase.QA,
        order=6,
        min_rounds=1,
        max_rounds=2,
        description="候选人提问",
        prompt_hint="让候选人提问，耐心解答"
    ),
    InterviewPhase.CLOSING: PhaseConfig(
        phase=InterviewPhase.CLOSING,
        order=7,
        min_rounds=1,
        max_rounds=1,
        description="结束语",
        prompt_hint="感谢候选人，说明后续流程"
    ),
}

def get_next_phase(current: InterviewPhase) -> InterviewPhase | None:
    """Get the next phase in order, None if at closing"""
    current_order = PHASE_CONFIGS[current].order
    for phase, config in PHASE_CONFIGS.items():
        if config.order == current_order + 1:
            return phase
    return None
