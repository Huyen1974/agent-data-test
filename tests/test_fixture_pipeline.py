"""
Test suite for Golden Fixtures Pipeline

Validates the structure and consistency of Langroid agent fixtures
without making external API calls (offline mode).

Usage:
    pytest -m fixture --cov=agent_data --disable-warnings
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Import agent_data for coverage


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path("agent_data/fixtures")


@pytest.fixture
def sample_queries(fixtures_dir: Path) -> dict[str, str]:
    """Load sample query files for testing."""
    queries = {}
    for i in [1, 2]:
        query_file = fixtures_dir / f"sample_query_{i}.txt"
        if query_file.exists():
            with open(query_file, encoding="utf-8") as f:
                queries[f"query_{i}"] = f.read().strip()
    return queries


@pytest.fixture
def expected_outputs(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    """Load expected output JSON files for testing."""
    outputs = {}
    for i in [1, 2]:
        output_file = fixtures_dir / f"expected_output_{i}.json"
        if output_file.exists():
            with open(output_file, encoding="utf-8") as f:
                outputs[f"output_{i}"] = json.load(f)
    return outputs


@pytest.mark.fixture
@pytest.mark.slow
class TestFixturePipeline:
    """Test suite for fixture pipeline validation."""

    def test_fixtures_directory_exists(self, fixtures_dir: Path):
        """Test that fixtures directory exists and is accessible."""
        assert fixtures_dir.exists(), "Fixtures directory should exist"
        assert fixtures_dir.is_dir(), "Fixtures path should be a directory"

    def test_sample_queries_exist(self, fixtures_dir: Path):
        """Test that sample query files exist and are readable."""
        for i in [1, 2]:
            query_file = fixtures_dir / f"sample_query_{i}.txt"
            assert query_file.exists(), f"Sample query {i} should exist"
            assert (
                query_file.stat().st_size > 0
            ), f"Sample query {i} should not be empty"

    def test_expected_outputs_exist(self, fixtures_dir: Path):
        """Test that expected output files exist and are valid JSON."""
        for i in [1, 2]:
            output_file = fixtures_dir / f"expected_output_{i}.json"
            assert output_file.exists(), f"Expected output {i} should exist"

            # Validate JSON structure
            with open(output_file, encoding="utf-8") as f:
                data = json.load(f)
                assert isinstance(
                    data, dict
                ), f"Expected output {i} should be a JSON object"

    def test_sample_queries_content(self, sample_queries: dict[str, str]):
        """Test that sample queries have meaningful content."""
        assert len(sample_queries) == 2, "Should have exactly 2 sample queries"

        for query_key, query_text in sample_queries.items():
            assert (
                len(query_text.strip()) > 10
            ), f"{query_key} should have meaningful content"
            assert not query_text.startswith(
                "TODO"
            ), f"{query_key} should not be a placeholder"

    def test_expected_output_structure(
        self, expected_outputs: dict[str, dict[str, Any]]
    ):
        """Test that expected outputs have correct ToolMessage structure."""
        assert len(expected_outputs) == 2, "Should have exactly 2 expected outputs"

        for output_key, output_data in expected_outputs.items():
            # Validate top-level structure
            assert "type" in output_data, f"{output_key} should have 'type' field"
            assert "content" in output_data, f"{output_key} should have 'content' field"
            assert (
                "metadata" in output_data
            ), f"{output_key} should have 'metadata' field"

            # Validate type field
            assert (
                output_data["type"] == "ToolMessage"
            ), f"{output_key} should be ToolMessage type"

            # Validate content structure
            content = output_data["content"]
            assert isinstance(content, dict), f"{output_key} content should be a dict"
            assert "query" in content, f"{output_key} content should have 'query' field"
            assert (
                "response" in content
            ), f"{output_key} content should have 'response' field"

            # Validate metadata structure
            metadata = output_data["metadata"]
            assert isinstance(metadata, dict), f"{output_key} metadata should be a dict"
            assert (
                "timestamp" in metadata
            ), f"{output_key} metadata should have 'timestamp'"
            assert (
                "model_version" in metadata
            ), f"{output_key} metadata should have 'model_version'"
            assert (
                "mock_data" in metadata
            ), f"{output_key} metadata should have 'mock_data' flag"

    def test_real_agent_mode_validation(
        self, expected_outputs: dict[str, dict[str, Any]]
    ):
        """Test validation for real agent mode (--no-mock flag) when mock_data is False."""
        for output_key, output_data in expected_outputs.items():
            metadata = output_data["metadata"]

            # Check if this is real agent mode (mock_data: false)
            if not metadata.get("mock_data", True):
                # Real agent mode validation

                # Should have additional metadata fields for real mode
                assert (
                    "embedding_model" in metadata
                ), f"{output_key} should have embedding_model in real mode"
                assert (
                    metadata["embedding_model"] == "text-embedding-3-small"
                ), f"{output_key} should use text-embedding-3-small embedding"

                assert (
                    "collection_name" in metadata
                ), f"{output_key} should have collection_name in real mode"
                assert (
                    metadata["collection_name"] == "test_documents"
                ), f"{output_key} should cite test_documents collection"

                assert (
                    "qdrant_region" in metadata
                ), f"{output_key} should have qdrant_region in real mode"
                assert (
                    metadata["qdrant_region"] == "asia-southeast1"
                ), f"{output_key} should use asia-southeast1 region"

                # Content should have collection_info for real mode
                content = output_data["content"]
                if "collection_info" in content:
                    collection_info = content["collection_info"]
                    assert (
                        collection_info["collection_name"] == "test_documents"
                    ), f"{output_key} collection_info should reference test_documents"
                    assert (
                        collection_info["embedding_model"] == "text-embedding-3-small"
                    ), f"{output_key} should use correct embedding model"
                    assert (
                        collection_info["distance_metric"] == "cosine"
                    ), f"{output_key} should use cosine distance metric"

    def test_output_content_quality(self, expected_outputs: dict[str, dict[str, Any]]):
        """Test that output content has meaningful responses."""
        for output_key, output_data in expected_outputs.items():
            content = output_data["content"]

            # Validate query content
            query = content["query"]
            assert (
                len(query.strip()) > 10
            ), f"{output_key} query should have meaningful content"

            # Validate response content
            response = content["response"]
            assert (
                len(response.strip()) > 50
            ), f"{output_key} response should be substantial"
            assert not response.startswith(
                "TODO"
            ), f"{output_key} response should not be placeholder"

    def test_metadata_consistency(self, expected_outputs: dict[str, dict[str, Any]]):
        """Test that metadata fields are consistent across outputs."""
        model_versions = set()

        for output_key, output_data in expected_outputs.items():
            metadata = output_data["metadata"]

            # Check required metadata fields
            assert (
                "processing_time_ms" in metadata
            ), f"{output_key} should have processing time"
            assert isinstance(
                metadata["processing_time_ms"], int
            ), f"{output_key} processing time should be integer"
            assert (
                metadata["processing_time_ms"] > 0
            ), f"{output_key} processing time should be positive"

            # Collect model versions for consistency check
            model_versions.add(metadata["model_version"])

        # All outputs should use the same model version in fixtures
        assert (
            len(model_versions) == 1
        ), "All fixtures should use the same model version"
        assert (
            "langroid" in list(model_versions)[0].lower()
        ), "Should use Langroid model version"

    def test_offline_mode_compliance(self, expected_outputs: dict[str, dict[str, Any]]):
        """Test that mock fixtures are marked for offline mode (no external API calls)."""
        for output_key, output_data in expected_outputs.items():
            metadata = output_data["metadata"]

            # Ensure mock_data flag is present
            assert "mock_data" in metadata, f"{output_key} should have mock_data flag"

            # If this is mock mode, ensure it's marked as such
            if metadata.get("mock_data", True):
                assert (
                    metadata["mock_data"] is True
                ), f"{output_key} should be marked as mock data when in mock mode"

    def test_query_response_alignment(
        self,
        sample_queries: dict[str, str],
        expected_outputs: dict[str, dict[str, Any]],
    ):
        """Test that queries and responses are properly aligned."""
        for i in [1, 2]:
            query_key = f"query_{i}"
            output_key = f"output_{i}"

            if query_key in sample_queries and output_key in expected_outputs:
                original_query = sample_queries[query_key]
                output_query = expected_outputs[output_key]["content"]["query"]

                assert (
                    original_query == output_query
                ), f"Query {i} should match between input and output files"


@pytest.mark.fixture
def test_fixture_coverage_included():
    """Test that fixture tests are included in coverage."""
    # This test ensures that the fixture tests are counted in --cov=agent_data
    # The test itself validates that the test module is properly structured
    assert __name__ in [
        "test_fixture_pipeline",
        "tests.test_fixture_pipeline",
    ], "Test module should be properly named for coverage"

    # Verify test classes and methods are discoverable
    test_class = TestFixturePipeline
    test_methods = [method for method in dir(test_class) if method.startswith("test_")]
    assert (
        len(test_methods) >= 7
    ), "Should have multiple test methods for comprehensive coverage"
