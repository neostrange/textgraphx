import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from textgraphx.pipeline.ingestion.graph_based_nlp import GraphBasedNLP


app = FastAPI()

origins = ["http://localhost:3000"]  # adjust this to the origin of your React app

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize the GraphBasedNLP object with the predefined directory path
# Use environment variable with fallback to canonical datastore location
_default_dataset = str(Path(__file__).parent.parent / 'datastore' / 'dataset')
dataset_directory = os.getenv('TEXTGRAPHX_DATASET_DIR', _default_dataset)
nlp = GraphBasedNLP([dataset_directory])


class ProcessTextRequest(BaseModel):
    storeTag: bool


class RetrieveResultsRequest(BaseModel):
    cypher_query: str


@app.post("/load_corpus")
async def load_corpus():
    # Load the corpus from the predefined directory
    try:
        nlp.store_corpus(dataset_directory)
        return JSONResponse(content={"message": "Corpus loaded successfully"}, status_code=200)
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=500)


@app.post("/process_text")
async def process_text(request: ProcessTextRequest):
    # Process the text using the GraphBasedNLP object
    try:
        text_tuples = nlp.store_corpus(dataset_directory)  # Reuse loaded corpus
        nlp.process_text(text_tuples, text_id=1, storeTag=request.storeTag)
        return JSONResponse(content={"message": "Text processed successfully"}, status_code=200)
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=500)


@app.post("/retrieve_results")
async def retrieve_results(request: RetrieveResultsRequest):
    # Retrieve results from Neo4j based on the given criteria
    try:
        results = nlp.execute_cypher_query(request.cypher_query)
        return JSONResponse(content={"results": results}, status_code=200)
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=500)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8500)


__all__ = [
    "ProcessTextRequest",
    "RetrieveResultsRequest",
    "app",
    "dataset_directory",
    "load_corpus",
    "main",
    "nlp",
    "process_text",
    "retrieve_results",
]


if __name__ == "__main__":
    main()