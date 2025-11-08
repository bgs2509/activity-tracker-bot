"""
Cross-Service API Contract Tests.

Verifies that bot HTTP client calls match API endpoint definitions.
This test suite prevents issues where bot calls non-existent endpoints,
which was the root cause of path mismatch bugs (e.g., /by-telegram/ vs /by-telegram-id/).

Test Coverage:
    - Bot client paths match API endpoints
    - HTTP methods match (GET, POST, PATCH, DELETE)
    - Contract tests use current API paths
    - No orphaned API endpoints (endpoints without client calls)

Coverage Target: 100% of bot → API communication paths
Execution Time: < 1 second

Author: Testing Team
Date: 2025-11-08
"""

import pytest
import re
from typing import Dict, Set
from pathlib import Path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_api_endpoints() -> Dict[str, Set[str]]:
    """
    Extract all API endpoint paths from FastAPI router definitions.

    Returns:
        Dict mapping HTTP method to set of endpoint paths

    Example:
        @router.get("/users/by-telegram/{telegram_id}")
        -> {"GET": {"/api/v1/users/by-telegram/{telegram_id}"}}
    """
    endpoints = {}
    api_path = Path("services/data_postgres_api/src/api/v1/")

    if not api_path.exists():
        return endpoints

    for file in api_path.glob("*.py"):
        if file.name == "__init__.py":
            continue

        content = file.read_text()

        # Pattern: @router.METHOD("path") or @router.METHOD("/path")
        pattern = r'@router\.(get|post|patch|put|delete)\(["\']([^"\']+)["\']\)'
        for match in re.finditer(pattern, content):
            method, path = match.groups()

            # Normalize path
            if not path.startswith('/'):
                path = f"/{path}"

            # Add /api/v1 prefix if not present
            if not path.startswith('/api'):
                # Get base path from filename (e.g., users.py -> /users)
                base = file.stem
                if path.startswith(f'/{base}'):
                    full_path = f"/api/v1{path}"
                else:
                    full_path = f"/api/v1/{base}{path}"
            else:
                full_path = path

            # Normalize path parameters: {user_id}, {id}, {telegram_id} -> {id}
            normalized_path = re.sub(r'\{[^}]+\}', '{id}', full_path)

            endpoints.setdefault(method.upper(), set()).add(normalized_path)

    return endpoints


def extract_bot_client_calls() -> Dict[str, Set[str]]:
    """
    Extract all HTTP calls from bot client services.

    Returns:
        Dict mapping HTTP method to set of endpoint paths

    Example:
        self.client.get(f"/api/v1/users/by-telegram/{telegram_id}")
        -> {"GET": {"/api/v1/users/by-telegram/{id}"}}
    """
    calls = {}
    client_path = Path("services/tracker_activity_bot/src/infrastructure/http_clients/")

    if not client_path.exists():
        return calls

    for file in client_path.glob("*_service.py"):
        content = file.read_text()

        # Pattern 1: self.client.METHOD("path") or self.client.METHOD(f"path{var}")
        # Handle f-strings: f"/api/v1/users/{user_id}" or "/api/v1/users"
        patterns = [
            r'self\.client\.(get|post|patch|put|delete)\s*\(\s*f?["\']([^"\']+)["\']',
            r'self\._client\.(get|post|patch|put|delete)\s*\(\s*f?["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                method, path = match.groups()

                # Normalize path parameters: {user_id}, {id}, {telegram_id} -> {id}
                # Also handle f-string variables
                normalized_path = re.sub(r'\{[^}]+\}', '{id}', path)

                calls.setdefault(method.upper(), set()).add(normalized_path)

    return calls


def extract_contract_test_paths() -> Dict[str, Set[str]]:
    """
    Extract paths used in contract tests.

    Returns:
        Dict mapping HTTP method to set of paths used in tests

    Example:
        response = client.get("/api/v1/users/by-telegram/123456789")
        -> {"GET": {"/api/v1/users/by-telegram/{id}"}}
    """
    test_paths = {}
    contract_test_dir = Path("services/data_postgres_api/tests/contract/")

    if not contract_test_dir.exists():
        return test_paths

    for file in contract_test_dir.glob("test_*.py"):
        content = file.read_text()

        # Pattern: client.METHOD("/path") with or without parameters
        pattern = r'client\.(get|post|patch|put|delete)\s*\(["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content):
            method, path = match.groups()

            # Normalize numeric IDs to {id}
            normalized_path = re.sub(r'/\d+', '/{id}', path)

            test_paths.setdefault(method.upper(), set()).add(normalized_path)

    return test_paths


def normalize_path(path: str) -> str:
    """
    Normalize API path for comparison.

    Args:
        path: API endpoint path

    Returns:
        Normalized path with standardized parameter placeholders

    Examples:
        "/api/v1/users/{user_id}" -> "/api/v1/users/{id}"
        "/api/v1/users/123" -> "/api/v1/users/{id}"
    """
    # Replace all path parameters with {id}
    normalized = re.sub(r'\{[^}]+\}', '{id}', path)
    # Replace numeric values with {id}
    normalized = re.sub(r'/\d+', '/{id}', normalized)
    return normalized


def paths_match(bot_path: str, api_path: str) -> bool:
    """
    Check if bot client path matches API endpoint.

    Args:
        bot_path: Path from bot client call
        api_path: Path from API endpoint definition

    Returns:
        True if paths match after normalization

    Examples:
        ("/api/v1/users/{user_id}", "/api/v1/users/{telegram_id}") -> True
        ("/api/v1/users/by-telegram", "/api/v1/users/by-telegram/{id}") -> False
    """
    return normalize_path(bot_path) == normalize_path(api_path)


# ============================================================================
# TEST SUITES
# ============================================================================

class TestBotAPIContracts:
    """Test suite for bot → API contract validation."""

    @pytest.mark.integration
    def test_bot_client_paths_match_api_endpoints(self):
        """
        Verify all bot HTTP client calls match existing API endpoints.

        GIVEN: Bot HTTP client service calls
        WHEN: Comparing with API endpoint definitions
        THEN: All bot calls match existing API endpoints

        This test would have caught the /by-telegram/ vs /by-telegram-id/ bug.
        """
        api_endpoints = extract_api_endpoints()
        bot_calls = extract_bot_client_calls()

        mismatches = []

        for method, bot_paths in bot_calls.items():
            api_paths = api_endpoints.get(method, set())

            for bot_path in bot_paths:
                # Check if bot path matches any API endpoint
                has_match = any(
                    paths_match(bot_path, api_path)
                    for api_path in api_paths
                )

                if not has_match:
                    mismatches.append(f"{method} {bot_path}")

        if mismatches:
            # Generate helpful error message
            error_msg = [
                f"\n{'='*60}",
                "BOT CALLS NON-EXISTENT API ENDPOINTS",
                f"{'='*60}",
                "",
                "The following bot client calls have NO matching API endpoints:",
                ""
            ]
            for call in sorted(mismatches):
                error_msg.append(f"  ❌ {call}")

            error_msg.extend([
                "",
                "Available API endpoints by method:",
                ""
            ])

            for method, paths in sorted(api_endpoints.items()):
                error_msg.append(f"  {method}:")
                for path in sorted(paths)[:5]:
                    error_msg.append(f"    ✓ {path}")
                if len(paths) > 5:
                    error_msg.append(f"    ... and {len(paths) - 5} more")

            error_msg.extend([
                "",
                "To fix this:",
                "1. Add missing API endpoint in services/data_postgres_api/src/api/v1/",
                "2. Update bot client path in services/tracker_activity_bot/src/infrastructure/http_clients/",
                f"{'='*60}\n"
            ])

            pytest.fail("\n".join(error_msg))

    @pytest.mark.integration
    def test_http_methods_match(self):
        """
        Verify bot uses correct HTTP methods for API calls.

        GIVEN: Bot HTTP client calls
        WHEN: Checking HTTP method usage
        THEN: Bot uses RESTful HTTP methods correctly
              - GET for reads
              - POST for creates
              - PATCH for updates
              - DELETE for deletes

        This test would have caught PUT vs PATCH mismatches.
        """
        bot_calls = extract_bot_client_calls()
        api_endpoints = extract_api_endpoints()

        # Check for PUT usage (should use PATCH for partial updates)
        put_calls = bot_calls.get("PUT", set())
        if put_calls:
            pytest.fail(
                f"Bot uses PUT instead of PATCH for partial updates:\n"
                f"{chr(10).join(f'  ❌ PUT {path}' for path in put_calls)}\n\n"
                f"Use PATCH for partial updates per REST best practices."
            )

        # Verify all bot methods have corresponding API endpoints
        for method, paths in bot_calls.items():
            if method not in api_endpoints:
                pytest.fail(
                    f"Bot uses {method} but API has no {method} endpoints:\n"
                    f"{chr(10).join(f'  ❌ {method} {path}' for path in paths)}"
                )


class TestContractTestCoverage:
    """Test suite for contract test coverage."""

    @pytest.mark.integration
    def test_contract_tests_use_current_api_paths(self):
        """
        Verify contract tests use current API endpoint paths.

        GIVEN: API contract test paths
        WHEN: Comparing with actual API endpoints
        THEN: Contract tests use correct, up-to-date paths

        This test prevents contract tests from using outdated paths.
        """
        api_endpoints = extract_api_endpoints()
        test_paths = extract_contract_test_paths()

        outdated = []

        for method, paths in test_paths.items():
            api_paths = api_endpoints.get(method, set())

            for test_path in paths:
                # Check if test path matches any current API endpoint
                has_match = any(
                    paths_match(test_path, api_path)
                    for api_path in api_paths
                )

                if not has_match:
                    outdated.append(f"{method} {test_path}")

        if outdated:
            error_msg = [
                f"\n{'='*60}",
                "CONTRACT TESTS USE OUTDATED PATHS",
                f"{'='*60}",
                "",
                "The following contract test paths don't match current API:",
                ""
            ]
            for call in sorted(outdated):
                error_msg.append(f"  ❌ {call}")

            error_msg.extend([
                "",
                "Update contract tests to use current API paths.",
                f"{'='*60}\n"
            ])

            pytest.fail("\n".join(error_msg))

    @pytest.mark.integration
    def test_api_endpoints_have_contract_tests(self):
        """
        Verify all API endpoints have contract tests.

        GIVEN: API endpoint definitions
        WHEN: Checking contract test coverage
        THEN: Every API endpoint has at least one contract test

        NOTE: This is a warning test - missing tests won't fail build.
        """
        api_endpoints = extract_api_endpoints()
        test_paths = extract_contract_test_paths()

        missing_tests = []

        for method, api_paths in api_endpoints.items():
            test_paths_for_method = test_paths.get(method, set())

            for api_path in api_paths:
                # Check if API endpoint is tested
                has_test = any(
                    paths_match(api_path, test_path)
                    for test_path in test_paths_for_method
                )

                if not has_test:
                    missing_tests.append(f"{method} {api_path}")

        if missing_tests:
            # This is informational - we don't fail the build
            warning_msg = [
                f"\n{'='*60}",
                "⚠️  WARNING: API ENDPOINTS WITHOUT CONTRACT TESTS",
                f"{'='*60}",
                "",
                "The following API endpoints have no contract tests:",
                ""
            ]
            for endpoint in sorted(missing_tests)[:10]:
                warning_msg.append(f"  ⚠️  {endpoint}")

            if len(missing_tests) > 10:
                warning_msg.append(f"  ... and {len(missing_tests) - 10} more")

            warning_msg.extend([
                "",
                "Consider adding contract tests for better coverage.",
                f"{'='*60}\n"
            ])

            # Print warning but don't fail
            print("\n".join(warning_msg))


class TestAPIPathConsistency:
    """Test suite for API path naming consistency."""

    @pytest.mark.integration
    def test_api_paths_follow_rest_conventions(self):
        """
        Verify API paths follow RESTful naming conventions.

        GIVEN: API endpoint paths
        WHEN: Checking path structure
        THEN: Paths follow REST best practices:
              - Use nouns, not verbs
              - Use kebab-case
              - Use plural for collections
              - Use path parameters for IDs
        """
        api_endpoints = extract_api_endpoints()

        # Common violations
        violations = []

        # Check for verb-based paths (anti-pattern)
        verb_patterns = [
            r'/get[A-Z]',
            r'/create[A-Z]',
            r'/update[A-Z]',
            r'/delete[A-Z]',
            r'/fetch[A-Z]',
        ]

        for method, paths in api_endpoints.items():
            for path in paths:
                # Check for verbs in path
                for verb_pattern in verb_patterns:
                    if re.search(verb_pattern, path):
                        violations.append(
                            f"{method} {path} - Uses verb in path (use HTTP method instead)"
                        )

                # Check for snake_case instead of kebab-case
                # Extract path segments (excluding parameters)
                segments = re.findall(r'/([a-z_]+)', path)
                for segment in segments:
                    if '_' in segment and segment != 'api':
                        violations.append(
                            f"{method} {path} - Uses snake_case '{segment}' (use kebab-case)"
                        )

        if violations:
            # This is a warning, not a failure (legacy code may exist)
            warning_msg = [
                f"\n{'='*60}",
                "⚠️  WARNING: API PATH NAMING VIOLATIONS",
                f"{'='*60}",
                "",
                "The following paths violate REST conventions:",
                ""
            ]
            for violation in violations[:10]:
                warning_msg.append(f"  ⚠️  {violation}")

            if len(violations) > 10:
                warning_msg.append(f"  ... and {len(violations) - 10} more")

            warning_msg.extend([
                "",
                "REST Best Practices:",
                "  ✓ Use nouns: /users not /getUsers",
                "  ✓ Use HTTP methods: GET /users/{id} not GET /getUserById/{id}",
                "  ✓ Use kebab-case: /user-settings not /user_settings",
                "  ✓ Use plurals: /users not /user",
                f"{'='*60}\n"
            ])

            print("\n".join(warning_msg))


# ============================================================================
# REGRESSION TESTS (Specific Bug Prevention)
# ============================================================================

class TestRegressionPrevention:
    """Tests that prevent specific API contract bugs from recurring."""

    @pytest.mark.integration
    def test_user_lookup_endpoint_exists(self):
        """
        Regression test: User lookup by telegram_id must exist.

        Bug History: 2025-11-08 - Bot called /by-telegram/ but API had /by-telegram-id/
        Root Cause: Endpoint path mismatch between bot client and API

        GIVEN: Bot needs to lookup users by telegram_id
        WHEN: Checking API endpoints
        THEN: GET /api/v1/users/by-telegram/{id} endpoint exists
        """
        api_endpoints = extract_api_endpoints()
        get_endpoints = api_endpoints.get("GET", set())

        has_endpoint = any(
            "/users/by-telegram/{id}" in normalize_path(path)
            for path in get_endpoints
        )

        assert has_endpoint, \
            "REGRESSION: User lookup endpoint missing!\\n" \
            "Expected: GET /api/v1/users/by-telegram/{telegram_id}\\n" \
            f"Available GET endpoints: {sorted(get_endpoints)}"

    @pytest.mark.integration
    def test_settings_update_uses_patch(self):
        """
        Regression test: Settings update must use PATCH, not PUT.

        Bug History: 2025-11-08 - Bot used PATCH but API had PUT
        Root Cause: HTTP method mismatch for partial updates

        GIVEN: Bot sends partial settings updates
        WHEN: Checking API endpoints
        THEN: PATCH /api/v1/user-settings/{id} endpoint exists (not PUT)
        """
        api_endpoints = extract_api_endpoints()
        patch_endpoints = api_endpoints.get("PATCH", set())
        put_endpoints = api_endpoints.get("PUT", set())

        has_patch = any(
            "/user-settings/{id}" in normalize_path(path)
            for path in patch_endpoints
        )

        has_put = any(
            "/user-settings/{id}" in normalize_path(path)
            for path in put_endpoints
        )

        assert has_patch, \
            "REGRESSION: Settings update endpoint must use PATCH!\\n" \
            "Expected: PATCH /api/v1/user-settings/{settings_id}\\n" \
            f"Available PATCH endpoints: {sorted(patch_endpoints)}"

        assert not has_put, \
            "REGRESSION: Settings update uses PUT instead of PATCH!\\n" \
            "Use PATCH for partial updates per REST best practices.\\n" \
            f"Found PUT endpoints: {sorted(put_endpoints)}"
