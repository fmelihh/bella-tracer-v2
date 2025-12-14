from dotenv import load_dotenv
from bella_tracer_v2 import pipelines


load_dotenv()


def run_synthetic_data_generator_pipeline():
    print("Starting synthetic data generator pipeline...")
    pipelines.synthetic_data_generator.synthetic_data_generator_pipeline.serve()


def run_knowledge_graph_parser_pipeline():
    print("Starting knowledge graph parser pipeline...")
    pipelines.knowledge_graph_parser.knowledge_graph_parser.serve()
