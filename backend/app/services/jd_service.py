import uuid
from datetime import datetime
from app.services.es_client import ESClient
from app.models.jd import JobDescription, JDCreateRequest, JDUpdateRequest

JD_INDEX = "job_descriptions"

# Elasticsearch索引映射配置
JD_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "department": {"type": "keyword"},
            "description": {"type": "text", "analyzer": "standard"},
            "requirements": {"type": "text"},
            "required_skills": {"type": "keyword"},
            "preferred_skills": {"type": "keyword"},
            "interview_config": {
                "properties": {
                    "written_question_count": {"type": "integer"},
                    "voice_max_duration": {"type": "integer"},
                    "focus_areas": {"type": "keyword"},
                    "difficulty": {"type": "keyword"}
                }
            },
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }
}

class JDService:
    def __init__(self):
        self.es_client = ESClient()
        self._ensure_index()

    def _ensure_index(self):
        """确保索引存在"""
        self.es_client.create_index(JD_INDEX, JD_INDEX_MAPPING)

    def create(self, request: JDCreateRequest) -> JobDescription:
        """创建JD"""
        jd_id = str(uuid.uuid4())
        now = datetime.now()

        jd = JobDescription(
            id=jd_id,
            title=request.title,
            department=request.department,
            description=request.description,
            requirements=request.requirements,
            required_skills=request.required_skills,
            preferred_skills=request.preferred_skills,
            interview_config=request.interview_config or {},
            created_at=now,
            updated_at=None
        )

        # 存储到ES
        doc = jd.model_dump(mode="json")
        self.es_client.index_document(JD_INDEX, jd_id, doc)

        return jd

    def get(self, jd_id: str) -> JobDescription | None:
        """获取JD详情"""
        try:
            result = self.es_client.get_document(JD_INDEX, jd_id)
            return JobDescription(**result["_source"])
        except Exception:
            return None

    def list(self, page: int = 1, size: int = 20) -> dict:
        """获取JD列表"""
        query = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }
        result = self.es_client.search(JD_INDEX, query)
        total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
        data = [JobDescription(**hit["_source"]) for hit in result["hits"]["hits"]]
        return {"data": data, "total": total}

    def update(self, jd_id: str, request: JDUpdateRequest) -> JobDescription | None:
        """更新JD"""
        # 获取现有JD
        jd = self.get(jd_id)
        if not jd:
            return None

        # 更新字段
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(jd, key, value)

        # 更新时间戳
        jd.updated_at = datetime.now()

        # 保存到ES
        doc = jd.model_dump(mode="json")
        self.es_client.index_document(JD_INDEX, jd_id, doc)

        return jd

    def delete(self, jd_id: str) -> bool:
        """删除JD"""
        try:
            self.es_client.delete_document(JD_INDEX, jd_id)
            return True
        except Exception:
            return False

    def search_by_title(self, keyword: str, page: int = 1, size: int = 20) -> dict:
        """按标题搜索JD"""
        query = {
            "query": {
                "match": {
                    "title": {
                        "query": keyword,
                        "operator": "and"
                    }
                }
            },
            "from": (page - 1) * size,
            "size": size,
            "sort": [{"created_at": "desc"}]
        }
        result = self.es_client.search(JD_INDEX, query)
        total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
        data = [JobDescription(**hit["_source"]) for hit in result["hits"]["hits"]]
        return {"data": data, "total": total}
