from typing import Dict, List, Set
from .roles import Role

# Module names
class Module:
    VOLUNTEERS = "volunteers"
    VACANCIES = "vacancies"
    LEISURE = "leisure"
    PROJECTS = "projects"
    EVENTS = "events"
    NEWS = "news"
    USERS = "users"
    COURSES = "courses"
    CERTIFICATES = "certificates"
    EXPERTS = "experts"
    RESUMES = "resumes"


# Permission types
class Permission:
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# Role → Module permissions mapping
ROLE_PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
    Role.CLIENT: {
        # Clients have no admin panel access
    },

    Role.VOLUNTEER_ADMIN: {
        Module.VOLUNTEERS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
    },

    Role.MSB: {
        Module.VACANCIES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.LEISURE: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
    },

    Role.NPO: {
        Module.PROJECTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.EVENTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
    },

    Role.GOVERNMENT: {
        # Read-only access to everything
        Module.VOLUNTEERS: {Permission.READ},
        Module.VACANCIES: {Permission.READ},
        Module.LEISURE: {Permission.READ},
        Module.PROJECTS: {Permission.READ},
        Module.EVENTS: {Permission.READ},
        Module.NEWS: {Permission.READ},
        Module.USERS: {Permission.READ},
        Module.COURSES: {Permission.READ},
        Module.CERTIFICATES: {Permission.READ},
        Module.EXPERTS: {Permission.READ},
        Module.RESUMES: {Permission.READ},
    },

    Role.ADMINISTRATOR: {
        Module.NEWS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.USERS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.VOLUNTEERS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.VACANCIES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.LEISURE: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.PROJECTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.EVENTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.COURSES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.CERTIFICATES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.EXPERTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.RESUMES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
    },

    Role.SUPER_ADMIN: {
        # Full access to everything
        Module.VOLUNTEERS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.VACANCIES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.LEISURE: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.PROJECTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.EVENTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.NEWS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.USERS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.COURSES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.CERTIFICATES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.EXPERTS: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
        Module.RESUMES: {Permission.READ, Permission.CREATE, Permission.UPDATE, Permission.DELETE},
    },
}


def has_permission(role: str, module: str, permission: str) -> bool:
    """
    Check if a role has a specific permission for a module

    Args:
        role: User's role (e.g., "volunteer_admin")
        module: Module name (e.g., "volunteers")
        permission: Permission type (e.g., "create")

    Returns:
        bool: True if role has permission, False otherwise
    """
    if role not in ROLE_PERMISSIONS:
        return False

    module_permissions = ROLE_PERMISSIONS[role].get(module, set())
    return permission in module_permissions


def get_accessible_modules(role: str) -> List[str]:
    """
    Get list of modules a role can access

    Args:
        role: User's role

    Returns:
        List of module names the role can access
    """
    if role not in ROLE_PERMISSIONS:
        return []

    return list(ROLE_PERMISSIONS[role].keys())


def is_read_only(role: str, module: str) -> bool:
    """
    Check if role has only read access to a module

    Args:
        role: User's role
        module: Module name

    Returns:
        bool: True if only read permission, False otherwise
    """
    if role not in ROLE_PERMISSIONS:
        return False

    module_permissions = ROLE_PERMISSIONS[role].get(module, set())

    # Has read but no write permissions
    return (Permission.READ in module_permissions and
            not any(p in module_permissions for p in [Permission.CREATE, Permission.UPDATE, Permission.DELETE]))
