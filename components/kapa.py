from typing import TYPE_CHECKING, Any, List, Text, Dict, Optional
from dataclasses import dataclass

import time
import aiohttp
import json
import asyncio
import urllib.parse

import structlog
from rasa.utils.endpoints import EndpointConfig
from rasa.core.information_retrieval import (
    SearchResultList,
    InformationRetrieval,
    InformationRetrievalException,
)

if TYPE_CHECKING:
    # from langchain.schema import Document
    from langchain.schema.embeddings import Embeddings

structlogger = structlog.get_logger()

class SearchResult:
    def __init__(self, text: str, metadata: Dict, score: Optional[float] = None):
        self.text = text
        self.metadata = metadata
        self.score = score

@dataclass
class SearchResultList:
    results: List[SearchResult]
    metadata: Dict

class KapaInformationRetrievalException(InformationRetrievalException):
    """Exception raised for errors in the Kapa."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()

    def __str__(self) -> str:
        return self.base_message + self.message + f"{self.__cause__}"

class Kapa(InformationRetrieval):
    """Kapa implementation."""

    def __init__(
        self,
        embeddings: "Embeddings",
    ):
        structlogger.debug("kapa.__init__")
        self.embeddings = embeddings
        self.token = None
        self.url = None
        self.project_id = None
        self.endpoint_type = None

    def connect(self, config: EndpointConfig) -> None:
        """Setup to Kapa values."""
        config_dict = vars(config)
        structlogger.debug("kapa.connect", config_dict=config_dict)
        kapa_args = config.kwargs
        structlogger.debug("kapa.connect", config_dict=config_dict, kapa_args=kapa_args, kapa_endpoint_type=kapa_args.get('kapa_endpoint_type'), kapa_project_id=kapa_args.get('kapa_project_id'), kapa_num_results=kapa_args.get('kapa_num_results'))
        
        self.token = kapa_args.get("kapa_token")
        if not self.token:
            raise KapaInformationRetrievalException(
                "Kapa token not set."
            )
        self.project_id = kapa_args.get("kapa_project_id")
        if not self.project_id:
            raise KapaInformationRetrievalException(
                "Kapa project id not set."
            )
        if not kapa_args.get("kapa_endpoint_type"):
            self.endpoint_type = "search"
            structlogger.warning("kapa.connect", warning="kapa_endpoint_type not set in endpoints.yml, setting to 'search'")
        else:
            self.endpoint_type = kapa_args.get("kapa_endpoint_type")
        # self.endpoint_type = config_dict.kapa_endpoint_type if config_dict.kapa_endpoint_type else "chat"
        # self.integration_id = config_dict.kapa_integration_id
        if self.endpoint_type == "search":
            # Docs: https://docs.kapa.ai/api#tag/Search
            # https://api.kapa.ai/query/v1/projects/{project_id}/search/
            self.url = f"https://api.kapa.ai/query/v1/projects/{self.project_id}/search/"
        if self.endpoint_type == "chat":
            # Docs: https://docs.kapa.ai/api#tag/Chat/operation/query_v1_projects_chat
            # https://api.kapa.ai/query/v1/projects/{project_id}/chat/
            self.url = f"https://api.kapa.ai/query/v1/projects/{self.project_id}/chat/"
        if kapa_args.get("kapa_num_results"):
            self.num_results = int(kapa_args.get("kapa_num_results"))
        else:
            self.num_results = 3

    def _create_chat_results(self, kapa_json: dict) -> SearchResultList:
        structlogger.debug("kapa._create_chat_results", kapa_json=kapa_json, type=type(kapa_json))
        # Extract answer text
        answer_text = kapa_json.get("answer")
        
        # Extract metadata from the first relevant source
        if kapa_json["relevant_sources"]:
            metadata = kapa_json["relevant_sources"][0]
        else:
            metadata = {}
        structlogger.debug("kapa._create_chat_results", answer_text=answer_text, metadata=metadata)
        
        # Create SearchResult object
        search_result = SearchResult(text=answer_text, metadata=metadata)
        
        # Create SearchResultList object
        search_result_list = SearchResultList(results=[search_result], metadata={})
        
        return search_result_list

    async def kapa_query_chat(self, query_string: str):
        structlogger.debug("kapa.kapa_query_chat", url=self.url, query_string=query_string)
        headers = {
            'X-API-KEY': self.token,
            'Content-Type': 'application/json'
        }
        # set payload body, value for query to query_string
        payload = json.dumps({
            "query": query_string,
            "num_results": self.num_results
        })

        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, data=payload, timeout=18) as response:
                    response_json = await response.json()
                    # calc trans time in ms
                    trans_time = (time.time() - start_time) * 1000
                    structlogger.debug("kapa.kapa_query_chat.kapa_response", trans_time=trans_time, response_json=response_json, response_type=type(response_json), response_json_type=type(response_json))
                    # Check if the response status is OK
                    if response.status == 200:
                        response = await response.json()  # Assuming the response is in JSON format
                        answer = self._create_chat_results(response)
                        return answer
                    else:
                        # Handle HTTP errors
                        raise KapaInformationRetrievalException(
                            f"Kapa search http error. HTTP Error when calling the knowledge base: {response.status}, url: {self.url}, headers: {headers}, response: {response}"
                        ) from e
                        return f"HTTP Error when calling the knowledge base"
                    # return response_json
        except asyncio.TimeoutError as e:
            # return "Kapa timeout"
            raise KapaInformationRetrievalException(
                f"Kapa search timeout. Encountered error: {str(e)}, url: {self.url}, headers: {headers}"
            ) from e
        except Exception as e:
            raise KapaInformationRetrievalException(
                f"Kapa search failed. Encountered error: {str(e)}, url: {self.url}, headers: {headers}"
            ) from e

    @staticmethod
    def _create_search_results(response_json: dict) -> SearchResultList:
        """Helper method to create search results from API response."""
        results = SearchResultList(results=[], metadata={})

        # 1) Fetch search results and combine them all into one single result
        search_results = response_json["search_results"]
        answer = "\n".join([search_result["content"] for search_result in search_results])

        # 2) Initialize the SearchResult instance and append it to the list
        # TODO Fix metadata to not be the first element, but proper items
        results.results.append(
            SearchResult(
                text=answer,
                metadata={
                    "answer": answer,
                    "source_url": search_results[0].get("source_url"),
                    "title": search_results[0].get("title"),
                    "source_type": search_results[0].get("source_type"),
                },
            )
        )
        return results

    async def kapa_query_search(self, query_string: str):
        structlogger.debug("kapa.kapa_query_search", url=self.url, query_string=query_string)
        headers = {
            'X-API-KEY': self.token,
            'Content-Type': 'application/json'
        }
        # set payload body, value for query to query_string
        payload = json.dumps({
            "query": query_string,
            "num_results": self.num_results
        })

        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, data=payload, timeout=18) as response:
                    response_json = await response.json()
                    # calc trans time in ms
                    trans_time = (time.time() - start_time) * 1000
                    structlogger.debug("kapa.kapa_query_search.kapa_response", trans_time=trans_time, response_json=response_json, response_type=type(response_json), response_json_type=type(response_json))
                    # Check if the response status is OK
                    if response.status == 200:
                        response = await response.json()  # Assuming the response is in JSON format
                        answer = self._create_search_results(response)
                        return answer
                    else:
                        # Handle HTTP errors
                        raise KapaInformationRetrievalException(
                            f"Kapa search http error. HTTP Error when calling the knowledge base: {response.status}, url: {self.url}, headers: {headers}, response: {response}"
                        ) from e
                        return f"HTTP Error when calling the knowledge base"
                    # return response_json
        except asyncio.TimeoutError as e:
            # return "Kapa timeout"
            raise KapaInformationRetrievalException(
                f"Kapa search timeout. Encountered error: {str(e)}, url: {self.url}, headers: {headers}"
            ) from e
        except Exception as e:
            raise KapaInformationRetrievalException(
                f"Kapa search failed. Encountered error: {str(e)}, url: {self.url}, headers: {headers}"
            ) from e

    async def search(
        self, query: Text, tracker_state: dict[Text, Any], threshold: float = 0.0
    ) -> SearchResultList:
        """Search for a document in the Qdrant vector store.

        Args:
            query: The query to search for.
            threshold: minimum similarity score to consider a document a match.

        Returns:
            SearchResultList: A list of documents that match the query.
                @dataclass
                class SearchResult:
                    text: str
                    metadata: dict
                    score: Optional[float] = None

                @dataclass
                class SearchResultList:
                    results: List[SearchResult]
                    metadata: dict

                You can use the class method SearchResultList.from_document_list() to convert from a [Langchain Document](https://python.langchain.com/v0.2/docs/integrations/document_loaders/copypaste/) object type.
        """
        structlogger.debug("kapa.search", query=query)
        if self.endpoint_type == "chat":
            result = await self.kapa_query_chat(query)
        else:
            result = await self.kapa_query_search(query)
        structlogger.debug("kapa.search", result=result)
        return result
