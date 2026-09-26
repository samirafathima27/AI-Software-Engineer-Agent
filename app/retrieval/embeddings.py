from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
    global _model

    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def generate_embedding(text: str) -> list[float]:
    model = get_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings.tolist()

if __name__ == "__main__":
    from app.retrieval.chunker import chunk_repository

    chunks = chunk_repository("workspace")

    texts = [chunk["text"] for chunk in chunks]

    embeddings = generate_embeddings(texts)

    print("\n========================================")
    print("          EMBEDDING TEST")
    print("========================================")

    print(f"\nChunks: {len(chunks)}")
    print(f"Embeddings: {len(embeddings)}")

    if embeddings:
        print(f"Embedding dimensions: {len(embeddings[0])}")

    for index, embedding in enumerate(embeddings, start=1):
        print(f"\nChunk {index}: {chunks[index - 1]['name']}")
        print(f"Vector length: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")