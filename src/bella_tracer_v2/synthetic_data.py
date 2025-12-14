import os
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from data_designer.essentials import (
    DataDesigner,
    DataDesignerConfigBuilder,
    SamplerColumnConfig,
    SamplerType,
    CategorySamplerParams,
    ModelProvider,
    ModelConfig,
    LLMStructuredColumnConfig,
)


class MetadataItem(BaseModel):
    key: str
    value: str


class LogEntry(BaseModel):
    trace_id: str = Field(
        ...,
        description="A unique UUID v4 string identifying the entire transaction. MUST be identical for every log in this list.",
    )
    span_id: str = Field(
        ...,
        description="A unique hexadecimal string (e.g., 16 chars) identifying this specific unit of work/operation.",
    )
    parent_span_id: Optional[str] = Field(
        default=None,
        description="The span_id of the service that called this service. Must be null/None for the root/entry-point service.",
    )
    service_name: str = Field(
        ...,
        description="The identifier of the microservice (e.g., 'payment-service', 'auth-api').",
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 formatted timestamp (e.g., '2023-10-27T10:00:00.123Z'). Ensure timestamps strictly follow causal order (parents start before children).",
    )
    level: str = Field(
        ...,
        description="The severity level of the log. Allowed values: DEBUG, INFO, WARN, ERROR, CRITICAL.",
    )
    message: str = Field(
        ...,
        description="A human-readable text description of the event (e.g., 'Processing payment', 'Database connection timeout').",
    )
    metadata: list[MetadataItem] = Field(
        default_factory=list,
        description="A list of max 3-5 key-value pairs relevant to the log (e.g., key='http.method', value='POST').",
    )


class TraceOutput(BaseModel):
    logs: list[LogEntry]


def generate_complex_traces(num_records: int = 50) -> pd.DataFrame:
    # 1. Setup Provider
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found.")

    openai_provider = ModelProvider(
        name="openai",
        endpoint="https://api.openai.com/v1",
        provider_type="openai",
        api_key=api_key,
    )

    # 2. Setup Model (Using a larger context model is better for complex JSON)
    gpt_config = ModelConfig(
        alias="gpt-structured",
        model="gpt-4o",
        provider="openai",
        inference_parameters={"temperature": 0.5, "max_tokens": 3024},
    )

    designer = DataDesigner(model_providers=[openai_provider])
    config = DataDesignerConfigBuilder(model_configs=[gpt_config])

    # --- Step 1: Define The "Shape" of the Trace (Topology) ---

    # instead of just a root service, we define a "Call Graph Pattern"
    # This dictates how services talk to each other.
    patterns = [
        "E-Commerce Checkout (Gateway -> Auth -> Order -> Payment & Inventory)",
        "Search Aggregation (Gateway -> SearchOrchestrator -> [Service A, Service B, Service C] in parallel)",
        "Async Report Generation (API -> Queue -> Worker -> S3 & EmailService)",
        "User Onboarding (Gateway -> Auth -> UserDB -> Notification -> Analytics)",
    ]

    config.add_column(
        SamplerColumnConfig(
            name="call_graph_pattern",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=patterns),
        )
    )

    # --- Step 2: Define The "Incident" (The Story) ---

    # Complex failure scenarios that require multi-service interaction
    scenarios = [
        "Cascading Failure: Database slow-down causes timeouts in upstream services",
        "Retry Storm: Payment service fails intermittently, causing OrderService to retry 3 times",
        "Partial Failure: Search works but 'Service B' returns error (Graceful degradation)",
        "Race Condition: Two requests modify UserDB simultaneously (Optimistic Locking Failure)",
        "Happy Path: Successful execution with high latency in one specific node",
    ]

    config.add_column(
        SamplerColumnConfig(
            name="scenario",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=scenarios),
        )
    )

    # --- Step 3: The Complex Graph Generator Prompt ---

    prompt_template = """
    You are a Distributed Tracing Engine Generator.

    TASK:
    Generate a highly detailed distributed trace (a list of log entries) for the following architecture:
    **Architecture Pattern**: {{ call_graph_pattern }}
    **Scenario/Incident**: {{ scenario }}

    REQUIREMENTS:
    1. **Topology**: You must simulate MULTIPLE distinct services (at least 4-6 services) interacting based on the pattern.
    2. **Causality**: Use `span_id` and `parent_span_id` to strictly define the call graph.
       - The entry point service has `parent_span_id: null`.
       - If Svc A calls Svc B, Svc B's `parent_span_id` MUST be Svc A's `span_id`.
    3. **Complexity**: 
       - Include strictly paired logs: "Starting request" AND "Finished request" for each span.
       - If the scenario involves retries, show the repeated calls with new span IDs but same parent.
       - Include "Network Latency" by adjusting timestamps realistically (e.g. child finishes 200ms after start).
    4. **Data Content**:
       - `trace_id`: MUST be identical for ALL logs in this list (Use a UUID).
       - `service_name`: distinct names (e.g., 'checkout-api', 'payment-svc-v1').
       - `metadata`: Add relevant keys like `http.status`, `db.statement`, `retry_count`, `pod_id`.
    
    Output the data strictly adhering to the provided `TraceOutput` schema.
    """

    config.add_column(
        LLMStructuredColumnConfig(
            name="trace_data",
            model_alias="gpt-structured",
            prompt=prompt_template,
            output_format=TraceOutput,
        )
    )

    # --- Generate ---
    print(f"Generating {num_records} complex distributed traces...")
    dataset = designer.create(config_builder=config, num_records=num_records)

    # Save
    df = dataset.load_dataset()
    return df


__all__ = ["generate_complex_traces"]
