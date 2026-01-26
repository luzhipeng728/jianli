"""
分析维度管理 API

提供分析维度的增删改查功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal
from app.services.dimension_service import get_dimension_service
from app.models.dimension import (
    AnalysisDimension,
    DimensionCreateRequest,
    DimensionUpdateRequest
)

router = APIRouter(prefix="/api/dimension", tags=["维度管理"])

dimension_service = get_dimension_service()


@router.get("")
async def list_dimensions(
    type: Optional[Literal["screening", "evaluation", "parsing"]] = Query(
        None, description="维度类型：screening-筛选, evaluation-评估, parsing-解析"
    ),
    enabled_only: bool = Query(False, description="只返回启用的维度")
) -> dict:
    """获取维度列表

    Args:
        type: 维度类型筛选
        enabled_only: 只返回启用的维度

    Returns:
        维度列表
    """
    dimensions = dimension_service.list(dim_type=type, enabled_only=enabled_only)
    return {
        "status": "success",
        "data": [d.model_dump(mode="json") for d in dimensions]
    }


@router.get("/{dimension_id}")
async def get_dimension(dimension_id: str) -> dict:
    """获取单个维度详情

    Args:
        dimension_id: 维度ID

    Returns:
        维度详情
    """
    dimension = dimension_service.get(dimension_id)
    if not dimension:
        raise HTTPException(404, "维度不存在")

    return {
        "status": "success",
        "data": dimension.model_dump(mode="json")
    }


@router.post("")
async def create_dimension(request: DimensionCreateRequest) -> dict:
    """创建新维度

    Args:
        request: 创建请求

    Returns:
        创建的维度
    """
    dimension = dimension_service.create(
        name=request.name,
        dim_type=request.type,
        weight=request.weight,
        description=request.description,
        prompt_hint=request.prompt_hint
    )

    return {
        "status": "success",
        "data": dimension.model_dump(mode="json")
    }


@router.put("/{dimension_id}")
async def update_dimension(
    dimension_id: str,
    request: DimensionUpdateRequest
) -> dict:
    """更新维度

    Args:
        dimension_id: 维度ID
        request: 更新请求

    Returns:
        更新后的维度
    """
    dimension = dimension_service.update(
        dimension_id=dimension_id,
        name=request.name,
        weight=request.weight,
        description=request.description,
        prompt_hint=request.prompt_hint,
        is_enabled=request.is_enabled
    )

    if not dimension:
        raise HTTPException(404, "维度不存在")

    return {
        "status": "success",
        "data": dimension.model_dump(mode="json")
    }


@router.delete("/{dimension_id}")
async def delete_dimension(dimension_id: str) -> dict:
    """删除维度（只能删除用户创建的维度，不能删除系统默认维度）

    Args:
        dimension_id: 维度ID

    Returns:
        删除结果
    """
    try:
        success = dimension_service.delete(dimension_id)
        if not success:
            raise HTTPException(404, "维度不存在")

        return {
            "status": "success",
            "message": "维度已删除"
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/reset")
async def reset_dimensions() -> dict:
    """重置为默认维度（保留用户创建的维度）

    Returns:
        重置结果
    """
    dimension_service.reset_defaults()
    return {
        "status": "success",
        "message": "已重置为默认维度"
    }


@router.get("/config/screening")
async def get_screening_config() -> dict:
    """获取筛选维度配置（用于简历匹配）

    Returns:
        筛选维度的权重和提示词
    """
    return {
        "status": "success",
        "data": {
            "weights": dimension_service.get_screening_weights(),
            "prompts": dimension_service.get_screening_prompts()
        }
    }


@router.get("/config/evaluation")
async def get_evaluation_config() -> dict:
    """获取评估维度配置（用于面试评估）

    Returns:
        评估维度列表
    """
    return {
        "status": "success",
        "data": dimension_service.get_evaluation_dimensions()
    }


@router.get("/config/parsing")
async def get_parsing_config() -> dict:
    """获取解析关注点配置（用于简历解析）

    Returns:
        解析关注点列表
    """
    return {
        "status": "success",
        "data": dimension_service.get_parsing_prompts()
    }
