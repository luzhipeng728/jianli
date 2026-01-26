# 笔试题目生成 API 使用指南

## API 端点

### 生成笔试题目
**POST** `/api/interview/generate-questions`

根据职位描述(JD)和候选人简历生成个性化的笔试题目。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| resume_id | string | 是 | - | 简历ID |
| jd_id | string | 是 | - | 职位描述ID |
| count | integer | 否 | 5 | 生成题目数量 |

#### 请求示例

```bash
curl -X POST "http://localhost:8000/api/interview/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "550e8400-e29b-41d4-a716-446655440000",
    "jd_id": "660e8400-e29b-41d4-a716-446655440001",
    "count": 5
  }'
```

```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "jd_id": "660e8400-e29b-41d4-a716-446655440001",
  "count": 5
}
```

#### 成功响应

**状态码**: 200 OK

```json
{
  "status": "success",
  "data": [
    {
      "id": "a1b2c3d4-e5f6-4a5b-8c7d-9e0f1a2b3c4d",
      "type": "single",
      "content": "在FastAPI中，以下哪个装饰器用于定义POST请求的路由？",
      "options": [
        "A. @app.get()",
        "B. @app.post()",
        "C. @app.put()",
        "D. @app.route()"
      ],
      "correct_answer": "B",
      "explanation": "@app.post()装饰器用于定义处理POST请求的路由，FastAPI使用不同的装饰器来区分HTTP方法。",
      "points": 10
    },
    {
      "id": "b2c3d4e5-f6a7-4b5c-8d7e-9f0a1b2c3d4e",
      "type": "multiple",
      "content": "以下哪些是Python中的数据库ORM框架？（多选）",
      "options": [
        "A. SQLAlchemy",
        "B. Django ORM",
        "C. Peewee",
        "D. React"
      ],
      "correct_answer": ["A", "B", "C"],
      "explanation": "SQLAlchemy、Django ORM和Peewee都是Python的ORM框架，而React是JavaScript前端框架。",
      "points": 15
    },
    {
      "id": "c3d4e5f6-a7b8-4c5d-8e7f-9a0b1c2d3e4f",
      "type": "judgment",
      "content": "在MySQL中，索引会加快查询速度但会降低写入性能。",
      "options": [
        "A. 正确",
        "B. 错误"
      ],
      "correct_answer": "A",
      "explanation": "索引通过建立数据结构来加快查询，但在插入、更新、删除数据时需要维护索引，因此会影响写入性能。",
      "points": 10
    }
  ]
}
```

#### 错误响应

**JD不存在** - 状态码: 404

```json
{
  "detail": "JD不存在"
}
```

**简历不存在** - 状态码: 404

```json
{
  "detail": "简历不存在"
}
```

**生成失败** - 状态码: 500

```json
{
  "detail": "生成题目失败: [错误详情]"
}
```

## 题目类型说明

### 1. 单选题 (single)
- `type`: "single"
- `correct_answer`: 单个选项，如 "A"
- `options`: 通常包含4个选项（A-D）

### 2. 多选题 (multiple)
- `type`: "multiple"
- `correct_answer`: 多个选项数组，如 ["A", "B", "C"]
- `options`: 通常包含4个选项（A-D）

### 3. 判断题 (judgment)
- `type`: "judgment"
- `correct_answer`: "A" (正确) 或 "B" (错误)
- `options`: 固定为 ["A. 正确", "B. 错误"]

## 集成示例

### JavaScript/TypeScript (前端)

```typescript
interface GenerateQuestionsRequest {
  resume_id: string;
  jd_id: string;
  count?: number;
}

interface Question {
  id: string;
  type: 'single' | 'multiple' | 'judgment';
  content: string;
  options: string[];
  correct_answer: string | string[];
  explanation: string;
  points: number;
}

async function generateQuestions(
  request: GenerateQuestionsRequest
): Promise<Question[]> {
  const response = await fetch('/api/interview/generate-questions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`生成题目失败: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

// 使用示例
const questions = await generateQuestions({
  resume_id: 'resume-123',
  jd_id: 'jd-456',
  count: 5,
});

questions.forEach((q, index) => {
  console.log(`题目 ${index + 1}: ${q.content}`);
  console.log(`类型: ${q.type}`);
  console.log(`答案: ${q.correct_answer}`);
});
```

### Python (后端服务调用)

```python
import httpx
from typing import List, Dict

async def generate_questions(
    resume_id: str,
    jd_id: str,
    count: int = 5
) -> List[Dict]:
    """调用API生成笔试题目"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8000/api/interview/generate-questions',
            json={
                'resume_id': resume_id,
                'jd_id': jd_id,
                'count': count
            }
        )
        response.raise_for_status()
        result = response.json()
        return result['data']

# 使用示例
questions = await generate_questions(
    resume_id='resume-123',
    jd_id='jd-456',
    count=5
)

for i, q in enumerate(questions, 1):
    print(f"题目 {i}: {q['content']}")
    print(f"类型: {q['type']}")
    print(f"答案: {q['correct_answer']}")
```

### Python (直接调用Agent)

```python
from app.agents.question_generator import question_generator
from app.services.jd_service import JDService
from app.services.resume_parser import ResumeParser

async def generate_questions_direct(
    resume_id: str,
    jd_id: str,
    count: int = 5
):
    """直接调用Agent生成题目"""
    # 加载数据
    jd_service = JDService()
    resume_parser = ResumeParser()
    
    jd = jd_service.get(jd_id)
    resume = resume_parser.get_resume(resume_id)
    
    if not jd or not resume:
        raise ValueError("JD或简历不存在")
    
    # 生成题目
    questions = await question_generator.generate_questions(
        jd=jd,
        resume=resume,
        count=count
    )
    
    return questions

# 使用示例
questions = await generate_questions_direct(
    resume_id='resume-123',
    jd_id='jd-456',
    count=5
)
```

## 最佳实践

### 1. 题目数量建议
- 初级岗位: 3-5道题
- 中级岗位: 5-8道题
- 高级岗位: 8-10道题

### 2. 题型分布建议
- 单选题: 50-60%
- 多选题: 20-30%
- 判断题: 20-30%

### 3. 错误处理
```python
try:
    questions = await generate_questions(resume_id, jd_id, count)
except HTTPException as e:
    if e.status_code == 404:
        print("JD或简历不存在")
    elif e.status_code == 500:
        print(f"生成失败: {e.detail}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 4. 缓存策略
建议对同一JD和简历的题目进行缓存（如Redis），避免重复生成：

```python
import hashlib
import json

def get_cache_key(resume_id: str, jd_id: str, count: int) -> str:
    """生成缓存键"""
    data = f"{resume_id}:{jd_id}:{count}"
    return f"questions:{hashlib.md5(data.encode()).hexdigest()}"

# 先查缓存
cache_key = get_cache_key(resume_id, jd_id, count)
cached_questions = redis_client.get(cache_key)

if cached_questions:
    questions = json.loads(cached_questions)
else:
    questions = await generate_questions(resume_id, jd_id, count)
    # 缓存1小时
    redis_client.setex(cache_key, 3600, json.dumps(questions))
```

## 注意事项

1. **API限流**: 建议对该接口进行限流，避免频繁调用导致LLM成本过高
2. **数据验证**: 确保传入的resume_id和jd_id存在且有效
3. **题目审核**: 生成的题目建议人工审核后再用于正式面试
4. **题目多样性**: 同一JD可以多次生成不同的题目，提供更多选择
5. **性能考虑**: LLM调用可能需要5-15秒，建议使用异步处理或后台任务

