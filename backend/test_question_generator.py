"""测试笔试题目生成Agent"""

import asyncio
from app.agents.question_generator import question_generator
from app.models.jd import JobDescription, InterviewConfig
from app.models.resume import ResumeData, BasicInfo, Skills, Experience

async def test_question_generation():
    """测试题目生成功能"""

    # 创建测试用的JD
    jd = JobDescription(
        id="test-jd-1",
        title="Python后端开发工程师",
        department="技术部",
        description="负责公司核心业务系统的后端开发，使用FastAPI框架构建高性能API服务",
        requirements=[
            "3年以上Python开发经验",
            "熟悉FastAPI或Django框架",
            "熟悉MySQL和Redis",
            "有RESTful API设计经验"
        ],
        required_skills=["Python", "FastAPI", "MySQL", "Redis"],
        preferred_skills=["Docker", "Kubernetes", "微服务"],
        interview_config=InterviewConfig(
            written_question_count=5,
            difficulty="medium",
            focus_areas=["Python基础", "FastAPI框架", "数据库优化"]
        )
    )

    # 创建测试用的简历
    resume = ResumeData(
        id="test-resume-1",
        file_name="test.pdf",
        basic_info=BasicInfo(
            name="张三",
            email="zhangsan@example.com",
            phone="13800138000"
        ),
        skills=Skills(
            hard_skills=["Python", "FastAPI", "Django", "MySQL", "Redis", "Docker"],
            soft_skills=["团队协作", "沟通能力", "问题解决"]
        ),
        experience=[
            Experience(
                company="某互联网公司",
                title="Python开发工程师",
                start_date="2020-01",
                end_date="2023-12",
                duties="负责公司电商平台后端开发，使用Django框架开发RESTful API，优化MySQL查询性能，引入Redis缓存提升系统响应速度"
            )
        ]
    )

    print("开始生成笔试题目...")
    print(f"JD: {jd.title}")
    print(f"候选人: {resume.basic_info.name}")
    print("-" * 80)

    try:
        # 生成5道题目
        questions = await question_generator.generate_questions(
            jd=jd,
            resume=resume,
            count=5
        )

        print(f"\n成功生成 {len(questions)} 道题目:\n")

        for i, q in enumerate(questions, 1):
            print(f"题目 {i} [{q.type.value}] ({q.points}分)")
            print(f"  内容: {q.content}")
            print(f"  选项:")
            for option in q.options:
                print(f"    {option}")
            print(f"  正确答案: {q.correct_answer}")
            print(f"  解析: {q.explanation}")
            print()

        print("-" * 80)
        print("测试成功!")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_question_generation())
