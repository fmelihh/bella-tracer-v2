# Bella Tracer v2 - GraphRAG Observability Platform

![Python](https://img.shields.io/badge/Python-3.12-blue)
![RAG](https://img.shields.io/badge/AI-Graph_RAG-purple)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)

> **Available Languages**: [🇬🇧 English](README.en.md) | [🇹🇷 Türkçe](README.tr.md)

## Overview

**Bella Tracer v2** is an advanced observability platform that leverages **Graph Retrieval-Augmented Generation (GraphRAG)** and **Neo4j** to analyze and understand complex distributed system traces. The platform synthesizes synthetic logs, builds dynamic knowledge graphs from observability data, and provides intelligent querying capabilities powered by AI agents.

## Key Features

### 🤖 AI-Powered Query System
- **LangGraph-based Agent**: Intelligent query processing with question optimization and answer ranking
- **OpenAI Integration**: Advanced LLM and embedding capabilities
- **Multi-stage Processing**: Query optimization, document retrieval, and semantic reranking

### 📊 Knowledge Graph Management
- **Neo4j Backend**: Powerful graph database for relationship mapping
- **Dynamic Graph Building**: Automatic creation of nodes and relationships from trace data
- **Vector Search**: Semantic search capabilities with OpenAI embeddings

### 🔄 Data Pipeline Architecture
- **Synthetic Data Generation**: Complex trace pattern generation for testing and validation
- **Kafka Integration**: Real-time data streaming and processing
- **Prefect Workflows**: Orchestrated data pipelines for ETL operations

### 📈 Trace Analysis
- **Multi-Level Trace Processing**: Service, pod, and log entry correlation
- **Context Extraction**: Intelligent metadata parsing from observability logs
- **Relationship Mapping**: Automatic discovery of trace hierarchies and dependencies

## Technology Stack

- **LangChain**: AI framework and tool integrations
- **LangGraph**: Agent orchestration and workflow
- **Neo4j GraphRAG**: Knowledge graph RAG
- **FastAPI**: REST API framework
- **Prefect**: Workflow orchestration
- **Kafka**: Distributed streaming
- **OpenAI**: LLM and embeddings
- **spaCy**: NLP processing
- **Pandas**: Data manipulation

## Quick Start

### Prerequisites

- Python 3.12+
- Neo4j 5.x
- Kafka 3.x (or Docker)
- OpenAI API key

### Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env  # Edit with your credentials

# Start services
docker-compose up -d

# Create Neo4j index
make neo4j-index
```

### Running Pipelines

```bash
# Start data generation and knowledge graph pipelines
make run-flows

# Or start API server
uv run api
```

### Querying

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What services failed recently?"}'
```

## Project Structure

```
bella-tracer-v2/
├── src/bella_tracer_v2/
│   ├── api/                    # FastAPI application
│   ├── pipelines/              # ETL pipelines
│   ├── services/               # External service integrations
│   ├── agent.py                # LangGraph agent
│   └── models.py               # Data models
├── artifacts/                  # Generated datasets
├── docker-compose.yaml         # Local environment setup
└── pyproject.toml              # Project configuration
```

## Documentation

For detailed information, see:
- 📖 [English Documentation](README.en.md)
- 📖 [Turkish Documentation](README.tr.md)

## License

MIT License - see LICENSE file for details

## Support

For questions or issues, please open an issue on the repository.

---

**Status**: Beta - Under active development  
**Last Updated**: December 2025
