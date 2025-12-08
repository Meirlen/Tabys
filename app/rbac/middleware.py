from fastapi import Depends, HTTPException, status
from typing import List, Optional
from app.oauth2 import get_current_admin
from app import models
from .permissions import has_permission, is_read_only, Module, Permission
from .roles import Role


def require_role(*allowed_roles: str):
    """
    Decorator to require specific roles

    Usage:
        @router.get("/volunteers")
        def get_volunteers(admin = Depends(require_role(Role.VOLUNTEER_ADMIN, Role.SUPER_ADMIN))):
            ...
    """
    def role_checker(current_admin: models.Admin = Depends(get_current_admin)):
        admin_role = current_admin.role.value if hasattr(current_admin.role, 'value') else current_admin.role

        if admin_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещен. Требуется одна из ролей: {', '.join(allowed_roles)}"
            )
        return current_admin

    return role_checker


def require_permission(module: str, permission: str):
    """
    Decorator to require specific permission for a module

    Usage:
        @router.post("/volunteers")
        def create_volunteer(
            admin = Depends(require_permission(Module.VOLUNTEERS, Permission.CREATE))
        ):
            ...
    """
    def permission_checker(current_admin: models.Admin = Depends(get_current_admin)):
        admin_role = current_admin.role.value if hasattr(current_admin.role, 'value') else current_admin.role

        if not has_permission(admin_role, module, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"У вас нет прав для выполнения действия '{permission}' в модуле '{module}'"
            )
        return current_admin

    return permission_checker


def require_module_access(module: str, allow_read_only: bool = False):
    """
    Decorator to require access to a specific module

    Args:
        module: Module name (e.g., Module.VOLUNTEERS)
        allow_read_only: If True, allows read-only users. If False, blocks them.

    Usage:
        @router.get("/volunteers")
        def get_volunteers(admin = Depends(require_module_access(Module.VOLUNTEERS, allow_read_only=True))):
            ...
    """
    def module_checker(current_admin: models.Admin = Depends(get_current_admin)):
        admin_role = current_admin.role.value if hasattr(current_admin.role, 'value') else current_admin.role

        # Check if has at least read permission
        if not has_permission(admin_role, module, Permission.READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"У вас нет доступа к модулю '{module}'"
            )

        # If we don't allow read-only and user is read-only, block
        if not allow_read_only and is_read_only(admin_role, module):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"У вас только права на просмотр модуля '{module}'"
            )

        return current_admin

    return module_checker


def block_read_only():
    """
    Decorator to block read-only users (specifically for Government role)

    Usage:
        @router.post("/news")
        def create_news(admin = Depends(block_read_only())):
            ...
    """
    def read_only_blocker(current_admin: models.Admin = Depends(get_current_admin)):
        admin_role = current_admin.role.value if hasattr(current_admin.role, 'value') else current_admin.role

        if admin_role == Role.GOVERNMENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас только права на просмотр. Редактирование запрещено."
            )

        return current_admin

    return read_only_blocker


def get_current_admin_with_module(module: str):
    """
    Get current admin and verify module access

    Usage:
        admin = Depends(get_current_admin_with_module(Module.VOLUNTEERS))
    """
    return require_module_access(module, allow_read_only=True)


def check_admin_permission(admin: models.Admin, module: str, permission: str) -> bool:
    """
    Helper function to check if admin has permission (for use in route logic)

    Args:
        admin: Admin model instance
        module: Module name
        permission: Permission type

    Returns:
        bool: True if admin has permission
    """
    admin_role = admin.role.value if hasattr(admin.role, 'value') else admin.role
    return has_permission(admin_role, module, permission)
