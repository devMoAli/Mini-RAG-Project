import asyncio
import json
import os
import sys

try:
    from src.main import app, lifespan
    from src.controllers.NLPController import NLPController

    
    from src.models.db_schemas import Project
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


current_dir = os.path.dirname(os.path.abspath(__file__))
EVAL_DATA_PATH = os.path.join(current_dir, "questions.json")
TOP_K = 5


async def run_evaluation():
    async with lifespan(app):
       
        nlp = NLPController(
            generation_client=app.generation_client,
            embedding_client=app.embedding_client,
            vectordb_client=app.vectordb_client,
            template_parser=app.state.template_parser,
        )

        eval_project = Project(project_id="1")

        if not os.path.exists(EVAL_DATA_PATH):
            print(f"❌ Error: {EVAL_DATA_PATH} not found.")
            return
       
        collections = app.vectordb_client.client.get_collections()
        print(f"DEBUG: Real collections in Qdrant: {collections}")
        with open(EVAL_DATA_PATH, "r") as f:
            questions = json.load(f)

        hits = 0
        print(f"\n--- 🔍 RAG Retrieval Evaluation (Top-{TOP_K}) ---")

        for q in questions:
            query = q["question"]
            expected = q["expected_doc"]

            results = await nlp.retrieve(project=eval_project, query=query, top_k=TOP_K)
            retrieved_docs = [r["doc_name"] for r in results]
            is_hit = expected in retrieved_docs

            status = "✅ HIT" if is_hit else "❌ MISS"
            print(f"{status} | Q: {query[:40]}...")

            if not is_hit:
                print(f"   └─ Expected: {expected} | Found: {retrieved_docs}")
            else:
                hits += 1

        total = len(questions)
        print(f"\n--- Result: {(hits/total)*100:.2f}% ({hits}/{total}) ---")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
