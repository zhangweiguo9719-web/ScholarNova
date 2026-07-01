"""
API 依赖注入

提供通用的依赖注入函数
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> Optional[str]:
    """
    获取当前用户 ID

    从请求头中提取用户 ID，支持匿名访问
    """
    return x_user_id


async def require_user_id(
    user_id: Optional[str] = Depends(get_current_user_id),
) -> str:
    """
    要求用户 ID

    如果没有提供用户 ID，返回 401 错误
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required",
        )
    return user_id
