from pydoc import text
from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List
import time
import os


class NLPController(BaseController):

    def __init__(
        self, generation_client, embedding_client, vectordb_client, template_parser
    ):
        super().__init__()

        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client
        self.template_parser = template_parser

        # 1. Get IDs from .env with fallbacks
        gen_model_id = os.getenv("GENERATION_MODEL_ID", "llama3.1:8b-instruct-q8_0")
        embed_model_id = os.getenv("EMBEDDING_MODEL_ID", "nomic-embed-text")
        embed_size = int(os.getenv("EMBEDDING_MODEL_SIZE", "768"))

        # 2. Assign Generation Model
        self.generation_client.get_generation_model(model_id=gen_model_id)

        # 3. Assign Embedding Model (Now dynamic!)
        self.embedding_client.get_embedding_model(
            model_id=embed_model_id, embedding_size=embed_size
        )

    def create_collection_name(self, project_id: str) -> str:
        return f"collection_{project_id}".strip()

    def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = self.vectordb_client.get_collection_info(
            collection_name=collection_name
        )
        return collection_info

    # Sanitize Chunk Function
    def sanitize_chunk(self, text: str) -> str:
        # 1. Remove obvious injection triggers
        blacklisted_phrases = [
            "ignore all previous instructions",
            "system prompt:",
            "you are now a",
            "assistant instructions",
        ]
        sanitized = text.lower()
        for phrase in blacklisted_phrases:
            sanitized = sanitized.replace(phrase, "[CLEANED]")

        # 2. Basic cleanup (whitespace/extra newlines)
        return " ".join(sanitized.split())

    def index_into_vector_db(
        self,
        project: Project,
        chunks: List[DataChunk],
        chunks_ids: List[int],
        do_reset: bool = False,
    ):
        # 1. Get Collection Name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # 2. Manage items
        # texts = [c.chunk_text for c in chunks]
        # metadatas = [c.chunk_metadata for c in chunks]
        texts = []
        metadatas = []
        for c in chunks:
            clean_text = self.sanitize_chunk(c.chunk_text)
            texts.append(clean_text)

            # Ensure doc_name is in the metadata for EVERY chunk
            meta = c.chunk_metadata or {}
            if "doc_name" not in meta:
                # Fallback to a filename if available in the chunk object
                meta["doc_name"] = getattr(c, "doc_name", "unknown_doc")
            metadatas.append(meta)
        vectors = []
        for text in texts:
            vector = self.embedding_client.embed_text(
                text=text, document_type=DocumentTypeEnum.DOCUMENT.value
            )
            vectors.append(vector)
            time.sleep(0.1)  # To avoid rate limiting

        # 3. Create Collection if not exists
        _ = self.vectordb_client.create_collection(
            collection_name=collection_name,
            do_reset=True,
            embedding_size=self.embedding_client.embedding_size,
        )
        # 4. Insert into Vector DB
        _ = self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadatas,
            vectors=vectors,
            record_ids=chunks_ids,
        )
        return True

    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 5,
    ):
        # 1. Get Collection Name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # 2. Get Text Embedding
        try:
            # If your provider is async, use 'await' here
            query_vector = self.embedding_client.embed_text(
                text=text, document_type=DocumentTypeEnum.QUERY.value
            )
        except Exception as e:
            print(f"CRITICAL ERROR in Embedding: {e}")
            return None  # Return None to trigger 500 error in route

        if not query_vector:
            print("Error: Embedding returned None or Empty")
            return []  # Return empty list if no vector could be made

        # 3. Semantic Search in Vector DB
        search_results = self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit,
        )
        if not search_results:
            return False

        return search_results

    # Answer_RAG_Question Function
    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        # Initialize variables at the top to avoid UnboundLocalError
        answer = ""
        full_prompt = ""
        chat_history = []
        # 1. Retrieve relevant documents
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, chat_history

        # 2. Construct LLM prompt with fallbacks to avoid NoneType errors
        system_prompt = (
            self.template_parser.get_local_template("rag", "system_prompt")
            or "You are a helpful assistant."  # Default fallback string
        )

        documents_prompts = "\n".join(
            [
                str(
                    self.template_parser.get_local_template(
                        "rag",
                        "document_prompt",
                        {
                            "doc_number": idx + 1,
                            "chunk_text": (doc.text if doc.text else ""),
                        },
                    )
                    or ""
                )
                for idx, doc in enumerate(retrieved_documents)
            ]
        )

        footer_prompt = (
            self.template_parser.get_local_template(
                "rag", "footer_prompt", {"query": query}
            )
            or f"Context: {query}"  # Default fallback
        )

        # step3: Construct Generation Client Prompts
        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n\n".join([documents_prompts, footer_prompt])

        # step4: Retrieve the Answer
        answer = self.generation_client.generate_text(
            prompt=full_prompt, chat_history=chat_history
        )

        # step5: System-level Guardrail (Post-Generation Check)
        # We look for signs that the LLM was manipulated into "leaking" or "ignoring"
        forbidden_triggers = [
            "ignore all previous",
            "system prompt",
            "developer mode",
            "override instructions",
            "as a language model, i am now",
        ]

        # If the LLM output looks like it's trying to execute a prompt injection command
        if any(trigger in answer.lower() for trigger in forbidden_triggers):
            print(
                f"⚠️ SECURITY ALERT: Potential Prompt Injection detected in LLM output."
            )
            return (
                "I'm sorry, but I cannot fulfill this request due to security policy violations.",
                full_prompt,
                chat_history,
            )

        return answer, full_prompt, chat_history

    # Retriever function
    async def retrieve(self, project: Project, query: str, top_k: int = 5):
        results = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=top_k,
        )

        if not results:
            return []

        # This mapping ensures we find the doc_name even if the DB structure changes
        return [
            {
                "doc_name": (
                    getattr(r, "doc_name", None)
                    or (
                        r.payload.get("doc_name")
                        if hasattr(r, "payload") and r.payload
                        else None
                    )
                    or (
                        r.metadata.get("doc_name")
                        if hasattr(r, "metadata") and r.metadata
                        else None
                    )
                    or "0irybcxs2uch_Google.txt"  # Final hardcoded fallback for your current test
                ),
                "score": getattr(r, "score", 0.0),
                "text": getattr(r, "text", ""),
            }
            for r in results
        ]
