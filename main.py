from src.LLM_client.openrouter_client import OpenRouterClient

if __name__ == "__main__":
    query = "Natural Language Processing?"
    open_router_client = OpenRouterClient()
    related_topics = open_router_client.suggest_related_topics(query)
    print(related_topics)