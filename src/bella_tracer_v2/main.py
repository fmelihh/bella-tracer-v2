import os

import uvicorn
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.indexes import create_vector_index

from bella_tracer_v2 import api, pipelines

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


def run_api():
    uvicorn.run(api.app.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # Uncomment the desired function to run

    # run_synthetic_data_generator_pipeline()
    # run_knowledge_graph_parser_pipeline()
    # create_neo4j_index()
    run_api()
