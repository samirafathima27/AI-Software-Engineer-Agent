from app.retrieval.chunker import chunk_repository
from app.retrieval.embeddings import generate_embeddings
from app.retrieval.vector_store import CodeVectorStore


def index_repository(repository_path: str = "workspace") -> int:
    """
    Scan the repository, create code chunks, generate embeddings,
    and store them in ChromaDB.

    Returns:
        Number of indexed code chunks.
    """

    print("\n========================================")
    print("       BUILDING CODE INDEX")
    print("========================================")

    print("\nScanning repository...")

    chunks = chunk_repository(repository_path)

    print(f"Found {len(chunks)} code chunks.")

    if not chunks:
        print("No code chunks found.")
        return 0

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print("\nGenerating embeddings...")

    embeddings = generate_embeddings(texts)

    print(f"Generated {len(embeddings)} embeddings.")

    store = CodeVectorStore()

    print("\nUpdating vector store...")

    store.clear()

    store.add_chunks(
        chunks,
        embeddings
    )

    print(
        f"\nSuccessfully indexed "
        f"{store.count()} code chunks."
    )

    return store.count()


if __name__ == "__main__":
    count = index_repository("workspace")

    print("\n========================================")
    print("          INDEX COMPLETE")
    print("========================================")

    print(f"\nTotal indexed chunks: {count}")