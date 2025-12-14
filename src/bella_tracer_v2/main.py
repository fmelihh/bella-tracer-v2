import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.indexes import create_vector_index
from bella_tracer_v2 import pipelines


load_dotenv()


def run_synthetic_data_generator_pipeline():
    print("Starting synthetic data generator pipeline...")
    pipelines.synthetic_data_generator.synthetic_data_generator_pipeline.serve()


def run_knowledge_graph_parser_pipeline():
    print("Starting knowledge graph parser pipeline...")
    pipelines.knowledge_graph_parser.knowledge_graph_parser.serve()


def create_neo4j_index():
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    # Create the index
    create_vector_index(
        driver,
        "log_vector_index",
        label="Chunk",
        embedding_property="embedding",
        dimensions=3072,
        similarity_fn="euclidean",
    )
    driver.close()
