from sqlalchemy import text
from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenAIEnums
from openai import OpenAI
import logging


class OpenAIProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        api_url: str = None,
        # Tokens input & Output Cost
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)
        self.enums = OpenAIEnums
        self.logger = logging.getLogger(__name__)

    # function to set Generation Model which useful in runtime
    def get_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    # function to Embedding Model
    def get_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    # function to process text
    def process_text(self, text: str):
        if text is None:
            return ""
        return text[: self.default_input_max_characters].strip()

    # function to Generate Text
    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        # Validations
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None
        # If all went good return what expected
        max_output_tokens = (
            max_output_tokens
            if max_output_tokens
            else self.default_generation_max_output_tokens
        )
        temperature = (
            temperature if temperature else self.default_generation_temperature
        )
        chat_history.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        )
        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )
        # Validations
        if (
            not response
            or not response.choices
            or len(response.choices) == 0
            or not response.choices[0].message
        ):
            # If all went good return what expected
            self.logger.error("Error while generating text with OpenAI")
            return None
        return response.choices[0].message.content

    # function to Embed text
    def embed_text(self, text: str, document_type: str = None):
        # Validations
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None
        # If all went good we send msg to be converted to vector embedding
        response = self.client.embeddings.create(
            model=self.embedding_model_id,
            input=text,
        )
        # Validations
        if (
            not response
            or not response.data
            or len(response.data) == 0
            or not response.data[0].embedding
        ):
            self.logger.error("Error while Embedding text with OpenAI")
            return None
        # If all went good return what expected
        return response.data[0].embedding

    # function to Construct Prompt
    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": self.process_text(prompt)}
