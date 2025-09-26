#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VM AI Service Environment Check Script
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_status(message, status="INFO"):
    """Print status message"""
    symbols = {"INFO": "[INFO]", "SUCCESS": "[OK]", "ERROR": "[ERROR]", "WARNING": "[WARN]"}
    print(f"{symbols.get(status, '[INFO]')} {message}")

def check_python_packages():
    """Check required Python packages"""
    print_status("Checking Python packages...")

    required_packages = [
        'sentence-transformers',
        'chromadb',
        'pandas',
        'numpy',
        'torch'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_status(f"{package} - installed", "SUCCESS")
        except ImportError:
            print_status(f"{package} - not installed", "ERROR")
            missing_packages.append(package)

    if missing_packages:
        print_status(f"Missing packages: {', '.join(missing_packages)}", "WARNING")
        print_status(f"Run: pip install {' '.join(missing_packages)}", "INFO")
        return False

    return True

def check_embedding_model():
    """Check embedding model"""
    print_status("Checking BAAI/bge-base-zh-v1.5 model...")

    try:
        from sentence_transformers import SentenceTransformer

        print_status("Loading model...", "INFO")
        model = SentenceTransformer('BAAI/bge-base-zh-v1.5')

        dimension = model.get_sentence_embedding_dimension()
        max_length = model.max_seq_length

        print_status(f"Model dimension: {dimension}", "SUCCESS")
        print_status(f"Max sequence length: {max_length}", "SUCCESS")

        # Test encoding
        test_embedding = model.encode(["test text"])
        print_status(f"Encoding test success, vector shape: {test_embedding.shape}", "SUCCESS")

        if dimension != 768:
            print_status(f"Warning: Expected 768 dimension, got {dimension}", "WARNING")
            return False

        return True

    except ImportError:
        print_status("sentence-transformers not installed", "ERROR")
        return False
    except Exception as e:
        print_status(f"Model loading failed: {e}", "ERROR")
        return False

def check_vector_database():
    """Check vector database"""
    print_status("Checking vector database...")

    db_dir = Path("rag/chroma_db")

    if not db_dir.exists():
        print_status("Vector database directory not found", "ERROR")
        print_status("Run: python rebuild_vectordb.py", "INFO")
        return False

    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=str(db_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_or_create_collection("faq_with_training")
        count = collection.count()

        print_status(f"Vector database document count: {count}", "SUCCESS")

        if count == 0:
            print_status("Vector database is empty, need rebuild", "WARNING")
            return False

        # Test query
        results = collection.query(
            query_texts=["how to like"],
            n_results=1
        )

        if results and results['documents']:
            print_status("Vector query test success", "SUCCESS")
            return True
        else:
            print_status("Vector query test failed", "ERROR")
            return False

    except ImportError:
        print_status("chromadb not installed", "ERROR")
        return False
    except Exception as e:
        print_status(f"Vector database error: {e}", "ERROR")
        return False

def check_ollama_service():
    """Check Ollama service"""
    print_status("Checking Ollama service...")

    try:
        import requests

        ollama_url = "http://127.0.0.1:11434/api/tags"
        response = requests.get(ollama_url, timeout=5)

        if response.status_code == 200:
            print_status("Ollama service is running", "SUCCESS")

            data = response.json()
            models = [model['name'] for model in data.get('models', [])]

            required_model = "qwen2.5:3b-instruct"
            if required_model in models:
                print_status(f"Model {required_model} installed", "SUCCESS")
                return True
            else:
                print_status(f"Model {required_model} not installed", "WARNING")
                print_status(f"Run: ollama pull {required_model}", "INFO")
                return False
        else:
            print_status("Ollama service not responding", "ERROR")
            return False

    except Exception as e:
        print_status(f"Cannot connect to Ollama: {e}", "ERROR")
        print_status("Make sure Ollama is installed and running: ollama serve", "INFO")
        return False

def check_django_settings():
    """Check Django settings"""
    print_status("Checking Django settings...")

    env_file = Path(".env")
    if not env_file.exists():
        print_status(".env file not found", "ERROR")
        print_status("Make sure .env file is copied to project root", "INFO")
        return False

    try:
        env_content = env_file.read_text(encoding='utf-8')

        checks = [
            ("DEBUG=False", "Production environment"),
            ("pawday114404.duckdns.org", "Domain setting"),
            ("https://pawday114404.duckdns.org", "HTTPS setting")
        ]

        all_good = True
        for check, description in checks:
            if check in env_content:
                print_status(f"{description} - correct", "SUCCESS")
            else:
                print_status(f"{description} - need check", "WARNING")
                all_good = False

        return all_good

    except Exception as e:
        print_status(f"Error reading .env file: {e}", "ERROR")
        return False

def create_rebuild_script():
    """Create vector database rebuild script"""
    rebuild_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Vector Database Script
"""
import os
import shutil

def rebuild_vector_db():
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from chromadb.config import Settings

        print("Loading embedding model...")
        embedder = SentenceTransformer('BAAI/bge-base-zh-v1.5')
        print(f'Model dimension: {embedder.get_sentence_embedding_dimension()}')

        DB_DIR = 'rag/chroma_db'
        COLLECTION_NAME = 'faq_with_training'

        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            print('Deleted old vector database')

        print("Creating new vector database...")
        client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_or_create_collection(COLLECTION_NAME)

        # FAQ data - using simple text to avoid encoding issues
        faq_data = [
            {
                'id': 'Q1',
                'question': 'How to record pet health?',
                'answer': 'Record basic vital signs, observe appetite and activity, measure temperature, track daily bowel movements and urination, vaccination and regular health checkups.'
            },
            {
                'id': 'Q2',
                'question': 'How to like and comment in community?',
                'answer': 'To like: click heart icon below posts. To comment: click comment icon, write your thoughts in input box, click send button or use Ctrl+Enter. Login required for interactions.'
            },
            {
                'id': 'Q3',
                'question': 'What community features are available?',
                'answer': 'Post features: share pet photos and daily life. Interaction: like, comment, share. Browse: view other users posts, search topics. Profile: manage personal info and pets.'
            }
        ]

        documents = []
        metadatas = []
        ids = []

        for faq in faq_data:
            doc_text = f"Question: {faq['question']}\\n\\nAnswer: {faq['answer']}"
            documents.append(doc_text)
            metadatas.append({
                'id': faq['id'],
                'title': faq['question'],
                'source': 'FAQ'
            })
            ids.append(f"faq_{faq['id']}")

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f'Vector database rebuilt! Total documents: {collection.count()}')
        return True

    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    rebuild_vector_db()
'''

    with open("rebuild_vectordb.py", "w", encoding="utf-8") as f:
        f.write(rebuild_script)

    print_status("Created rebuild_vectordb.py script", "SUCCESS")

def main():
    """Main check process"""
    print("=" * 50)
    print("VM AI Service Environment Check")
    print("=" * 50)

    checks = [
        ("Python Packages", check_python_packages),
        ("Embedding Model", check_embedding_model),
        ("Vector Database", check_vector_database),
        ("Ollama Service", check_ollama_service),
        ("Django Settings", check_django_settings),
    ]

    results = {}

    for name, check_func in checks:
        print(f"\\n--- {name} ---")
        try:
            results[name] = check_func()
        except Exception as e:
            print_status(f"{name} check error: {e}", "ERROR")
            results[name] = False

    # Summary
    print("\\n" + "=" * 50)
    print("Check Results Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results.items():
        status = "SUCCESS" if passed else "ERROR"
        print_status(f"{name}: {'PASSED' if passed else 'FAILED'}", status)
        if not passed:
            all_passed = False

    if all_passed:
        print_status("All checks passed! AI service environment is ready", "SUCCESS")
    else:
        print_status("Some checks failed. Please follow the suggestions above", "WARNING")
        create_rebuild_script()

        print("\\nFix suggestions:")
        print("1. Install missing Python packages")
        print("2. Run: python rebuild_vectordb.py")
        print("3. Make sure Ollama service is running")
        print("4. Check .env settings file")

    return all_passed

if __name__ == "__main__":
    main()