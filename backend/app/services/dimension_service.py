"""
维度管理服务

提供维度的增删改查功能，数据存储在JSON文件中
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal, List, Dict
from app.models.dimension import (
    AnalysisDimension,
    DEFAULT_SCREENING_DIMENSIONS,
    DEFAULT_EVALUATION_DIMENSIONS,
    DEFAULT_PARSING_DIMENSIONS
)


class DimensionService:
    """维度管理服务"""

    def __init__(self, data_dir: str = "/data/dimensions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "dimensions.json"
        self._ensure_defaults()

    def _ensure_defaults(self):
        """确保默认维度存在"""
        if not self.data_file.exists():
            # 初始化默认维度
            dimensions = []

            # 添加筛选维度
            for d in DEFAULT_SCREENING_DIMENSIONS:
                dim = AnalysisDimension(
                    id=str(uuid.uuid4()),
                    **d
                )
                dimensions.append(dim.model_dump(mode="json"))

            # 添加评估维度
            for d in DEFAULT_EVALUATION_DIMENSIONS:
                dim = AnalysisDimension(
                    id=str(uuid.uuid4()),
                    **d
                )
                dimensions.append(dim.model_dump(mode="json"))

            # 添加解析维度
            for d in DEFAULT_PARSING_DIMENSIONS:
                dim = AnalysisDimension(
                    id=str(uuid.uuid4()),
                    **d
                )
                dimensions.append(dim.model_dump(mode="json"))

            self._save_all(dimensions)

    def _load_all(self) -> List[dict]:
        """加载所有维度"""
        if not self.data_file.exists():
            return []
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_all(self, dimensions: List[dict]):
        """保存所有维度"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(dimensions, f, ensure_ascii=False, indent=2)

    def list(
        self,
        dim_type: Optional[Literal["screening", "evaluation", "parsing"]] = None,
        enabled_only: bool = False
    ) -> List[AnalysisDimension]:
        """获取维度列表

        Args:
            dim_type: 维度类型筛选
            enabled_only: 只返回启用的维度
        """
        dimensions = self._load_all()
        result = []

        for d in dimensions:
            if dim_type and d.get("type") != dim_type:
                continue
            if enabled_only and not d.get("is_enabled", True):
                continue
            result.append(AnalysisDimension(**d))

        return result

    def get(self, dimension_id: str) -> Optional[AnalysisDimension]:
        """获取单个维度"""
        dimensions = self._load_all()
        for d in dimensions:
            if d.get("id") == dimension_id:
                return AnalysisDimension(**d)
        return None

    def create(
        self,
        name: str,
        dim_type: Literal["screening", "evaluation", "parsing"],
        weight: float = 0.0,
        description: str = "",
        prompt_hint: str = ""
    ) -> AnalysisDimension:
        """创建新维度"""
        dimensions = self._load_all()

        new_dim = AnalysisDimension(
            id=str(uuid.uuid4()),
            name=name,
            type=dim_type,
            weight=weight,
            description=description,
            prompt_hint=prompt_hint,
            is_default=False,
            is_enabled=True
        )

        dimensions.append(new_dim.model_dump(mode="json"))
        self._save_all(dimensions)

        return new_dim

    def update(
        self,
        dimension_id: str,
        name: Optional[str] = None,
        weight: Optional[float] = None,
        description: Optional[str] = None,
        prompt_hint: Optional[str] = None,
        is_enabled: Optional[bool] = None
    ) -> Optional[AnalysisDimension]:
        """更新维度"""
        dimensions = self._load_all()

        for i, d in enumerate(dimensions):
            if d.get("id") == dimension_id:
                if name is not None:
                    d["name"] = name
                if weight is not None:
                    d["weight"] = weight
                if description is not None:
                    d["description"] = description
                if prompt_hint is not None:
                    d["prompt_hint"] = prompt_hint
                if is_enabled is not None:
                    d["is_enabled"] = is_enabled
                d["updated_at"] = datetime.now().isoformat()

                dimensions[i] = d
                self._save_all(dimensions)
                return AnalysisDimension(**d)

        return None

    def delete(self, dimension_id: str) -> bool:
        """删除维度（只能删除非默认维度）"""
        dimensions = self._load_all()

        for i, d in enumerate(dimensions):
            if d.get("id") == dimension_id:
                if d.get("is_default"):
                    raise ValueError("不能删除系统默认维度")
                dimensions.pop(i)
                self._save_all(dimensions)
                return True

        return False

    def reset_defaults(self):
        """重置为默认维度"""
        # 保留用户创建的维度
        dimensions = self._load_all()
        custom_dims = [d for d in dimensions if not d.get("is_default")]

        # 重新创建默认维度
        default_dims = []
        for d in DEFAULT_SCREENING_DIMENSIONS + DEFAULT_EVALUATION_DIMENSIONS + DEFAULT_PARSING_DIMENSIONS:
            dim = AnalysisDimension(
                id=str(uuid.uuid4()),
                **d
            )
            default_dims.append(dim.model_dump(mode="json"))

        self._save_all(default_dims + custom_dims)

    def get_screening_weights(self) -> Dict[str, float]:
        """获取筛选维度权重（用于简历匹配）"""
        dims = self.list(dim_type="screening", enabled_only=True)
        weights = {}
        for d in dims:
            # 使用英文key便于代码使用
            key = self._name_to_key(d.name)
            weights[key] = d.weight
        return weights

    def get_screening_prompts(self) -> List[dict]:
        """获取筛选维度的提示词（用于AI分析）"""
        dims = self.list(dim_type="screening", enabled_only=True)
        return [
            {
                "name": d.name,
                "weight": d.weight,
                "description": d.description,
                "prompt_hint": d.prompt_hint
            }
            for d in dims
        ]

    def get_evaluation_dimensions(self) -> List[dict]:
        """获取面试评估维度（用于评估Agent）"""
        dims = self.list(dim_type="evaluation", enabled_only=True)
        return [
            {
                "name": d.name,
                "weight": d.weight,
                "description": d.description
            }
            for d in dims
        ]

    def get_parsing_prompts(self) -> List[dict]:
        """获取简历解析关注点（用于解析提示词）"""
        dims = self.list(dim_type="parsing", enabled_only=True)
        return [
            {
                "name": d.name,
                "description": d.description,
                "prompt_hint": d.prompt_hint
            }
            for d in dims
        ]

    def _name_to_key(self, name: str) -> str:
        """将中文名转换为英文key"""
        mapping = {
            "技能匹配": "skill",
            "工作经验": "experience",
            "教育背景": "education",
            "求职意向": "intention"
        }
        return mapping.get(name, name.lower().replace(" ", "_"))


# 单例
_dimension_service: Optional[DimensionService] = None


def get_dimension_service() -> DimensionService:
    """获取维度服务单例"""
    global _dimension_service
    if _dimension_service is None:
        _dimension_service = DimensionService()
    return _dimension_service
