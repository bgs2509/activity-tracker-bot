"""
Docker container health smoke tests.

These tests verify that all Docker containers start successfully
and respond to health checks.

Requirements:
- Docker and docker-compose must be installed
- Run with: docker-compose up -d before testing
"""
import pytest
import requests
import time
from typing import Dict


# Service endpoints configuration
SERVICES = {
    "data_postgres_api": {
        "url": "http://localhost:8000/health",
        "timeout": 30,
        "description": "Data API Service"
    },
    "tracker_activity_bot": {
        # Bot doesn't expose HTTP, will check via docker ps
        "description": "Telegram Bot Service"
    }
}


@pytest.mark.smoke
def test_data_api_health_endpoint():
    """
    Verify data_postgres_api service is running and healthy.

    This test sends a GET request to the /health endpoint.
    """
    service_config = SERVICES["data_postgres_api"]
    url = service_config["url"]
    timeout = service_config["timeout"]

    # Wait for service to be ready (with retry logic)
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)

            # Assert health check passes
            assert response.status_code == 200, \
                f"Health check failed with status {response.status_code}"

            data = response.json()
            assert "status" in data, "Health response missing 'status' field"
            assert data["status"] == "healthy", \
                f"Service unhealthy: {data.get('status')}"

            print(f"✅ {service_config['description']} is healthy")
            return

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for service to start (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_delay)
            else:
                pytest.fail(f"Could not connect to {url} after {max_retries} attempts")

        except requests.exceptions.Timeout:
            pytest.fail(f"Health check timed out after {timeout}s")


@pytest.mark.smoke
def test_postgres_container_running():
    """
    Verify PostgreSQL container is running.

    Uses docker ps to check container status.
    """
    import subprocess

    result = subprocess.run(
        ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Status}}"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Docker command failed"
    assert "Up" in result.stdout, "PostgreSQL container is not running"
    print("✅ PostgreSQL container is running")


@pytest.mark.smoke
def test_redis_container_running():
    """
    Verify Redis container is running.

    Uses docker ps to check container status.
    """
    import subprocess

    result = subprocess.run(
        ["docker", "ps", "--filter", "name=redis", "--format", "{{.Status}}"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Docker command failed"
    assert "Up" in result.stdout, "Redis container is not running"
    print("✅ Redis container is running")


@pytest.mark.smoke
def test_bot_container_running():
    """
    Verify Telegram bot container is running.

    Uses docker ps to check container status.
    """
    import subprocess

    result = subprocess.run(
        ["docker", "ps", "--filter", "name=tracker_activity_bot", "--format", "{{.Status}}"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Docker command failed"
    assert "Up" in result.stdout, "Bot container is not running"
    print("✅ Telegram bot container is running")


@pytest.mark.smoke
def test_all_containers_healthy():
    """
    Verify all containers pass their health checks.

    Uses docker ps to check health status.
    """
    import subprocess

    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Docker command failed"

    output = result.stdout
    print("\n📊 Container Status:")
    print(output)

    # Check that no container is unhealthy
    assert "unhealthy" not in output.lower(), \
        "One or more containers are unhealthy"

    print("✅ All containers are healthy")
