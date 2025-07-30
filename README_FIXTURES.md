# Golden Fixtures for Langroid Agent Testing

## Purpose

This directory contains golden fixtures for testing Langroid agent compatibility and ensuring consistent pipeline behavior. These fixtures provide reproducible test data for validating agent responses without making external API calls.

### What are Golden Fixtures?

Golden fixtures are static reference data that represent expected inputs and outputs for testing. They serve as:

- **Regression Testing**: Ensure changes don't break existing functionality
- **Offline Testing**: Test pipeline structure without external dependencies
- **Consistency Validation**: Verify response formats and data structures
- **Development Baseline**: Provide examples for new development

## Fixture Files

### Input Files

- **`sample_query_1.txt`**: User prompt about document lookup and ML deployment strategies
- **`sample_query_2.txt`**: User prompt requesting LLM explanation of vector embeddings

### Expected Output Files

- **`expected_output_1.json`**: Example ToolMessage response for document search query
- **`expected_output_2.json`**: Example response for explanation query with vector summary

## Output Structure

All expected outputs follow the ToolMessage format:

```json
{
  "type": "ToolMessage",
  "content": {
    "query": "Original user query",
    "response": "Agent response text",
    "sources": [...],      // Optional: for document search
    "vector_summary": {...} // Optional: for vector operations
  },
  "metadata": {
    "timestamp": "ISO 8601 timestamp",
    "processing_time_ms": 1250,
    "model_version": "langroid-0.58.0",
    "search_type": "semantic_similarity",
    "mock_data": true
  }
}
```

## Regenerating Fixtures

### Mock Mode (Default)

To regenerate mock fixtures (safe for CI):

```bash
python scripts/gen_fixtures.py
```

This mode uses mock data and does not require external API access.

### Real Agent Mode

To generate fixtures using real Langroid agent with OpenAI + Qdrant:

```bash
python scripts/gen_fixtures.py --no-mock
```

## Running Real Agent Tests

For real agent testing with OpenAI and Qdrant integration:

### Prerequisites

1. **Environment Variables**: Set the following in your environment:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export QDRANT_CLUSTER1_KEY="your-qdrant-api-key"
   export QDRANT_CLUSTER1_ID="your-qdrant-cluster-id"
   ```

2. **Dependencies**: Install Langroid:
   ```bash
   pip install langroid==0.58.0
   ```

### Real Agent Configuration

- **Collection**: `test_documents` (automatically cleaned before each run)
- **Schema**: Langroid creates automatically (cosine distance, 384-dim vectors)
- **Embedding Model**: `text-embedding-3-small` (OpenAI)
- **Region**: `asia-southeast1`
- **Clean Collection**: Yes, ensures reproducibility for CI runs

### Running Real Tests

```bash
# Generate real agent fixtures
python scripts/gen_fixtures.py --no-mock

# Run tests to validate CPG1.1 (Qdrant connectivity) and CPG1.2 (OpenAI connectivity)
pytest tests/test_fixture_pipeline.py -m fixture --disable-warnings
```

### Real Mode Validation

When using `--no-mock`, the tests validate:

- **CPG1.1 (Qdrant Connectivity)**: Response metadata cites `test_documents` collection
- **CPG1.2 (OpenAI Connectivity)**: Real responses generated with `mock_data: false`
- **Collection Info**: Proper embedding model and distance metric configuration
- **Regional Configuration**: Correct asia-southeast1 region usage

### CI Integration

Real agent tests are configured to run only:
- With `e2e` label on pull requests
- On manual workflow dispatch
- Never in normal CI to keep builds fast

This script:

1. Loads sample query files from `agent_data/fixtures/`
2. Processes each query through mock Langroid DocChatAgent
3. Generates structured JSON responses
4. Updates expected output files

**Note**: The generation script uses mock data (marked with `mock_data: true`) to avoid external API calls during testing.

## Running Fixture Tests

```bash
# Run all fixture tests
pytest -m fixture --cov=agent_data --disable-warnings

# Run with verbose output
pytest -m fixture --cov=agent_data --disable-warnings -v

# Run specific fixture test
pytest tests/test_fixture_pipeline.py -v
```

### Test Markers

- `@pytest.mark.fixture`: Identifies fixture-related tests
- `@pytest.mark.slow`: Marks tests that may take longer to run

## Consistency and Reproducibility

### Key Principles

1. **Deterministic**: Same input always produces same output
2. **Offline**: No external API dependencies (mock mode)
3. **Versioned**: Tied to specific Langroid version (0.58.0)
4. **Structured**: Consistent JSON schema for all outputs

### Validation

The test suite validates:

- File existence and accessibility
- JSON structure and required fields
- Content quality and completeness
- Metadata consistency across fixtures
- Offline mode compliance (mock_data flag)
- Real agent mode validation (when mock_data: false)

## Integration with CI/CD

Fixture tests are designed to run in CI environments:

- No external dependencies required (mock mode)
- Fast execution (< 5 seconds)
- Clear pass/fail criteria
- Coverage reporting included
- E2E tests only run with explicit trigger

## Future Enhancements

When expanding real agent testing:

1. Add more diverse query types and edge cases
2. Implement retry logic for transient network issues
3. Add performance benchmarking for response times
4. Expand collection management and cleanup utilities

## File Organization

```
agent_data/fixtures/
├── sample_query_1.txt          # Input query about ML deployment
├── sample_query_2.txt          # Input query about vector embeddings
├── expected_output_1.json      # Expected response for query 1
└── expected_output_2.json      # Expected response for query 2
```

## Version History

- **v0.1.0** (2024-07-30): Initial golden fixtures for Langroid 0.58.0
- Mock-based implementation for CI safety
- Comprehensive test suite with structure validation
- **v0.6b** (2025-07-30): Real OpenAI + Qdrant integration
- Added `--no-mock` flag for real agent testing
- CPG1.1 (Qdrant connectivity) and CPG1.2 (OpenAI connectivity) validation
- E2E workflow for controlled real agent testing

---

For questions or issues with fixtures, see the test suite in `tests/test_fixture_pipeline.py` or run the generator script for debugging.
