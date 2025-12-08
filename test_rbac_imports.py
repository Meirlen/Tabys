#!/usr/bin/env python3
"""
Test script to verify RBAC system is properly integrated
Run this to check if all imports work correctly
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all RBAC imports"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║               RBAC System Import Test                              ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    errors = []
    success = []

    # Test 1: Import models
    print("Testing models.py imports...")
    try:
        from app import models
        if hasattr(models, 'RoleEnum'):
            print("  ✓ RoleEnum found in models")
            print(f"    Available roles: {[r.value for r in models.RoleEnum]}")
            success.append("models.RoleEnum")
        else:
            errors.append("RoleEnum not found in models.py")
            print("  ✗ RoleEnum not found in models")
    except Exception as e:
        errors.append(f"Failed to import models: {e}")
        print(f"  ✗ Error: {e}")

    print()

    # Test 2: Import schemas
    print("Testing schemas.py imports...")
    try:
        from app import schemas
        if hasattr(schemas, 'RoleEnum'):
            print("  ✓ RoleEnum found in schemas")
            print(f"    Available roles: {[r.value for r in schemas.RoleEnum]}")
            success.append("schemas.RoleEnum")
        else:
            errors.append("RoleEnum not found in schemas.py")
            print("  ✗ RoleEnum not found in schemas")
    except Exception as e:
        errors.append(f"Failed to import schemas: {e}")
        print(f"  ✗ Error: {e}")

    print()

    # Test 3: Import RBAC roles
    print("Testing app.rbac.roles...")
    try:
        from app.rbac import Role, ROLE_HIERARCHY
        print("  ✓ Role enum imported")
        print(f"    Available roles: {[r.value for r in Role]}")
        print(f"    Role hierarchy: {ROLE_HIERARCHY}")
        success.append("rbac.Role")
    except Exception as e:
        errors.append(f"Failed to import rbac.roles: {e}")
        print(f"  ✗ Error: {e}")

    print()

    # Test 4: Import RBAC permissions
    print("Testing app.rbac.permissions...")
    try:
        from app.rbac import Module, Permission, ROLE_PERMISSIONS, has_permission
        print("  ✓ Permission system imported")
        print(f"    Available modules: {[attr for attr in dir(Module) if not attr.startswith('_')]}")
        print(f"    Permission types: {[attr for attr in dir(Permission) if not attr.startswith('_')]}")

        # Test permission check
        test_result = has_permission("volunteer_admin", "volunteers", "read")
        print(f"    Test: volunteer_admin can read volunteers? {test_result}")
        success.append("rbac.permissions")
    except Exception as e:
        errors.append(f"Failed to import rbac.permissions: {e}")
        print(f"  ✗ Error: {e}")

    print()

    # Test 5: Import RBAC middleware
    print("Testing app.rbac.middleware...")
    try:
        from app.rbac import (
            require_role,
            require_permission,
            require_module_access,
            block_read_only,
            check_admin_permission
        )
        print("  ✓ Middleware decorators imported")
        print("    Available decorators:")
        print("      - require_role")
        print("      - require_permission")
        print("      - require_module_access")
        print("      - block_read_only")
        print("      - check_admin_permission")
        success.append("rbac.middleware")
    except Exception as e:
        errors.append(f"Failed to import rbac.middleware: {e}")
        print(f"  ✗ Error: {e}")

    print()

    # Test 6: Test permission matrix
    print("Testing permission matrix...")
    try:
        from app.rbac import has_permission, Module, Permission

        test_cases = [
            ("volunteer_admin", Module.VOLUNTEERS, Permission.READ, True),
            ("volunteer_admin", Module.VACANCIES, Permission.READ, False),
            ("msb", Module.VACANCIES, Permission.CREATE, True),
            ("government", Module.NEWS, Permission.READ, True),
            ("government", Module.NEWS, Permission.CREATE, False),
            ("super_admin", Module.VOLUNTEERS, Permission.DELETE, True),
        ]

        all_passed = True
        for role, module, perm, expected in test_cases:
            result = has_permission(role, module, perm)
            status = "✓" if result == expected else "✗"
            if result != expected:
                all_passed = False
            print(f"  {status} {role} → {module}.{perm}: {result} (expected: {expected})")

        if all_passed:
            success.append("permission_matrix")
        else:
            errors.append("Some permission checks failed")

    except Exception as e:
        errors.append(f"Failed to test permissions: {e}")
        print(f"  ✗ Error: {e}")

    print()
    print("═" * 70)
    print()

    # Summary
    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(f"  • {error}")
        print()
        print(f"✓ Passed: {len(success)}")
        print(f"✗ Failed: {len(errors)}")
        return False
    else:
        print("✅ ALL TESTS PASSED!")
        print()
        print(f"Successfully tested {len(success)} components:")
        for item in success:
            print(f"  ✓ {item}")
        print()
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║          🎉 RBAC SYSTEM IS READY TO USE! 🎉                        ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()
        print("Next steps:")
        print("1. Run database migration: ./apply_rbac_migration.sh")
        print("2. Apply RBAC to your routes (see examples/ folder)")
        print("3. Test with different user roles")
        print()
        return True


if __name__ == "__main__":
    try:
        success = test_imports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
