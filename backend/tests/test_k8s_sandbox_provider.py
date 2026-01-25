"""Integration tests for KubernetesSandboxProvider.

These tests require a real Kubernetes cluster (e.g., Docker Desktop with K8s enabled).
They test the full lifecycle of sandbox creation, usage, and cleanup.

Prerequisites:
1. Docker Desktop with Kubernetes enabled, or minikube/kind cluster
2. kubectl configured to connect to the cluster
3. Run: kubectl apply -f docker/k8s/namespace.yaml
4. Run: kubectl apply -f docker/k8s/headless-service.yaml
5. (Optional) Run: kubectl apply -f docker/k8s/skills-pv-pvc.yaml

Run tests:
    pytest tests/test_k8s_sandbox_provider.py -v -s

Skip these tests if K8s is not available:
    pytest tests/test_k8s_sandbox_provider.py -v -s -k "not k8s"
"""

import os
import subprocess
import sys
import time
import uuid

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def is_kubernetes_available() -> bool:
    """Check if Kubernetes cluster is available and accessible."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_namespace_ready() -> bool:
    """Check if the deer-flow namespace exists."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "namespace", "deer-flow"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_headless_service_ready() -> bool:
    """Check if the headless service exists."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "service", "deer-flow-sandbox", "-n", "deer-flow"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip all tests if Kubernetes is not available
pytestmark = pytest.mark.skipif(
    not is_kubernetes_available(),
    reason="Kubernetes cluster not available. Start Docker Desktop with K8s enabled.",
)


@pytest.fixture(scope="module")
def ensure_k8s_resources():
    """Ensure K8s namespace and headless service are created before tests."""
    if not is_namespace_ready():
        pytest.skip("Namespace 'deer-flow' not found. Run: kubectl apply -f docker/k8s/namespace.yaml")

    if not is_headless_service_ready():
        pytest.skip("Headless service 'deer-flow-sandbox' not found. Run: kubectl apply -f docker/k8s/headless-service.yaml")


@pytest.fixture
def provider(ensure_k8s_resources):
    """Create a KubernetesSandboxProvider instance for testing."""
    from src.community.aio_sandbox import KubernetesSandboxProvider

    provider = KubernetesSandboxProvider()
    yield provider
    # Cleanup: shutdown provider after each test
    provider.shutdown()


@pytest.fixture
def thread_id():
    """Generate a unique thread ID for testing."""
    return f"test-thread-{uuid.uuid4().hex[:8]}"


class TestKubernetesSandboxProviderBasic:
    """Basic tests for KubernetesSandboxProvider initialization."""

    def test_provider_initialization(self, provider):
        """Test that provider initializes correctly."""
        assert provider is not None
        assert provider._core_v1 is not None
        assert provider._config["namespace"] == "deer-flow"
        assert provider._config["pod_prefix"] == "deer-flow-sandbox"

    def test_provider_config_loading(self, provider):
        """Test configuration is loaded correctly."""
        config = provider._config
        assert "image" in config
        assert "namespace" in config
        assert "ttl_seconds" in config
        assert config["ttl_seconds"] > 0


class TestKubernetesSandboxProviderLifecycle:
    """Tests for sandbox lifecycle: acquire, use, release."""

    def test_acquire_and_release_sandbox(self, provider, thread_id):
        """Test basic acquire and release of a sandbox."""
        # Acquire sandbox
        sandbox_id = provider.acquire(thread_id=thread_id)
        assert sandbox_id is not None
        assert len(sandbox_id) == 8  # UUID[:8]

        # Verify sandbox is tracked
        sandbox = provider.get(sandbox_id)
        assert sandbox is not None
        assert sandbox.id == sandbox_id

        # Verify Pod exists
        assert sandbox_id in provider._pods
        pod_name = provider._pods[sandbox_id]
        assert pod_name.startswith("deer-flow-sandbox-")

        # Release sandbox
        provider.release(sandbox_id)

        # Verify sandbox is removed from active tracking
        assert provider.get(sandbox_id) is None

        # Verify Pod is no longer tracked (it's been deleted)
        assert sandbox_id not in provider._pods

    def test_acquire_same_thread_reuses_sandbox(self, provider, thread_id):
        """Test that acquiring for the same thread reuses existing sandbox."""
        # First acquire
        sandbox_id_1 = provider.acquire(thread_id=thread_id)

        # Second acquire with same thread_id should reuse
        sandbox_id_2 = provider.acquire(thread_id=thread_id)

        assert sandbox_id_1 == sandbox_id_2

        # Cleanup
        provider.release(sandbox_id_1)

    def test_acquire_different_threads_creates_different_sandboxes(self, provider):
        """Test that different threads get different sandboxes."""
        thread_id_1 = f"test-thread-{uuid.uuid4().hex[:8]}"
        thread_id_2 = f"test-thread-{uuid.uuid4().hex[:8]}"

        sandbox_id_1 = provider.acquire(thread_id=thread_id_1)
        sandbox_id_2 = provider.acquire(thread_id=thread_id_2)

        assert sandbox_id_1 != sandbox_id_2

        # Cleanup
        provider.release(sandbox_id_1)
        provider.release(sandbox_id_2)

    def test_acquire_without_thread_id(self, provider):
        """Test acquiring sandbox without thread_id."""
        sandbox_id = provider.acquire(thread_id=None)
        assert sandbox_id is not None

        sandbox = provider.get(sandbox_id)
        assert sandbox is not None

        provider.release(sandbox_id)


class TestKubernetesSandboxExecution:
    """Tests for executing commands and file operations in sandbox."""

    def test_execute_simple_command(self, provider, thread_id):
        """Test executing a simple shell command."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Execute echo command
            result = sandbox.execute_command("echo 'Hello, Kubernetes!'")
            assert "Hello, Kubernetes!" in result
        finally:
            provider.release(sandbox_id)

    def test_execute_command_with_output(self, provider, thread_id):
        """Test executing command and capturing output."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Execute pwd command
            result = sandbox.execute_command("pwd")
            assert result.strip()  # Should return a path

            # Execute ls command
            result = sandbox.execute_command("ls -la /")
            assert "bin" in result or "usr" in result
        finally:
            provider.release(sandbox_id)

    def test_execute_python_code(self, provider, thread_id):
        """Test executing Python code in sandbox."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Execute simple Python
            result = sandbox.execute_command('python3 -c "print(2 + 2)"')
            assert "4" in result

            # Execute Python with imports
            result = sandbox.execute_command('python3 -c "import sys; print(sys.version_info.major)"')
            assert "3" in result
        finally:
            provider.release(sandbox_id)

    def test_write_and_read_file(self, provider, thread_id):
        """Test writing and reading files in sandbox."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Get home directory
            home_dir = sandbox.home_dir
            test_file = f"{home_dir}/test_file.txt"
            test_content = "Hello from K8s sandbox test!"

            # Write file
            sandbox.write_file(test_file, test_content)

            # Read file back
            content = sandbox.read_file(test_file)
            assert test_content in content
        finally:
            provider.release(sandbox_id)

    def test_write_file_append(self, provider, thread_id):
        """Test appending to files in sandbox."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            home_dir = sandbox.home_dir
            test_file = f"{home_dir}/append_test.txt"

            # Write initial content
            sandbox.write_file(test_file, "Line 1\n")

            # Append more content
            sandbox.write_file(test_file, "Line 2\n", append=True)

            # Read and verify
            content = sandbox.read_file(test_file)
            assert "Line 1" in content
            assert "Line 2" in content
        finally:
            provider.release(sandbox_id)

    def test_list_directory(self, provider, thread_id):
        """Test listing directory contents."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # List root directory
            entries = sandbox.list_dir("/")
            assert len(entries) > 0

            # Should contain common directories
            entry_str = " ".join(entries)
            assert "bin" in entry_str or "usr" in entry_str or "etc" in entry_str
        finally:
            provider.release(sandbox_id)

    def test_execute_multiline_script(self, provider, thread_id):
        """Test executing a multiline script."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Create and execute a script
            script = """
for i in 1 2 3; do
    echo "Number: $i"
done
"""
            result = sandbox.execute_command(script)
            assert "Number: 1" in result
            assert "Number: 2" in result
            assert "Number: 3" in result
        finally:
            provider.release(sandbox_id)


class TestKubernetesSandboxConcurrency:
    """Tests for concurrent sandbox operations."""

    def test_multiple_sandboxes_concurrent(self, provider):
        """Test creating multiple sandboxes concurrently."""
        sandbox_ids = []
        num_sandboxes = 3

        try:
            # Create multiple sandboxes
            for i in range(num_sandboxes):
                thread_id = f"concurrent-test-{uuid.uuid4().hex[:8]}"
                sandbox_id = provider.acquire(thread_id=thread_id)
                sandbox_ids.append(sandbox_id)

            # Verify all sandboxes are unique and accessible
            assert len(set(sandbox_ids)) == num_sandboxes

            for sandbox_id in sandbox_ids:
                sandbox = provider.get(sandbox_id)
                assert sandbox is not None
                # Verify each sandbox can execute commands
                result = sandbox.execute_command("echo 'test'")
                assert "test" in result

        finally:
            # Cleanup all sandboxes
            for sandbox_id in sandbox_ids:
                provider.release(sandbox_id)

    def test_sandbox_isolation(self, provider):
        """Test that sandboxes are isolated from each other."""
        thread_id_1 = f"isolation-test-{uuid.uuid4().hex[:8]}"
        thread_id_2 = f"isolation-test-{uuid.uuid4().hex[:8]}"

        sandbox_id_1 = provider.acquire(thread_id=thread_id_1)
        sandbox_id_2 = provider.acquire(thread_id=thread_id_2)

        sandbox_1 = provider.get(sandbox_id_1)
        sandbox_2 = provider.get(sandbox_id_2)

        try:
            # Create a file in sandbox 1
            sandbox_1.write_file("/tmp/isolation_test.txt", "sandbox1")

            # Try to read it from sandbox 2 - should not exist or have different content
            result = sandbox_2.execute_command("cat /tmp/isolation_test.txt 2>&1 || echo 'NOT_FOUND'")
            # Either file doesn't exist or has different content
            assert "NOT_FOUND" in result or "sandbox1" not in result or "No such file" in result

        finally:
            provider.release(sandbox_id_1)
            provider.release(sandbox_id_2)


class TestKubernetesSandboxCleanup:
    """Tests for sandbox cleanup and shutdown."""

    def test_shutdown_releases_all_sandboxes(self, ensure_k8s_resources):
        """Test that shutdown releases all active sandboxes."""
        from src.community.aio_sandbox import KubernetesSandboxProvider

        provider = KubernetesSandboxProvider()

        # Create multiple sandboxes
        sandbox_ids = []
        for i in range(2):
            thread_id = f"shutdown-test-{uuid.uuid4().hex[:8]}"
            sandbox_id = provider.acquire(thread_id=thread_id)
            sandbox_ids.append(sandbox_id)

        # Verify sandboxes exist
        assert len(provider._sandboxes) == 2

        # Shutdown
        provider.shutdown()

        # Verify all sandboxes are released
        assert len(provider._sandboxes) == 0

    def test_release_deletes_pod(self, provider, thread_id):
        """Test that release deletes the Pod."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        pod_name = provider._pods[sandbox_id]

        # Release
        provider.release(sandbox_id)

        # Pod should no longer be tracked in provider
        assert sandbox_id not in provider._pods

        # Give K8s a moment to process the deletion
        time.sleep(3)

        # Verify Pod is deleted or terminating in K8s
        result = subprocess.run(
            ["kubectl", "get", "pod", pod_name, "-n", "deer-flow", "-o", "jsonpath={.metadata.deletionTimestamp}"],
            capture_output=True,
            timeout=10,
        )
        # Pod should either not exist (returncode != 0) or have a deletionTimestamp (terminating)
        pod_deleted_or_terminating = result.returncode != 0 or result.stdout.decode().strip() != ""
        assert pod_deleted_or_terminating, f"Pod {pod_name} should be deleted or terminating"


class TestKubernetesSandboxErrorHandling:
    """Tests for error handling scenarios."""

    def test_get_nonexistent_sandbox(self, provider):
        """Test getting a non-existent sandbox returns None."""
        result = provider.get("nonexistent-id")
        assert result is None

    def test_release_nonexistent_sandbox(self, provider):
        """Test releasing a non-existent sandbox doesn't raise error."""
        # Should not raise
        provider.release("nonexistent-id")

    def test_double_release(self, provider, thread_id):
        """Test that double release doesn't cause issues."""
        sandbox_id = provider.acquire(thread_id=thread_id)

        # First release
        provider.release(sandbox_id)

        # Second release should not raise
        provider.release(sandbox_id)


class TestKubernetesSandboxRealWorldScenarios:
    """Tests simulating real-world usage scenarios."""

    def test_data_analysis_workflow(self, provider, thread_id):
        """Simulate a data analysis workflow."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Create sample data
            csv_content = "name,value\nAlice,100\nBob,200\nCharlie,150"
            sandbox.write_file("/tmp/data.csv", csv_content)

            # Analyze with Python
            python_script = """
import csv
with open("/tmp/data.csv") as f:
    reader = csv.DictReader(f)
    total = sum(int(row["value"]) for row in reader)
    print(f"Total: {total}")
"""
            result = sandbox.execute_command(f"python3 -c '{python_script}'")
            assert "Total: 450" in result

        finally:
            provider.release(sandbox_id)

    def test_file_processing_workflow(self, provider, thread_id):
        """Simulate a file processing workflow."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Create multiple files
            for i in range(3):
                sandbox.write_file(f"/tmp/file_{i}.txt", f"Content {i}")

            # Process files
            result = sandbox.execute_command("cat /tmp/file_*.txt")
            assert "Content 0" in result
            assert "Content 1" in result
            assert "Content 2" in result

            # Count files
            result = sandbox.execute_command("ls /tmp/file_*.txt | wc -l")
            assert "3" in result

        finally:
            provider.release(sandbox_id)

    def test_long_running_computation(self, provider, thread_id):
        """Test a longer-running computation."""
        sandbox_id = provider.acquire(thread_id=thread_id)
        sandbox = provider.get(sandbox_id)

        try:
            # Run a computation that takes a few seconds
            result = sandbox.execute_command("python3 -c \"import time; time.sleep(2); print('Computation complete')\"")
            assert "Computation complete" in result

        finally:
            provider.release(sandbox_id)


# Utility functions for manual testing
def cleanup_all_test_pods():
    """Utility to clean up all test pods manually."""
    subprocess.run(
        [
            "kubectl",
            "delete",
            "pods",
            "-n",
            "deer-flow",
            "-l",
            "app=deer-flow-sandbox",
            "--force",
            "--grace-period=0",
        ],
        capture_output=True,
    )
    print("Cleaned up all deer-flow-sandbox pods")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
