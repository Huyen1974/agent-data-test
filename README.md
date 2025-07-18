# Agent Data Langroid

A modern knowledge management system built with Langroid for Google Cloud Platform.

## Project Overview

Agent Data Langroid is a next-generation agent-based data management system that leverages the power of Langroid framework to provide intelligent document processing, semantic search, and knowledge management capabilities. This project is designed to work seamlessly with Google Cloud services including Cloud Storage, Firestore, and Qdrant vector databases.

## Features

- **Multi-Agent Architecture**: Built on Langroid framework for sophisticated agent interactions
- **Vector Search**: Advanced semantic search using Qdrant vector database
- **Cloud Integration**: Native Google Cloud Platform integration
- **Document Processing**: Intelligent document ingestion and processing
- **Scalable Design**: Microservices architecture with containerized deployment
- **CI/CD Ready**: Comprehensive testing and deployment pipelines

## Architecture

```
agent_data/          # Core agent data management modules
├── agents/          # Langroid agent implementations
├── vector_store/    # Vector database integration
├── tools/           # Agent tools and utilities
└── config/          # Configuration management

tests/               # Test suites
scripts/             # Deployment and utility scripts
terraform/           # Infrastructure as Code
```

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry or pip-tools
- Google Cloud SDK
- Docker (for containerized deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/agent-data-langroid.git
cd agent-data-langroid
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify installation:
```bash
python -c "import langroid; print(f'Langroid version: {langroid.__version__}')"
```

### Development Setup

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Run pre-commit hooks:
```bash
pre-commit install
pre-commit run --all-files
```

## Configuration

The project uses environment-based configuration. Copy `.env.example` to `.env` and configure your settings:

```bash
# Google Cloud Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=asia-southeast1

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Langroid Configuration
LANGROID_API_KEY=your-api-key
```

## Deployment

### Local Development
```bash
# Start Qdrant locally
docker run -p 6333:6333 qdrant/qdrant

# Run the application
python -m agent_data.main
```

### Google Cloud Deployment
```bash
# Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply

# Deploy application
gcloud functions deploy agent-data-function --source .
gcloud run deploy agent-data-service --source .
```

## Testing

The project includes comprehensive test suites:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent_data

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -m "feat: add your feature"`
6. Push to the branch: `git push origin feature/your-feature`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please:
- Check the [documentation](docs/)
- Open an issue on GitHub
- Contact the development team

## Roadmap

- [ ] Enhanced multi-agent workflows
- [ ] Advanced vector search capabilities
- [ ] Real-time collaboration features
- [ ] Enhanced security and compliance
- [ ] Performance optimizations

---

Built with ❤️ using [Langroid](https://github.com/langroid/langroid) and Google Cloud Platform.
