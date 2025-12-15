import os
import re
from datetime import datetime
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from neo4j import GraphDatabase

from bella_tracer_v2.models import GraphState, RankingOutput

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
    # filters = state["extracted_filters"] if state["extracted_filters"] else {}

    question = state["original_question"]
    trace_id_match = re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        question,
    )
    specific_trace_id = trace_id_match.group(0) if trace_id_match else None

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    docs = []

    try:
        if specific_trace_id:
            print(
                f"--> Trace ID Detected: {specific_trace_id}. Switching to Graph Traversal Mode."
            )

            cypher_query = """
            MATCH (t:Trace {trace_id: $trace_id})
            // Trace'e bağlı tüm logları çek
            MATCH (t)<-[:PART_OF_TRACE]-(log:LogEntry)
            
            // Context bilgilerini topla
            OPTIONAL MATCH (log)-[:EMITTED_BY]->(service:Service)
            OPTIONAL MATCH (log)-[:RUNNING_ON]->(pod:Pod)
            OPTIONAL MATCH (t)-[:IS_SCENARIO]->(scenario:Scenario)

            RETURN 
                log.message AS message,
                log.level AS level,
                log.timestamp AS timestamp,
                service.name AS service,
                pod.id AS pod,
                t.trace_id AS trace_id,
                scenario.name AS scenario,
                1.0 AS score
            ORDER BY log.timestamp ASC
            """

            records, _, _ = driver.execute_query(
                cypher_query, {"trace_id": specific_trace_id}
            )

        # ------------------------------------------------------------------
        # SENARYO B: Anlamsal Arama (Chunk -> LogEntry Bağlantısı ile)
        # ------------------------------------------------------------------
        else:
            print("--> No Trace ID. Using Vector Search.")
            embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
            query_vector = await embedding_model.aembed_query(
                state["optimized_question"]
            )

            cypher_query = """
            CALL db.index.vector.queryNodes('log_vector_index', 10, $embedding)
            YIELD node AS chunk, score
            
            // Varsayım: Entity extraction yapıldıysa LogEntry, Chunk ile bağlantılıdır.
            MATCH (log:LogEntry)-[:FROM_CHUNK|MENTIONS]->(chunk)
            
            MATCH (log)-[:EMITTED_BY]->(service:Service)
            OPTIONAL MATCH (log)-[:PART_OF_TRACE]->(t:Trace)
            OPTIONAL MATCH (t)-[:IS_SCENARIO]->(scenario:Scenario)

            RETURN 
                log.message AS message,
                log.level AS level,
                log.timestamp AS timestamp,
                service.name AS service,
                t.trace_id AS trace_id,
                scenario.name AS scenario,
                score
            ORDER BY score DESC
            """
            # NOT: Eğer veritabanınızda Chunk -> LogEntry ilişkisi 'FROM_CHUNK' değilse
            # (ki default pipeline'da bazen sadece Document-Chunk bağı olur),
            # o zaman text üzerinden eşleşme yapmak gerekebilir:
            # WHERE log.message IN chunk.text

            records, _, _ = driver.execute_query(
                cypher_query, {"embedding": query_vector}
            )

        for record in records:
            content = (
                f"[{record['timestamp']}] {record['level']} from {record['service']}:\n"
                f"Message: {record['message']}\n"
                f"Trace ID: {record['trace_id']}\n"
                f"Scenario: {record['scenario']}\n"
            )
            docs.append(
                {
                    "text": content,
                    "trace_id": record["trace_id"],
                    "score": record["score"],
                }
            )

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
    workflow.add_edge("optimize_query", "retrieval")
    # workflow.add_edge("extract_dates", "retrieval")
    workflow.add_edge("retrieval", "reranking")
    workflow.add_edge("reranking", "generation")
    workflow.add_edge("generation", END)

    app_graph = workflow.compile()

    return app_graph
