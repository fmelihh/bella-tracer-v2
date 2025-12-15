# Bella Tracer v2 - GraphRAG Observability Platform

![Python](https://img.shields.io/badge/Python-3.12-blue)
![RAG](https://img.shields.io/badge/AI-Graph_RAG-purple)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)

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

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Synthetic Data Generator Pipeline               │
│                                                         │
│  • Generates complex trace patterns                    │
│  • Creates realistic log sequences                     │
│  • Publishes to Kafka                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
           ┌─────────────────┐
           │   Kafka Broker  │
           └─────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│     Knowledge Graph Parser Pipeline                     │
│                                                         │
│  • Consumes trace data from Kafka                      │
│  • Parses log entries into narrative format            │
│  • Builds knowledge graph with LLM extraction          │
│  • Stores in Neo4j with vector embeddings              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
           ┌─────────────────┐
           │   Neo4j Graph   │
           │   + Vectors     │
           └────────┬────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   REST API Endpoint   │
        │  /query - GraphRAG    │
        │  Powered by LangGraph │
        └───────────────────────┘
```

## Components

### Core Modules

| Module | Purpose |
|--------|---------|
| `api/app.py` | FastAPI REST endpoint for GraphRAG queries |
| `pipelines/synthetic_data_generator.py` | Generates realistic synthetic traces and logs |
| `pipelines/knowledge_graph_parser.py` | Converts trace data into knowledge graphs |
| `services/kafka.py` | Kafka producer/consumer management |
| `agent.py` | LangGraph agent orchestration for query processing |
| `models.py` | Pydantic models for request/response validation |

### Data Processing Pipeline

1. **Synthetic Data Generation**: Creates diverse trace patterns representing different scenarios
2. **Kafka Streaming**: Publishes generated logs to Kafka topics
3. **Knowledge Graph Building**: Consumes logs, extracts entities/relationships, builds Neo4j graph
4. **Vector Indexing**: Embeds chunk data for semantic search
5. **Query Interface**: Provides REST API for intelligent trace querying

## Installation & Setup

### Prerequisites

- Python 3.12+
- Neo4j 5.x
- Kafka 3.x (or use Docker)
- OpenAI API key

### Environment Configuration

Create a `.env` file in the project root:

```env
# Neo4j Configuration
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Kafka Configuration
KAFKA_BROKER=localhost:9092
KAFKA_TOPIC=data

# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
```

### Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

### Docker Setup

```bash
# Start Neo4j and Kafka using Docker Compose
docker-compose up -d
```

## Usage

### 1. Create Neo4j Vector Index

```bash
# Create vector index for semantic search
make neo4j-index

# Or directly
uv run create_neo4j_index
```

### 2. Run Data Pipelines

Start both synthetic data generation and knowledge graph parsing pipelines:

```bash
make run-flows
```

Or run individually:

```bash
# Synthetic data generator pipeline
uv run synthetic_data_generator_pipeline

# Knowledge graph parser pipeline
uv run knowledge_graph_parser_pipeline
```

### 3. Start API Server

```bash
# Start the FastAPI server
uv run api

# Server will be available at http://localhost:8000
```

### 4. Query the System

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What services failed in the last hour?"
  }'
```

## API Reference

### POST /query

Intelligent query endpoint powered by GraphRAG.

**Request:**
```json
{
  "question": "string"
}
```

**Response:**
```json
{
  "answer": "string",
  "original_question": "string",
  "optimized_question": "string",
  "extracted_dates": { },
  "context_sources": ["string"]
}
```

## Data Flow Example

### Trace Processing Stages

1. **Raw Log Entry** (JSON)
   ```json
   {
     "trace_id": "trace-123",
     "service_name": "api-gateway",
     "level": "ERROR",
     "message": "Database connection timeout",
     "metadata": [
       {"key": "pod_id", "value": "pod-456"},
       {"key": "db.statement", "value": "SELECT * FROM users"}
     ]
   }
   ```

2. **Narrative Extraction**
   ```
   Service 'api-gateway' (running on pod 'pod-456') 
   logged level ERROR with message: "Database connection timeout". 
   Context: executed database query 'SELECT * FROM users'
   ```

3. **Knowledge Graph Nodes & Relationships**
   - Nodes: Service, Trace, Pod, LogEntry, Database
   - Relationships: PART_OF_TRACE, RUNNING_ON, EXECUTED_QUERY

## Project Structure

```
bella-tracer-v2/
├── src/bella_tracer_v2/
│   ├── api/                          # FastAPI application
│   │   └── app.py
│   ├── pipelines/                    # ETL pipelines
│   │   ├── synthetic_data_generator.py
│   │   └── knowledge_graph_parser.py
│   ├── services/                     # External services
│   │   └── kafka.py
│   ├── agent.py                      # LangGraph agent
│   ├── models.py                     # Data models
│   ├── main.py                       # Entry points
│   └── synthetic_data.py             # Trace generation
├── artifacts/                        # Generated datasets
├── docker-compose.yaml               # Local environment
├── Makefile                          # Build commands
└── pyproject.toml                    # Project metadata
```

## Technologies

- **LangChain**: AI framework and tool integrations
- **LangGraph**: Agent orchestration and workflow
- **Neo4j GraphRAG**: Knowledge graph RAG
- **FastAPI**: REST API framework
- **Prefect**: Workflow orchestration
- **Kafka**: Distributed streaming
- **OpenAI**: LLM and embeddings
- **spaCy**: NLP processing
- **Pandas**: Data manipulation

## Contributing

Contributions are welcome! Please ensure:

- Code follows PEP 8 standards
- Tests are provided for new features
- Documentation is updated accordingly

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Status**: Beta - Under active development

**Last Updated**: December 2025
