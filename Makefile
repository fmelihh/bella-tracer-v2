run-flows:
	prefect config set PREFECT_API_URL="http://0.0.0.0:4200/api" && \
	uv run knowledge_graph_parser_pipeline & \
	uv run synthetic_data_generator_pipeline