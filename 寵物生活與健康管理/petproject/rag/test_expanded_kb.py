import os, sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp import chat_service

def test_expanded_kb():
    print("Testing expanded knowledge base...")

    # Clear cache first
    chat_service.clear_cache()
    print("Cache cleared")

    # Test queries
    test_queries = [
        "狗狗適合的運動量？",
        "寵物適合的運動量？",
        "我要如何跟我家狗好相處？",
        "貓咪運動",
        "寵物疫苗"
    ]

    client, collection = chat_service._get_cached_client()
    if collection:
        print(f"Collection has {collection.count()} documents")

    for query in test_queries:
        print(f"\n--- Testing: {query} ---")
        try:
            context, sources = chat_service.safe_retrieve(query, top_k=3)
            print(f"Found content: {len(context) > 0}")
            print(f"Sources: {len(sources)}")
            if context:
                print(f"Content preview: {context[:150]}...")
                for i, source in enumerate(sources):
                    print(f"  Source {i+1}: score={source.get('score', 'N/A')}")
            else:
                print("No content found")

            # Try direct ChromaDB query for debugging
            if collection:
                embeddings = chat_service._embedder.encode([query], normalize_embeddings=True).tolist()
                raw_results = collection.query(
                    query_embeddings=embeddings,
                    n_results=3,
                    include=["documents", "metadatas", "distances"]
                )
                raw_docs = raw_results.get("documents", [[]])[0]
                raw_distances = raw_results.get("distances", [[]])[0]
                print(f"Raw ChromaDB results: {len(raw_docs)} documents")
                for i, (doc, dist) in enumerate(zip(raw_docs[:2], raw_distances[:2])):
                    similarity = 1.0 - dist
                    print(f"  Doc {i+1}: similarity={similarity:.3f}, preview={doc[:50]}...")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_expanded_kb()