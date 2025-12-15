import json

import numpy as np
from prefect import flow

from bella_tracer_v2 import services, synthetic_data


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super(NumpyEncoder, self).default(obj)


@flow(name="synthetic-data-generator")
async def synthetic_data_generator_pipeline():
    df = synthetic_data.generate_complex_traces(num_records=20)

    print("Starting Producer...")
    producer = await services.kafka.retrieve_aio_kafka_producer()
    await producer.start()

    for i, row in df.iterrows():
        print(f"Processing row {i}, {df['call_graph_pattern']}, {df['scenario']}")

        data = row["trace_data"]["logs"]
        for record in data:
            try:
                record = json.dumps(record, cls=NumpyEncoder).encode("utf-8")
            except Exception as e:
                print("An error occurred:", e)

            await producer.send("data", record)
