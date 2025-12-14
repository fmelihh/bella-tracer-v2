import os
from typing import List
from datetime import datetime

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from bella_tracer_v2.models import GraphState, RankingOutput

from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class OpenAIRerankerService:
    def __init__(self, model_name="gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.parser = JsonOutputParser(pydantic_object=RankingOutput)

    async def rerank(self, query: str, docs: List[dict], top_k: int = 5) -> List[dict]:
        if not docs:
            return []

        docs_text = ""
        for i, doc in enumerate(docs):
            content = doc.get("text", "")
            meta = {k: v for k, v in doc.items() if k != "text"}
            docs_text += f"--- DOC ID {i} ---\nContent: {content}\nMetadata: {meta}\n\n"

        prompt = ChatPromptTemplate.from_template(
            """You are an expert Observability and Log Analysis assistant.
            Your task is to rerank the provided log documents based on their relevance to the user's query.

            Criteria for relevance:
            1. Direct relation to the error/service in the query.
            2. High severity levels (ERROR/CRITICAL) are prioritized over INFO.
            3. Root cause indicators (exceptions, timeouts found in related logs).
            4. Temporal proximity.

            User Query: {query}

            Documents to Rank:
            {docs_text}

            Return a JSON object containing a list of the most relevant documents sorted by score (descending).
            Only return the top {top_k} documents.

            {format_instructions}
            """
        )

        chain = prompt | self.llm | self.parser

        try:
            result = await chain.ainvoke(
                {
                    "query": query,
                    "docs_text": docs_text,
                    "top_k": top_k,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )

            reranked_docs = []
            for item in result.get("ranked_results", []):
                idx = item["index"]
                if 0 <= idx < len(docs):
                    original_doc = docs[idx]
                    original_doc["rerank_score"] = item["relevance_score"]
                    original_doc["rerank_reason"] = item["reasoning"]
                    reranked_docs.append(original_doc)

            return reranked_docs

        except Exception as e:
            print(f"OpenAI Reranking Error: {e}")
            return docs[:top_k]


reranker_service = OpenAIRerankerService()


async def optimize_query_node(state: GraphState):
    print("--- STEP 1: Optimizing Query ---")
    question = state["original_question"]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_template(
        """You are an expert at refining search queries for log analysis.
        Rewrite the user question to be a concise, keyword-heavy search query suited for vector retrieval.
        Keep entity names (Pod IDs, Service Names, Trace IDs) exactly as is.

        User Question: {question}
        Optimized Query:"""
    )

    chain = prompt | llm
    response = await chain.ainvoke({"question": question})

    return {"optimized_question": response.content.strip()}


async def extract_dates_node(state: GraphState):
    print("--- STEP 2: Extracting Dates ---")
    question = state["original_question"]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_template(
        """Analyze the user question and extract time range filters.
        Return JSON with keys 'start_date' and 'end_date' (ISO 8601 format: YYYY-MM-DDTHH:MM:SS).
        If no date is specified, return null.
        current_time: {current_time}

        User Question: {question}
        JSON Output:"""
    )

    chain = prompt | llm | parser
    try:
        filters = await chain.ainvoke(
            {"question": question, "current_time": datetime.now().isoformat()}
        )
    except Exception:
        filters = {"start_date": None, "end_date": None}

    return {"extracted_filters": filters}


async def retrieval_node(state: GraphState):
    print("--- STEP 3: Retrieving with Graph Traversal ---")
    query_text = state["optimized_question"]
    filters = state["extracted_filters"] if state["extracted_filters"] else {}

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    try:
        embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
        query_vector = await embedding_model.aembed_query(query_text)

        cypher_query = """
        // 1. ADIM: Vektör araması ile Anchor Logları bul
        CALL db.index.vector.queryNodes('log_vector_index', 15, $embedding)
        YIELD node AS targetLog, score

        // --- TARİH FİLTRESİ EKLEMESİ ---
        WHERE ($start_date IS NULL OR targetLog.timestamp >= $start_date)
          AND ($end_date IS NULL OR targetLog.timestamp <= $end_date)

        // 2. ADIM: Context Genişletme (Service, Pod, Trace, Scenario)
        MATCH (targetLog)-[:EMITTED_BY]->(service:Service)
        OPTIONAL MATCH (targetLog)-[:RUNNING_ON]->(pod:Pod)
        OPTIONAL MATCH (targetLog)-[:PART_OF_TRACE]->(trace:Trace)-[:IS_SCENARIO]->(scenario:Scenario)

        // 3. ADIM: ROOT CAUSE ANALİZİ (Dependency Traversal)
        OPTIONAL MATCH (trace)<-[:PART_OF_TRACE]-(priorLog:LogEntry)
        WHERE priorLog.timestamp < targetLog.timestamp 
          AND priorLog.level IN ['ERROR', 'CRITICAL', 'WARN']
          AND priorLog <> targetLog

        OPTIONAL MATCH (priorLog)-[:EMITTED_BY]->(causeService:Service)

        // 4. ADIM: Sonuçları Derle
        RETURN 
            targetLog.message AS log_message,
            targetLog.level AS log_level,
            targetLog.timestamp AS log_time,
            service.name AS service_name,
            pod.id AS pod_id,
            trace.trace_id AS trace_id,
            scenario.name AS scenario,

            // Kök neden adaylarını birleştir
            collect(DISTINCT {
                service: causeService.name,
                message: priorLog.message,
                level: priorLog.level,
                time: priorLog.timestamp
            }) AS potential_root_causes,
            score
        ORDER BY score DESC
        """

        records, _, _ = driver.execute_query(
            cypher_query,
            {
                "embedding": query_vector,
                "start_date": filters.get("start_date"),
                "end_date": filters.get("end_date"),
            },
            database_="neo4j",
        )

        docs = []
        for record in records:
            content = (
                f"Log Event: '{record['log_message']}' (Level: {record['log_level']})\n"
                f"Source: Service '{record['service_name']}' on Pod '{record['pod_id']}'\n"
                f"Trace ID: {record['trace_id']}\n"
                f"Scenario: {record['scenario']}\n"
            )

            root_causes = [
                rc for rc in record["potential_root_causes"] if rc["message"]
            ]
            if root_causes:
                content += "POTENTIAL ROOT CAUSES (Preceding errors in this trace):\n"
                for rc in root_causes:
                    content += f"  - Service '{rc['service']}' logged {rc['level']}: '{rc['message']}'\n"
            else:
                content += "No preceding errors found in this trace.\n"

            metadata = {
                "trace_id": record["trace_id"],
                "service": record["service_name"],
                "score": record["score"],
            }

            docs.append({"text": content, **metadata})

    except Exception as e:
        print(f"Graph Retrieval Error: {e}")
        docs = []
    finally:
        driver.close()

    return {"retrieved_docs": docs}


async def reranking_node(state: GraphState):
    print("--- STEP 4: Reranking ---")
    query = state["optimized_question"]
    docs = state["retrieved_docs"]

    if not docs:
        return {"reranked_docs": []}

    reranked = await reranker_service.rerank(query, docs, top_k=5)
    return {"reranked_docs": reranked}


async def generation_node(state: GraphState):
    print("--- STEP 5: Generating Answer ---")
    question = state["original_question"]
    context_docs = state["reranked_docs"]

    context_text = "\n\n".join(
        [
            f"Doc (Score: {d.get('rerank_score', 0):.2f}):\n{d.get('text', '')}"
            for d in context_docs
        ]
    )

    if not context_text:
        context_text = "No relevant logs found."

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_template(
        """You are an advanced Site Reliability Engineer (SRE) AI assistant.
        Answer the user's question based strictly on the provided log context.
        The context is enhanced with Graph relationships (Upstream/Downstream errors).

        Directives:
        1. Identify the root cause if an error is present. Look at the "POTENTIAL ROOT CAUSES" section in the logs.
        2. If Service B failed, check if Service A failed before it. Connect these dots.
        3. Mention specific Pod IDs, Trace IDs, and timestamps.
        4. If the answer is not in the logs, state that clearly.

        Context:
        {context}

        User Question: {question}

        Answer:"""
    )

    chain = prompt | llm
    response = await chain.ainvoke({"context": context_text, "question": question})

    return {"final_answer": response.content}


def retrieve_graph() -> CompiledStateGraph:
    workflow = StateGraph(GraphState)

    workflow.add_node("optimize_query", optimize_query_node)
    workflow.add_node("extract_dates", extract_dates_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("reranking", reranking_node)
    workflow.add_node("generation", generation_node)

    workflow.set_entry_point("optimize_query")
    workflow.add_edge("optimize_query", "extract_dates")
    workflow.add_edge("extract_dates", "retrieval")
    workflow.add_edge("retrieval", "reranking")
    workflow.add_edge("reranking", "generation")
    workflow.add_edge("generation", END)

    app_graph = workflow.compile()

    return app_graph
