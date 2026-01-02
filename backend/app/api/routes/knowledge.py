import uuid
from fastapi import APIRouter, HTTPException
from app.services.es_client import ESClient
from app.models.chat import KnowledgeItem

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

KNOWLEDGE_INDEX = "knowledge_base"
es_client = ESClient()

@router.post("/import")
async def import_knowledge(items: list[KnowledgeItem]):
    """批量导入知识"""
    for item in items:
        if not item.id:
            item.id = str(uuid.uuid4())
        es_client.index_document(
            KNOWLEDGE_INDEX,
            item.id,
            item.model_dump(mode="json")
        )
    return {"status": "success", "count": len(items)}

@router.get("/list")
async def list_knowledge(page: int = 1, size: int = 20):
    """获取知识列表"""
    query = {
        "query": {"match_all": {}},
        "from": (page - 1) * size,
        "size": size,
        "sort": [{"created_at": "desc"}]
    }
    try:
        result = es_client.search(KNOWLEDGE_INDEX, query)
        items = [hit["_source"] for hit in result["hits"]["hits"]]
        total = result["hits"]["total"]["value"]
        return {"data": items, "total": total, "page": page, "size": size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "size": size}

@router.delete("/{item_id}")
async def delete_knowledge(item_id: str):
    """删除知识条目"""
    try:
        es_client.delete_document(KNOWLEDGE_INDEX, item_id)
        return {"status": "deleted"}
    except Exception:
        raise HTTPException(404, "条目不存在")
