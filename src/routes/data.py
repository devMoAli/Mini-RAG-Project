from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import os
import logging
import aiofiles
from typing import List
from bson import ObjectId

# Internal Imports
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignal
from routes.schemes.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.db_schemas import DataChunk, Asset
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


# ==========================================
# 1. UPLOAD ENDPOINT
# Handles multiple file uploads for a project
# ==========================================
@data_router.post("/upload/{project_id}")
async def upload_data(
    request: Request,
    project_id: str,
    files: List[UploadFile],  # Expecting a list of files from Postman key 'files'
    app_settings: Settings = Depends(get_settings),
):
    # Ensure the project exists in the DB before uploading
    project_model = await ProjectModel.create_instance(
        db_client=request.app.database_client
    )
    await project_model.get_project_or_create_one(project_id=project_id)

    data_controller = DataController()
    asset_model = await AssetModel.create_instance(
        db_client=request.app.database_client
    )
    uploaded_records = []

    for file in files:
        # Step A: Validate file type/extension
        is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
        if not is_valid:
            logger.warning(f"Skipping invalid file: {file.filename}")
            continue

        # Step B: Generate unique path on disk
        file_path, file_id = data_controller.generate_unique_file_path(
            original_filename=file.filename, project_id=project_id
        )

        # Step C: Save physical file to storage
        try:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            continue

        # Step D: Create database entry for the file (Asset)
        asset_resource = Asset(
            asset_project_id=project_id,
            asset_type=AssetTypeEnum.TYPE_FILE.value,
            asset_name=file_id,
            asset_size=os.path.getsize(file_path),
        )
        asset_record = await asset_model.create_asset(asset=asset_resource)
        uploaded_records.append(str(asset_record))

    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_UPLOADED_SUCCESS.value,
            "file_ids": uploaded_records,
            "count": len(uploaded_records),
        },
    )


# ==========================================
# 2. PROCESS ENDPOINT
# Chunks text from files and stores in Vector DB
# ==========================================
@data_router.post("/process/{project_id}")
async def process_endpoint(
    project_id: str,
    request: Request,
    process_request: ProcessRequest,
):
    file_id = process_request.file_id  # Single file target (optional)
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    asset_model = await AssetModel.create_instance(
        db_client=request.app.database_client
    )
    project_files_ids = {}

    # --- STEP 1: Determine scope (Single file vs All files) ---
    if file_id:
        # Targeted processing: Get record for a specific file_id
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project_id, asset_name=file_id
        )
        if asset_record:
            project_files_ids = {str(asset_record.id): asset_record.asset_name}
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"File {file_id} not found."},
            )
    else:
        # Bulk processing: Get all files belonging to this project
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project_id,
            asset_type=AssetTypeEnum.TYPE_FILE.value,
        )
        project_files_ids = {
            str(record.id): record.asset_name for record in project_files
        }

    if not project_files_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.NO_FILES_FOUND_FOR_PROCESSING.value},
        )

    # --- STEP 2: Setup Controllers and Models ---
    process_controller = ProcessController(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.database_client
    )

    # Delete existing chunks if a reset is requested
    if do_reset == 1:
        await chunk_model.delete_chunks_by_project_id(project_id=project_id)

    no_records = 0
    no_files = 0

    # --- STEP 3: The Processing Loop ---
    for asset_id, file_name in project_files_ids.items():
        # Get raw content from storage
        file_content = process_controller.get_file_content(file_id=file_name)
        if file_content is None:
            continue

        # Split content into smaller chunks
        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=file_name,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
        )

        if not file_chunks:
            continue

        # Prepare DataChunk objects for MongoDB
        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i + 1,
                chunk_project_id=project_id,
                chunk_asset_id=ObjectId(asset_id),  # Link chunk back to Asset
            )
            for i, chunk in enumerate(file_chunks)
        ]

        # Batch insert chunks into DB
        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    # --- STEP 4: Final Response (Outside the loop) ---
    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_PROCESSED_SUCCESS.value,
            "inserted_chunks": no_records,
            "processed_files": no_files,
        },
    )
