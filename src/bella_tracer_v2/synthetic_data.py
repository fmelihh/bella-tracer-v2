import os
from dotenv import load_dotenv
from data_designer.essentials import (
    DataDesigner,
    DataDesignerConfigBuilder,
    LLMTextColumnConfig,
    SamplerColumnConfig,
    SamplerType,
    CategorySamplerParams,
    ModelProvider,
    ModelConfig,
)

load_dotenv()


def generate_synthetic_data(num_records: int = 50):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    openai_provider = ModelProvider(
        name="openai",
        endpoint="https://api.openai.com/v1",
        provider_type="openai",
        api_key=api_key,
    )

    designer = DataDesigner(model_providers=[openai_provider])

    gpt_config = ModelConfig(
        alias="gpt-5",
        model="gpt-4o-mini",
        provider="openai",
        inference_parameters={"temperature": 0.7, "max_tokens": 4096},
    )

    config = DataDesignerConfigBuilder(model_configs=[gpt_config])

    services = [
        "PaymentGateway",
        "OrderService",
        "InventoryDB",
        "AuthService",
        "NotificationSvc",
    ]
    config.add_column(
        SamplerColumnConfig(
            name="root_service",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=services),
        )
    )

    scenarios = [
        "High Latency (Timeout)",
        "Database Connection Refused",
        "Invalid API Key",
        "Successful Transaction",
        "Memory Leak OOM",
    ]
    config.add_column(
        SamplerColumnConfig(
            name="scenario",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=scenarios),
        )
    )

    # --- Step 2: Use LLM to Generate the Graph Structure ---
    prompt_template = """
    You are a distributed systems simulator. 
    Generate a JSON object representing a distributed trace for a request starting at {{ root_service }}.
    The scenario is: {{ scenario }}.

    The output must be a valid JSON list of log entries. Each entry must have:
    - "trace_id": (Generate a unique UUID)
    - "span_id": (Unique ID)
    - "parent_span_id": (ID of caller, null if root)
    - "service_name": (Name of the service)
    - "timestamp": (ISO format)
    - "level": (INFO, WARN, ERROR)
    - "message": (Realistic log message)
    - "metadata": { "http.method": "...", "db.query": "..." }

    Ensure the logs tell a coherent story where one service calls another, and the error propagates up the stack.
    Return ONLY the raw JSON list, no markdown formatting.
    """

    config.add_column(
        LLMTextColumnConfig(
            name="raw_trace_json",
            model_alias="gpt-5",
            prompt=prompt_template,
        )
    )

    # --- Step 3: Generate ---
    print("Generating Synthetic Traces...")
    dataset = designer.create(config_builder=config, num_records=num_records)

    # Save
    dataset.load_dataset().to_json(
        "synthetic_traces.jsonl", orient="records", lines=True
    )
    print("Done! Check synthetic_traces.jsonl")


if __name__ == "__main__":
    generate_synthetic_data()
