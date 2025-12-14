import json
from prefect import flow
from bella_tracer_v2 import synthetic_data, services


@flow(name="synthetic-data-generator")
async def synthetic_data_generator_pipeline():
    df = synthetic_data.generate_complex_traces(num_records=50)

    print("Starting Producer...")
    producer = await services.kafka.retrieve_aio_kafka_producer()
    await producer.start()

    for i, row in df.iterrows():
        print(f"Processing row {i}, {df['call_graph_pattern']}, {df['scenario']}")

        data = row["trace_data"]
        for record in data:
            try:
                record = json.dumps(record).encode("utf-8")
            except Exception as e:
                print("An error occurred:", e)

            await producer.send("data", record)
