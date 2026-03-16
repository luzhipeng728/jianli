#!/usr/bin/env python3
"""
Elasticsearch索引初始化脚本
用于创建resumes和knowledge_base索引及其映射
"""

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError
import sys


def init_elasticsearch():
    """初始化Elasticsearch索引"""

    # 连接到Elasticsearch
    try:
        es = Elasticsearch(
            hosts=["http://localhost:9200"],
            request_timeout=30,
            verify_certs=False,
            ssl_show_warn=False
        )

        # 测试连接
        info = es.info()
        print(f"成功连接到Elasticsearch")
        print(f"集群名称: {info['cluster_name']}")
        print(f"ES版本: {info['version']['number']}")

    except ESConnectionError as e:
        print(f"错误: 连接Elasticsearch失败 - {e}")
        return False
    except Exception as e:
        print(f"错误: 初始化Elasticsearch客户端失败 - {e}")
        return False

    # 创建resumes索引
    resumes_index = "resumes"
    resumes_mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ik_analyzer": {
                        "type": "standard"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "file_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "file_type": {
                    "type": "keyword"
                },
                "raw_text": {
                    "type": "text",
                    "analyzer": "ik_analyzer"
                },
                "basic_info": {
                    "properties": {
                        "name": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "phone": {
                            "type": "keyword"
                        },
                        "email": {
                            "type": "keyword"
                        },
                        "age": {
                            "type": "integer"
                        },
                        "gender": {
                            "type": "keyword"
                        }
                    }
                },
                "education": {
                    "type": "nested",
                    "properties": {
                        "school": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "degree": {
                            "type": "keyword"
                        },
                        "major": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "start_date": {
                            "type": "keyword"
                        },
                        "end_date": {
                            "type": "keyword"
                        }
                    }
                },
                "experience": {
                    "type": "nested",
                    "properties": {
                        "company": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "title": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "start_date": {
                            "type": "keyword"
                        },
                        "end_date": {
                            "type": "keyword"
                        },
                        "duties": {
                            "type": "text",
                            "analyzer": "ik_analyzer"
                        }
                    }
                },
                "skills": {
                    "properties": {
                        "hard_skills": {
                            "type": "keyword"
                        },
                        "soft_skills": {
                            "type": "keyword"
                        }
                    }
                },
                "job_intention": {
                    "properties": {
                        "position": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "salary_min": {
                            "type": "integer"
                        },
                        "salary_max": {
                            "type": "integer"
                        },
                        "location": {
                            "type": "keyword"
                        }
                    }
                },
                "warnings": {
                    "type": "nested",
                    "properties": {
                        "type": {
                            "type": "keyword"
                        },
                        "message": {
                            "type": "text"
                        }
                    }
                },
                "match_score": {
                    "type": "float"
                },
                "created_at": {
                    "type": "date"
                },
                "updated_at": {
                    "type": "date"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    try:
        # 检查索引是否存在，如果存在则删除
        if es.indices.exists(index=resumes_index):
            es.indices.delete(index=resumes_index)
            print(f"已删除现有的 {resumes_index} 索引")

        # 创建索引
        es.indices.create(index=resumes_index, body=resumes_mapping)
        print(f"成功创建 {resumes_index} 索引")

    except Exception as e:
        print(f"错误: 创建 {resumes_index} 索引失败 - {e}")
        return False

    # 创建knowledge_base索引
    kb_index = "knowledge_base"
    kb_mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ik_analyzer": {
                        "type": "standard"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "title": {
                    "type": "text",
                    "analyzer": "ik_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "content": {
                    "type": "text",
                    "analyzer": "ik_analyzer"
                },
                "category": {
                    "type": "keyword"
                },
                "tags": {
                    "type": "keyword"
                },
                "source": {
                    "type": "keyword"
                },
                "created_at": {
                    "type": "date"
                }
            }
        }
    }

    try:
        # 检查索引是否存在，如果存在则删除
        if es.indices.exists(index=kb_index):
            es.indices.delete(index=kb_index)
            print(f"已删除现有的 {kb_index} 索引")

        # 创建索引
        es.indices.create(index=kb_index, body=kb_mapping)
        print(f"成功创建 {kb_index} 索引")

    except Exception as e:
        print(f"错误: 创建 {kb_index} 索引失败 - {e}")
        return False

    # 验证索引创建
    print("\n索引列表:")
    for index_name in [resumes_index, kb_index]:
        if es.indices.exists(index=index_name):
            index_info = es.indices.get(index=index_name)
            mapping = index_info[index_name]["mappings"]
            field_count = len(mapping.get("properties", {}))
            print(f"  - {index_name}: 已创建 (字段数: {field_count})")
        else:
            print(f"  - {index_name}: 未找到")

    print("\n所有索引初始化完成!")
    return True


if __name__ == "__main__":
    success = init_elasticsearch()
    sys.exit(0 if success else 1)
