from enum import Enum

class Role(str, Enum):
    """Role enumeration matching database values"""
    CLIENT = "client"
    VOLUNTEER_ADMIN = "volunteer_admin"
    MSB = "msb"
    NPO = "npo"
    GOVERNMENT = "government"
    ADMINISTRATOR = "administrator"
    SUPER_ADMIN = "super_admin"


# Role hierarchy (higher number = more privileges)
ROLE_HIERARCHY = {
    Role.CLIENT: 0,
    Role.VOLUNTEER_ADMIN: 1,
    Role.MSB: 1,
    Role.NPO: 1,
    Role.GOVERNMENT: 2,
    Role.ADMINISTRATOR: 3,
    Role.SUPER_ADMIN: 4,
}


def has_higher_or_equal_privilege(user_role: str, required_role: str) -> bool:
    """Check if user role has higher or equal privilege than required role"""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level
