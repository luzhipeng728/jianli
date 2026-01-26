# Agents Module

This module contains AI agents for various interview-related tasks.

## Controller Agent

The `controller_agent.py` provides an asynchronous monitoring system that oversees interview progress and quality.

### Features

- Asynchronous monitoring of interview quality and progress
- Silent guidance directives sent to interviewer agent
- Automatic detection of when interview should end
- Monitoring of exceptional situations (timeouts, off-topic discussions, etc.)
- Integration with Redis-based state management

### Core Functionality

1. **Progress Monitoring**: Tracks interview duration, question count, and topic coverage
2. **Quality Analysis**: Analyzes conversation quality using LLM to determine if guidance is needed
3. **Directive Generation**: Creates silent instructions for the interviewer agent to adjust direction
4. **End Condition Detection**: Determines optimal interview termination based on:
   - Sufficient assessment (minimum 5 questions)
   - Candidate request to end
   - Time limits (suggests ending after 25 minutes, hard limit at 30 minutes)

### Usage Example

```python
from app.agents import ControllerAgent
from app.models.jd import JobDescription
import asyncio

# Create controller agent for a session
session_id = "interview-session-123"
controller = ControllerAgent(session_id)

# Define callback for when interview should end
async def on_interview_end(reason: str):
    print(f"Interview ended: {reason}")
    # Perform cleanup, notify frontend, etc.

# Start monitoring loop
jd = JobDescription(
    title="Senior Python Developer",
    description="...",
    required_skills=["Python", "FastAPI", "Redis"],
    interview_config=InterviewConfig(
        focus_areas=["Python expertise", "API design", "System architecture"]
    )
)

# Run controller in background
controller_task = asyncio.create_task(
    controller.run_loop(jd, on_end_callback=on_interview_end)
)

# ... interview proceeds ...

# Stop controller when needed
controller.stop()
await controller_task
```

### How It Works

1. **Initialization**: Controller agent is created with a session ID
2. **Monitoring Loop**: Runs every 10 seconds to analyze current state
3. **Decision Making**: Uses LLM to analyze:
   - Current interview progress (time, question count)
   - Conversation history (last 10 messages)
   - Job requirements and focus areas
4. **Action Taking**:
   - Sends guidance directives via Redis command queue
   - Updates interview phase when ending
   - Invokes callbacks for important events

### Integration with State Management

The ControllerAgent integrates with `InterviewStateManager` to:
- Read session context and conversation history
- Push hint commands to guide the interviewer
- Push end interview commands
- Update interview phase transitions

## Evaluation Agent

The `evaluation_agent.py` provides automated evaluation report generation based on interview records.

### Features

- Analyzes interview session data (written tests, voice interviews)
- Evaluates candidates across 5 dimensions:
  - Professional Skills (30%)
  - Communication (20%)
  - Logical Thinking (20%)
  - Learning Ability (15%)
  - Job Fit (15%)
- Generates structured evaluation reports with scores, recommendations, highlights, and concerns

### Usage Example

```python
from app.agents.evaluation_agent import evaluation_agent
from app.services.interview_service import InterviewService
from app.models.jd import JobDescription
from app.models.resume import ResumeData

# Create instances
interview_service = InterviewService()

# Generate evaluation report
evaluation = await interview_service.generate_evaluation_report(
    session_id="session-123",
    jd=job_description,
    resume=resume_data
)

# Access evaluation results
print(f"Overall Score: {evaluation.overall_score}")
print(f"Recommendation: {evaluation.recommendation}")
print(f"Summary: {evaluation.summary}")

for dimension in evaluation.dimensions:
    print(f"{dimension.name}: {dimension.score} (weight: {dimension.weight})")
```

### Evaluation Report Structure

```python
{
  "overall_score": 75,
  "recommendation": "recommend",  # strongly_recommend/recommend/neutral/not_recommend
  "dimensions": [
    {
      "name": "专业能力",
      "score": 80,
      "weight": 0.30,
      "analysis": "技术深度良好，问题解决能力强..."
    },
    # ... more dimensions
  ],
  "highlights": ["技术功底扎实", "沟通清晰"],
  "concerns": ["某些领域经验不足"],
  "summary": "候选人综合素质良好，推荐进入下一轮",
  "detailed_analysis": "详细分析内容...",
  "generated_at": "2026-01-07T10:30:00"
}
```

### Integration with Interview Service

The evaluation agent is integrated into `InterviewService` through the `generate_evaluation_report` method:

```python
async def generate_evaluation_report(
    self,
    session_id: str,
    jd: JobDescription,
    resume: ResumeData
) -> Optional[Evaluation]:
    """Generate and save evaluation report to the session"""
    # This method:
    # 1. Retrieves the interview session
    # 2. Calls evaluation_agent to generate report
    # 3. Saves the evaluation to the session
    # 4. Returns the evaluation
```
