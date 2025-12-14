from fastapi import FastAPI
from bella_tracer_v2 import models, agent

app = FastAPI(title="GraphRAG Observability Service", version="1.0.0")


@app.post("/query", response_model=models.QueryResponse)
async def query_endpoint(request: models.QueryRequest):
    initial_state = {
        "original_question": request.question,
        "optimized_question": "",
        "extracted_filters": {},
        "retrieved_docs": [],
        "reranked_docs": [],
        "final_answer": "",
    }

    app_graph = agent.retrieve_graph()
    result = await app_graph.ainvoke(initial_state)

    sources = []
    for d in result["reranked_docs"]:
        snippet = d.get("text", "")[:150].replace("\n", " ") + "..."
        score = d.get("rerank_score", 0)
        sources.append(f"[Score: {score:.2f}] {snippet}")

    return models.QueryResponse(
        answer=result["final_answer"],
        original_question=result["original_question"],
        optimized_question=result["optimized_question"],
        extracted_dates=result["extracted_filters"],
        context_sources=sources,
    )
