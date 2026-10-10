from backend.app.services.llm_client import (
    LLMUnavailableError,
    generate_structured_notes,
)


def main():
    sample_passages = [
        {
            "chunk_id": "demo-chunk-001",
            "title": "Sample Computer Science Text",
            "author": "Demo Author",
            "excerpt": (
                "A binary search tree is a data structure in which each "
                "node has at most two children. Values smaller than a "
                "node's key are stored in its left subtree, while larger "
                "values are stored in its right subtree."
            ),
        }
    ]

    try:
        result = generate_structured_notes(
            "Explain the basic structure of a binary search tree.",
            sample_passages,
        )

        print("Gemini responded successfully.")
        print("Title:", result.get("title"))
        print("Sections:", result.get("sections"))

    except LLMUnavailableError as exc:
        print("Gemini request failed.")
        print(str(exc))


if __name__ == "__main__":
    main()
