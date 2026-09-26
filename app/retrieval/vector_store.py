import chromadb


COLLECTION_NAME = "code_repository"


class CodeVectorStore:

    def __init__(
        self,
        persist_directory: str = "data/chroma"
    ):
        self.persist_directory = persist_directory

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection = self._get_collection()

    def _get_collection(self):
        return self.client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]]
    ):
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks and embeddings must match."
            )

        # Refresh collection reference in case it was recreated.
        self.collection = self._get_collection()

        ids = [
            chunk["id"]
            for chunk in chunks
        ]

        documents = [
            chunk["text"]
            for chunk in chunks
        ]

        metadatas = [
            {
                "type": chunk["type"],
                "name": chunk["name"],
                "file": chunk["file"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
            }
            for chunk in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5
    ) -> dict:

        # Always refresh the collection reference.
        self.collection = self._get_collection()

        collection_count = self.collection.count()

        if collection_count == 0:
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        top_k = min(top_k, collection_count)

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

    def count(self) -> int:
        self.collection = self._get_collection()

        return self.collection.count()

    def clear(self):
        try:
            self.client.delete_collection(
                name=COLLECTION_NAME
            )
        except Exception:
            pass

        # IMPORTANT:
        # Re-acquire the newly created collection.
        self.collection = self._get_collection()


if __name__ == "__main__":
    from app.retrieval.indexer import index_repository

    print("\n========================================")
    print("       VECTOR STORE TEST")
    print("========================================")

    count = index_repository("workspace")

    print(f"\nIndexed chunks: {count}")