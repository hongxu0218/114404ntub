import os, sys
import django
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petproject.settings')
django.setup()

from petapp import chat_service
import chromadb
from chromadb.config import Settings

def main():
    print("Rebuilding Django AI knowledge base...")

    # Read Excel data
    df = pd.read_excel('data/platform_manual.xlsx')
    print(f"Loaded {len(df)} rows from Excel")

    # Initialize ChromaDB
    client = chromadb.PersistentClient(
        path=chat_service.DB_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    # Delete old collection and create new one
    try:
        client.delete_collection(chat_service.COLLECTION_NAME)
        print("Deleted old collection")
    except:
        print("No old collection to delete")

    collection = client.create_collection(chat_service.COLLECTION_NAME)
    print("Created new collection")

    # Process data
    documents = []
    metadatas = []
    ids = []

    for idx, row in df.iterrows():
        q = str(row.get('Question', '')).strip()
        a = str(row.get('Answer', '')).strip()

        if q and a:
            combined_text = f"Q: {q}\nA: {a}"
            documents.append(combined_text)
            metadatas.append({
                'question': q,
                'answer': a,
                'source': 'platform_manual',
                'id': f"qa_{idx+1}"
            })
            ids.append(f"qa_{idx+1}")

    print(f"Prepared {len(documents)} documents")

    # Generate embeddings and add to collection
    embeddings = chat_service._embedder.encode(documents, normalize_embeddings=True).tolist()
    print(f"Generated {len(embeddings)} embeddings, dimension: {len(embeddings[0])}")

    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Added {len(documents)} documents to collection")

    # Test queries
    test_queries = ["忘記密碼怎麼辦？", "註冊帳號"]
    for query in test_queries:
        try:
            context, sources = chat_service.safe_retrieve(query, top_k=3)
            print(f"Query: {query} -> Found: {len(context) > 0}")
            if context:
                print(f"  Preview: {context[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")

    print("Rebuild complete!")

if __name__ == "__main__":
    main()