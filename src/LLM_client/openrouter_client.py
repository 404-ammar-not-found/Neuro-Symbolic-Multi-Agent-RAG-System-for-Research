from dotenv import load_dotenv
from openrouter import OpenRouter
import os

class OpenRouterClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    def suggest_related_topics(self, query):
        """
        This function takes a query as input and uses the OpenRouter API to suggest related topics. The prompt is designed to instruct the LLM to provide a comprehensive list of related topics in JSON format, which can be used to expand the search for relevant papers on arxiv.

        Args: 
            query (str): The input query for which related topics are to be suggested.
        Returns:
            response (str): A JSON formatted string containing a list of related topics suggested by the L
        """

        PROMPT = f"""
        You are a research engineer in the following domain. 
        Suggest related topics for the following query: {query} to find relevant papers on arxiv. 
        The related topics should be relevant to the original query and should help in expanding the search for papers on arxiv.
        Return nothing but a list of related topics in JSON format. The list should be comprehensive and cover a wide range of related topics.
        """

        with OpenRouter(
            api_key=self.api_key
        ) as client:
            response = client.chat.send(
                model="z-ai/glm-4.5-air:free",
                messages=[
                    {"role": "user", "content": PROMPT}
                ]
            )

        return response