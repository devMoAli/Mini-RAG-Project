from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from routes.schemes.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from controllers.NLPController import NLPController
from models.ChunkModel import ChunkModel
from models import ResponseSignal
from fastapi.encoders import jsonable_encoder
import logging

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)


@nlp_router.post("/index/push/{project_id}")
async def index_project(
    request: Request,
    project_id: str,
    push_request: PushRequest,
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.database_client,
    )
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.database_client,
    )
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )
    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0

    while has_records:

        page_chunks = await chunk_model.get_chunks_by_project_id(
            project_id=project_id,
            page_no=page_no,
        )

        # Logic check: if no chunks returned, stop the loop
        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break

        # If we have chunks, move to next page for the next iteration
        page_no += 1

        chunks_ids = list(range(idx, idx + len(page_chunks)))
        idx += len(page_chunks)

        # Check if this controller method is async too!
        # If it is
        is_inserted = nlp_controller.index_into_vector_db(
            project=project,
            chunks=page_chunks,
            chunks_ids=chunks_ids,
            do_reset=push_request.do_reset if page_no == 2 else False,
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.INSERT_INTO_VECTOR_DB_ERROR.value},
            )

        inserted_items_count += len(page_chunks)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.INSERT_INTO_VECTOR_DB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        },
    )


@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(
    request: Request,
    project_id: str,
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.database_client,
    )
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )
    collection_info = nlp_controller.get_vector_db_collection_info(project=project)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.GET_VECTOR_DB_COLLECTION_INFO_SUCCESS.value,
            "collection_info": jsonable_encoder(collection_info),
        },
    )


@nlp_router.post("/index/search/{project_id}")
async def search_project_index(
    request: Request,
    project_id: str,
    search_request: SearchRequest,
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.database_client
    )
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    # Perform search
    results = await nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

    # If the controller returned None, it's a code/provider error
    if results is None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.VECTOR_SEARCH_ERROR.value,
                "results": [],
            },
        )

    # Success (even if results is an empty list [])
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.VECTOR_SEARCH_SUCCESS.value,
            "results": jsonable_encoder(results),
        },
    )


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(
    request: Request,
    project_id: str,
    search_request: SearchRequest,
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.database_client
    )
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )
    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project,
        query=search_request.text,
        limit=search_request.limit,
    )
    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        },
    )
