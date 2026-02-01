from .BaseDataModel import BaseDataModel
from .db_schemas import Project
from .enums.DataBaseEnum import DataBaseEnum


class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        # 1. ask class to call init function
        instance = cls(db_client)
        # 2. ask class to call initialize_collection function
        await instance.initialize_collection()
        # 3. return instance object with combined functions
        return instance

    async def initialize_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_PROJECT_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
            indexes = Project.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"], name=index["name"], unique=index["unique"]
                )
    # Create a new project
    async def create_project(self, project: Project) -> Project:

        result = await self.collection.insert_one(
            project.model_dump(by_alias=True, exclude_unset=True)
        )
        return result.inserted_id

    # Get Project or Create new project
    async def get_project_or_create_one(self, project_id: str):
        record = await self.collection.find_one({"project_id": project_id})

        if record is None:
            project = Project(project_id=project_id)
            inserted_id = await self.create_project(project=project)
            record = await self.collection.find_one({"_id": inserted_id})

        return Project(**record)

    # Get All Projects "don't forget to use pagination with any get all method"
    async def get_all_projects(self, page: int = 1, page_size: int = 10):

        # count total number of documents
        total_documents = await self.collection.count_documents({})
        # Calculate total number of pages
        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1
        # for memory efficiency use cursor with pagination
        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)
        projects = []
        async for document in cursor:
            projects.append(Project(**document))

        return projects, total_pages
