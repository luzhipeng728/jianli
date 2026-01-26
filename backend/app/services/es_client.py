from elasticsearch import Elasticsearch
from app.config import get_settings

class ESClient:
    def __init__(self):
        settings = get_settings()
        self.client = Elasticsearch(
            hosts=[f"http://{settings.es_host}:{settings.es_port}"]
        )

    def ping(self) -> bool:
        return self.client.ping()

    def create_index(self, index_name: str, body: dict) -> bool:
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=body)
        return True

    def delete_index(self, index_name: str) -> bool:
        if self.client.indices.exists(index=index_name):
            self.client.indices.delete(index=index_name)
        return True

    def index_document(self, index_name: str, doc_id: str, document: dict):
        return self.client.index(index=index_name, id=doc_id, document=document)

    def get_document(self, index_name: str, doc_id: str):
        return self.client.get(index=index_name, id=doc_id)

    def search(self, index_name: str, query: dict):
        return self.client.search(index=index_name, body=query)

    def delete_document(self, index_name: str, doc_id: str, refresh: bool = False):
        return self.client.delete(index=index_name, id=doc_id, refresh=refresh)

    def refresh_index(self, index_name: str):
        """强制刷新索引，使所有更改立即可见"""
        return self.client.indices.refresh(index=index_name)
