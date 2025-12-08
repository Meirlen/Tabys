#!/usr/bin/env python3
"""
Verification script to test RBAC system is working
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_rbac_system():
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║           RBAC System Verification Test                            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Import RBAC modules
    print("Test 1: Importing RBAC modules...")
    total_tests += 1
    try:
        from app.rbac import Role, Module, Permission
        from app.rbac import require_role, require_permission, require_module_access
        print("  ✓ RBAC modules imported successfully")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to import RBAC modules: {e}")
        return False
    
    # Test 2: Check Role enum
    print("\nTest 2: Checking Role enum...")
    total_tests += 1
    try:
        expected_roles = ['CLIENT', 'VOLUNTEER_ADMIN', 'MSB', 'NPO', 'GOVERNMENT', 'ADMINISTRATOR', 'SUPER_ADMIN']
        actual_roles = [r.name for r in Role]
        if set(actual_roles) == set(expected_roles):
            print(f"  ✓ All 7 roles defined: {', '.join(actual_roles)}")
            success_count += 1
        else:
            print(f"  ✗ Role mismatch. Expected: {expected_roles}, Got: {actual_roles}")
    except Exception as e:
        print(f"  ✗ Failed to check roles: {e}")
    
    # Test 3: Check Module constants
    print("\nTest 3: Checking Module constants...")
    total_tests += 1
    try:
        modules = [attr for attr in dir(Module) if not attr.startswith('_')]
        print(f"  ✓ Modules defined: {', '.join(modules[:5])}... ({len(modules)} total)")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to check modules: {e}")
    
    # Test 4: Test permission checks
    print("\nTest 4: Testing permission checks...")
    total_tests += 1
    try:
        from app.rbac import has_permission
        
        test_cases = [
            ("volunteer_admin", "volunteers", "read", True),
            ("volunteer_admin", "vacancies", "read", False),
            ("msb", "vacancies", "create", True),
            ("government", "news", "read", True),
            ("government", "news", "create", False),
            ("super_admin", "volunteers", "delete", True),
        ]
        
        all_passed = True
        for role, module, perm, expected in test_cases:
            result = has_permission(role, module, perm)
            if result == expected:
                print(f"  ✓ {role} → {module}.{perm}: {result}")
            else:
                print(f"  ✗ {role} → {module}.{perm}: {result} (expected {expected})")
                all_passed = False
        
        if all_passed:
            success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to test permissions: {e}")
    
    # Test 5: Import models with RoleEnum
    print("\nTest 5: Checking models.RoleEnum...")
    total_tests += 1
    try:
        from app.models import RoleEnum as ModelRoleEnum
        model_roles = [r.value for r in ModelRoleEnum]
        print(f"  ✓ Model RoleEnum has {len(model_roles)} values: {', '.join(model_roles[:3])}...")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to import models.RoleEnum: {e}")
    
    # Test 6: Import schemas with RoleEnum
    print("\nTest 6: Checking schemas.RoleEnum...")
    total_tests += 1
    try:
        from app.schemas import RoleEnum as SchemaRoleEnum
        schema_roles = [r.value for r in SchemaRoleEnum]
        print(f"  ✓ Schema RoleEnum has {len(schema_roles)} values: {', '.join(schema_roles[:3])}...")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed to import schemas.RoleEnum: {e}")
    
    print()
    print("=" * 70)
    print()
    print(f"Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print()
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║          ✅ ALL TESTS PASSED - RBAC SYSTEM IS READY! ✅            ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()
        print("Next steps:")
        print("1. Apply RBAC to your routes (see examples/ folder)")
        print("2. Test with different user roles")
        print("3. Check documentation in START_HERE.md")
        return True
    else:
        print()
        print(f"❌ {total_tests - success_count} test(s) failed")
        return False

if __name__ == "__main__":
    try:
        success = test_rbac_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
