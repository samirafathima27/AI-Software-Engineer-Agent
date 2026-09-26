from app.retrieval.embeddings import generate_embedding
from app.retrieval.indexer import index_repository
from app.retrieval.vector_store import CodeVectorStore


class SemanticCodeSearch:

    def __init__(self):
        self.store = CodeVectorStore()

    def search(
        self,
        query: str,
        top_k: int = 5,
        refresh_index: bool = False
    ) -> list[dict]:

        if refresh_index:
            index_repository("workspace")

        query_embedding = generate_embedding(query)

        results = self.store.search(
            query_embedding,
            top_k=top_k
        )

        matches = []

        documents = results.get(
            "documents",
            [[]]
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        for index, document in enumerate(documents):

            metadata = metadatas[index]

            matches.append({
                "name": metadata.get("name"),
                "type": metadata.get("type"),
                "file": metadata.get("file"),
                "line_start": metadata.get("line_start"),
                "line_end": metadata.get("line_end"),
                "content": document,
                "distance": (
                    distances[index]
                    if index < len(distances)
                    else None
                ),
            })

        return matches


def search_code(
    query: str,
    top_k: int = 5,
    refresh_index: bool = False
) -> list[dict]:

    searcher = SemanticCodeSearch()

    return searcher.search(
        query=query,
        top_k=top_k,
        refresh_index=refresh_index
    )


if __name__ == "__main__":

    print("\n========================================")
    print("        SEMANTIC CODE SEARCH")
    print("========================================")

    print("\nBuilding repository index...")

    index_repository("workspace")

    query = input(
        "\nEnter your code search query: "
    ).strip()

    if not query:
        print("No query provided.")
        raise SystemExit

    results = search_code(
        query,
        top_k=5,
        refresh_index=False
    )

    print(
        f"\nSearch results for: "
        f"{query}"
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        print("\n----------------------------------------")
        print(f"RESULT {index}")
        print("----------------------------------------")

        print(f"Name: {result['name']}")
        print(f"Type: {result['type']}")
        print(f"File: {result['file']}")

        print(
            f"Lines: "
            f"{result['line_start']}-"
            f"{result['line_end']}"
        )

        print(
            f"Distance: "
            f"{result['distance']}"
        )

        print("\nCode:")
        print(result["content"])