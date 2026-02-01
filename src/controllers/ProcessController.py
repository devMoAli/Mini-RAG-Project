from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingEnum

class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    # 1. get file extension method
    def get_file_extension(self, file_id: str) -> str:

        # Logic to retrieve the file extension based on file_id
        return os.path.splitext(file_id)[-1]

    # 2. get file loader method
    def get_file_loader(self, file_id: str):

        file_path = os.path.join(self.project_path, file_id)
        file_extension = self.get_file_extension(file_id=file_id)
        # check if file exist first
        if not os.path.exists(file_path):
            return None

        if file_extension == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf8")
        elif file_extension == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    # 3. get File Content method
    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id=file_id)
        if loader:
            return loader.load()
        return None

    # 4. Process File Content method
    def process_file_content(
        self,
        file_content: list,
        file_id: str,
        chunk_size: int = 100,
        overlap_size: int = 20,
    ):

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=overlap_size, length_function=len
        )

        file_content_texts = [rec.page_content for rec in file_content]
        file_content_metadata = [rec.metadata for rec in file_content]

        chunks = text_splitter.create_documents(
            file_content_texts, metadatas=file_content_metadata
        )
        return chunks
