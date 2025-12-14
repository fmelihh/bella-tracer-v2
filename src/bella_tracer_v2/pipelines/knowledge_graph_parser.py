import os
import json
import asyncio
from typing import Any

from neo4j import GraphDatabase
from prefect import flow, task, get_run_logger
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

from bella_tracer_v2.services.kafka import retrieve_aio_kafka_consumer

KAFKA_TOPIC = "data"
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

NODE_TYPES = ["Service", "Trace", "Scenario", "LogEntry", "Pod"]
REL_TYPES = ["PART_OF_TRACE", "EMITTED_BY", "RUNNING_ON", "IS_SCENARIO"]
PATTERNS = [
    ("LogEntry", "PART_OF_TRACE", "Trace"),
    ("LogEntry", "EMITTED_BY", "Service"),
    ("Service", "RUNNING_ON", "Pod"),
    ("Trace", "IS_SCENARIO", "Scenario"),
]


def create_narrative_from_trace(trace: dict[str, Any]) -> str:
    narrative_text = "OBSERVABILITY LOG ANALYSIS (SINGLE TRACE):\n\n"
    if not trace:
        return ""

    trace_id = trace.get("trace_id", "unknown-trace")

    narrative_text += f"--- START TRACE: {trace_id} ---\n"
    narrative_text += "Events Sequence:\n"

    service = log.get("service_name", "unknown-service")
    level = log.get("level", "INFO")
    msg = log.get("message", "")

    pod_id = "unknown-pod"
    context_details = []

    if "metadata" in trace and isinstance(trace["metadata"], list):
        for meta in trace["metadata"]:
            key = meta.get("key", "").lower()
            val = meta.get("value", "")

            if key == "pod_id":
                pod_id = val
                continue

            if "db.statement" in key:
                context_details.append(f"executed database query '{val}'")

            elif "http.method" in key:
                context_details.append(f"via HTTP {val}")
            elif "http.status" in key or "status_code" in key:
                context_details.append(f"returned status code {val}")
            elif "url" in key or "endpoint" in key:
                context_details.append(f"targeting endpoint '{val}'")

            elif "retry" in key:
                context_details.append(f"retry attempt #{val}")
            elif "error" in key or "exception" in key:
                context_details.append(f"encountered error '{val}'")

            elif "queue" in key or "topic" in key:
                context_details.append(f"using queue/topic '{val}'")

            else:
                context_details.append(f"{key}: {val}")

        narrative_text += f"- Service '{service}' (running on pod '{pod_id}') logged level {level} with message: \"{msg}\"."

        if context_details:
            details_str = ", ".join(context_details)
            narrative_text += f" Context attributes: [{details_str}]."

        narrative_text += "\n"

    narrative_text += f"--- END TRACE: {trace_id} ---\n"

    return narrative_text


@task(name="process_single_trace", retries=2, retry_delay_seconds=2)
async def process_single_trace(trace: dict[str, Any]):
    logger = get_run_logger()

    if not trace:
        return

    text_content = create_narrative_from_trace(trace)
    if not text_content:
        logger.warning("No logs found in trace data, skipping.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    try:
        trace_id = trace.get("trace_id", "unknown")
        logger.info(f"Processing single trace: {trace_id}")

        embedder = OpenAIEmbeddings(model="text-embedding-3-large")
        llm = OpenAILLM(
            model_name="gpt-4o",
            model_params={
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )

        kg_builder = SimpleKGPipeline(
            llm=llm,
            driver=driver,
            embedder=embedder,
            schema={
                "node_types": NODE_TYPES,
                "relationship_types": REL_TYPES,
                "patterns": PATTERNS,
            },
            on_error="IGNORE",
            from_pdf=False,
        )
        await kg_builder.run_async(text=text_content)
        logger.info(f"Successfully wrote trace {trace_id} to Neo4j.")

    except Exception as e:
        logger.error(f"Error processing trace: {e}")
        raise e
    finally:
        driver.close()


@flow(name="knowledge-graph-parser-pipeline", log_prints=True)
async def knowledge_graph_parser():
    logger = get_run_logger()
    logger.info(f"Connecting to Kafka topic: {KAFKA_TOPIC} for STREAM processing")

    consumer = await retrieve_aio_kafka_consumer(
        KAFKA_TOPIC, consumer_group="graph_rag_group_stream_v3"
    )
    await consumer.start()

    try:
        logger.info("Listening for messages...")
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                await process_single_trace(data)
                await consumer.commit()

            except json.JSONDecodeError:
                logger.error(
                    "Failed to decode JSON from Kafka message. Skipping but committing to move forward."
                )
                await consumer.commit()
                continue
            except Exception as e:
                logger.error(f"Critical error processing message: {e}")
                await asyncio.sleep(5)

    finally:
        logger.info("Stopping consumer...")
        await consumer.stop()
