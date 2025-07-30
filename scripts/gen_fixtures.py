#!/usr/bin/env python3
"""
Golden Fixtures Generator for Langroid Agent Pipeline

This script generates fixtures for testing Langroid agent compatibility.
Supports both mock mode (default) and real agent mode with --no-mock flag.

Usage:
    python scripts/gen_fixtures.py                # Mock mode (default)
    python scripts/gen_fixtures.py --no-mock      # Real Langroid agent mode

Output:
    Generates fixture files in agent_data/fixtures/
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def load_sample_queries() -> dict[str, str]:
    """Load sample query files from fixtures directory."""
    fixtures_dir = Path("agent_data/fixtures")
    queries = {}

    for i in [1, 2]:
        query_file = fixtures_dir / f"sample_query_{i}.txt"
        if query_file.exists():
            with open(query_file, encoding="utf-8") as f:
                queries[f"query_{i}"] = f.read().strip()

    return queries


def real_langroid_docchat_agent(query: str) -> dict[str, Any]:
    """
    Real Langroid DocChatAgent integration with OpenAI + Qdrant

    Uses:
    - OPENAI_API_KEY from environment
    - Qdrant cluster (QDRANT_CLUSTER1_ID, QDRANT_CLUSTER1_KEY, asia-southeast1)
    - Collection: test_documents (cleaned before run)
    - Embedding: text-embedding-3-small
    """
    try:
        import langroid as lr
        from langroid.agent.special.doc_chat_agent import DocChatAgent
        from langroid.utils.configuration import Settings, set_global
        from langroid.vector_store.qdrantdb import QdrantDBConfig
    except ImportError as e:
        raise ImportError(
            "langroid==0.58.0 is required for real agent mode. Install with: pip install langroid==0.58.0"
        ) from e

    # Check required environment variables
    required_env_vars = ["OPENAI_API_KEY", "QDRANT_CLUSTER1_ID", "QDRANT_CLUSTER1_KEY"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Configure Langroid settings
    settings = Settings(debug=False, cache=True, stream=False)
    set_global(settings)

    # Configure Qdrant connection
    qdrant_config = QdrantDBConfig(
        cloud=True,
        api_key=os.getenv("QDRANT_CLUSTER1_KEY"),
        url=f"https://{os.getenv('QDRANT_CLUSTER1_ID')}.asia-southeast1-0.aws.cloud.qdrant.io:6333",
        collection_name="test_documents",
        embedding=lr.embedding.models.OpenAIEmbeddingsConfig(
            model_type="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
        ),
        replace_collection=True,  # Clean collection before run
    )

    # Configure DocChatAgent
    agent_config = lr.agent.special.doc_chat_agent.DocChatAgentConfig(
        vecdb=qdrant_config,
        llm=lr.language_models.OpenAIGPTConfig(
            chat_model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")
        ),
    )

    # Create and run agent
    agent = DocChatAgent(agent_config)

    # Process query
    start_time = datetime.utcnow()
    response = agent.llm_response(query)
    end_time = datetime.utcnow()

    processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

    # Structure response as ToolMessage format
    return {
        "type": "ToolMessage",
        "content": {
            "query": query,
            "response": (
                response.content if hasattr(response, "content") else str(response)
            ),
            "collection_info": {
                "collection_name": "test_documents",
                "embedding_model": "text-embedding-3-small",
                "vector_dimension": 1536,  # text-embedding-3-small dimension
                "distance_metric": "cosine",
            },
        },
        "metadata": {
            "timestamp": start_time.isoformat() + "Z",
            "processing_time_ms": processing_time_ms,
            "model_version": "langroid-0.58.0",
            "embedding_model": "text-embedding-3-small",
            "collection_name": "test_documents",
            "qdrant_region": "asia-southeast1",
            "mock_data": False,
        },
    }


def mock_langroid_docchat_agent(query: str) -> dict[str, Any]:
    """
    MOCK: Simulate Langroid DocChatAgent response

    In real implementation, this would:
    1. Initialize DocChatAgent from langroid
    2. Process the query through the agent
    3. Return actual ToolMessage response

    For fixtures, we return structured mock data.
    """
    # MOCK: Generate timestamp for mock response
    timestamp = datetime.utcnow().isoformat() + "Z"

    # MOCK: Simulate different response types based on query content
    if "machine learning" in query.lower() or "deployment" in query.lower():
        return {
            "type": "ToolMessage",
            "content": {
                "query": query,
                "response": "Based on the document search, here are the key findings about ML model deployment strategies:\n\n**Containerization Approaches:**\n- Docker containers provide consistent deployment environments\n- Kubernetes orchestration for scalable model serving\n- Container registries for version management\n\n**Production Best Practices:**\n- Model versioning and A/B testing frameworks\n- Automated CI/CD pipelines for model updates\n- Health checks and monitoring endpoints\n\n**Monitoring Solutions:**\n- Model performance metrics tracking\n- Data drift detection systems\n- Resource utilization monitoring\n\nThe documents emphasize the importance of reproducible environments and robust monitoring for successful ML production deployments.",
                "sources": [
                    {
                        "document_id": "ml_deployment_guide_2024",
                        "relevance_score": 0.89,
                        "excerpt": "Container-based deployment provides isolation and reproducibility...",
                    },
                    {
                        "document_id": "production_ml_best_practices",
                        "relevance_score": 0.85,
                        "excerpt": "Monitoring model performance in production requires comprehensive metrics...",
                    },
                ],
            },
            "metadata": {
                "timestamp": timestamp,
                "processing_time_ms": 1250,
                "model_version": "langroid-0.58.0",
                "search_type": "semantic_similarity",
                "mock_data": True,
            },
        }
    else:
        # MOCK: Vector embeddings explanation response
        return {
            "type": "ToolMessage",
            "content": {
                "query": query,
                "response": "Vector embeddings are numerical representations of text, images, or other data that capture semantic meaning in high-dimensional space.\n\n**Core Concepts:**\n- Transform discrete data into continuous vector representations\n- Similar items have similar vector representations in embedding space\n- Enable mathematical operations on semantic content\n\n**Semantic Search Applications:**\n- Query and document vectors compared for relevance\n- Cosine similarity commonly used for text similarity\n- Dense retrieval systems outperform traditional keyword matching\n\n**Similarity Calculations:**\n- Cosine similarity: measures angle between vectors\n- Euclidean distance: measures geometric distance\n- Dot product: combines magnitude and direction\n\n**Dimensionality Reduction:**\n- PCA (Principal Component Analysis) for linear reduction\n- t-SNE for visualization of high-dimensional data\n- UMAP for preserving local and global structure\n- Helps reduce computational complexity while preserving semantic relationships",
                "vector_summary": {
                    "embedding_dimension": 384,
                    "similarity_threshold": 0.7,
                    "retrieval_method": "dense_passage_retrieval",
                },
            },
            "metadata": {
                "timestamp": timestamp,
                "processing_time_ms": 980,
                "model_version": "langroid-0.58.0",
                "response_type": "explanation",
                "mock_data": True,
            },
        }


def generate_fixtures(use_mock: bool = True):
    """Generate golden fixtures for Langroid agent testing."""
    mode = "MOCK" if use_mock else "REAL"
    print(f"🔧 Generating Golden Fixtures for Langroid Agent Pipeline ({mode} mode)...")

    if not use_mock:
        print("🌐 Using real Langroid DocChatAgent with OpenAI + Qdrant integration")
        print("🧹 Cleaning test_documents collection before run...")

    # Load sample queries
    queries = load_sample_queries()

    if not queries:
        print("❌ No sample queries found in agent_data/fixtures/")
        return

    fixtures_dir = Path("agent_data/fixtures")

    # Process each query and generate outputs
    for query_key, query_text in queries.items():
        print(f"📝 Processing {query_key}...")

        try:
            if use_mock:
                # MOCK: Simulate Langroid DocChatAgent processing
                response = mock_langroid_docchat_agent(query_text)
            else:
                # REAL: Use actual Langroid DocChatAgent
                response = real_langroid_docchat_agent(query_text)

            # Generate output filename
            query_num = query_key.split("_")[1]
            output_file = fixtures_dir / f"expected_output_{query_num}.json"

            # Save response to JSON file
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2, ensure_ascii=False)

            print(f"✅ Generated {output_file}")

        except Exception as e:
            print(f"❌ Error processing {query_key}: {e}")
            if not use_mock:
                print(
                    "💡 Ensure environment variables are set: OPENAI_API_KEY, QDRANT_CLUSTER1_ID, QDRANT_CLUSTER1_KEY"
                )
            raise

    print(f"\n🎯 Golden fixtures generated in {fixtures_dir} ({mode} mode)")
    print("📋 Fixture files:")
    for file in sorted(fixtures_dir.glob("*")):
        print(f"   - {file.name}")

    if use_mock:
        print("\n🔍 Next steps:")
        print("   1. Run: pytest -m fixture --cov=agent_data --disable-warnings")
        print("   2. Verify fixture structure in tests")
        print("   3. Update documentation in README_FIXTURES.md")
    else:
        print("\n🔍 Next steps:")
        print(
            "   1. Run: pytest tests/test_fixture_pipeline.py -m fixture --disable-warnings"
        )
        print(
            "   2. Verify CPG1.1 (Qdrant connectivity) and CPG1.2 (OpenAI connectivity)"
        )
        print("   3. Check that mock_data: false in generated files")


def main():
    parser = argparse.ArgumentParser(
        description="Generate golden fixtures for Langroid agent testing"
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Use real Langroid DocChatAgent instead of mock (requires OPENAI_API_KEY, QDRANT_CLUSTER1_ID, QDRANT_CLUSTER1_KEY)",
    )

    args = parser.parse_args()

    # Use mock mode by default, real mode with --no-mock
    use_mock = not args.no_mock

    generate_fixtures(use_mock=use_mock)


if __name__ == "__main__":
    main()
