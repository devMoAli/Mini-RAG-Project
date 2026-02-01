from enum import Enum


class ResponseSignal(Enum):
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOADED_SUCCESS = "file_uploaded_success"
    FILE_UPLOADED_FAILED = "file_uploaded_failed"
    FILE_VALIDATION_SUCCESS = "file_validation_success"
    FILE_VALIDATION_FAILED = "file_validation_failed"
    FILE_PROCESSING_FAILED = "file_processing_failed"
    FILE_PROCESSED_SUCCESS = "file_processed_success"
    NO_FILES_FOUND_FOR_PROCESSING = "no_files_found_for_processing"

    NO_FILES_ERROR = "not_found_files_error"
    FILE_ID_ERROR = "no_file_found_with_given_id_error"
    PROJECT_NOT_FOUND_ERROR = "project_not_found_error"

    CHUNKING_ERROR = "chunking_error"
    INSERT_INTO_VECTOR_DB_ERROR = "insert_into_vector_db_error"
    INSERT_INTO_VECTOR_DB_SUCCESS = "insert_into_vector_db_success"

    GET_VECTOR_DB_COLLECTION_INFO_SUCCESS = "get_vector_db_collection_info_success"
    VECTOR_SEARCH_ERROR = "vector_search_error"
    VECTOR_SEARCH_SUCCESS = "vector_search_success"
    
    RAG_ANSWER_ERROR = "rag_answer_error"
    RAG_ANSWER_SUCCESS = "rag_answer_success"