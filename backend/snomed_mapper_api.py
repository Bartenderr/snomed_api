from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="SNOMED Mapper Lite", version="1.1.0")

# Serve static files (HTML/CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS for frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:8000"] for stricter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# === Load and prepare the SNOMED reference data === #
REFERENCE_FILE_PATH = "reference_map.json"

try:
    tariff_df = pd.read_json(REFERENCE_FILE_PATH)
    tariff_df_clean = tariff_df[['tariff name', 'snomed code', 'snomed description']].dropna()
    tariff_df_clean = tariff_df_clean.drop_duplicates(subset='tariff name', keep='last')
    reference_tariff_names = tariff_df_clean['tariff name'].fillna('').str.lower().tolist()
    vectorizer = TfidfVectorizer().fit(reference_tariff_names)
    reference_vectors = vectorizer.transform(reference_tariff_names)
except Exception as e:
    print(f"Error loading reference file: {e}")
    raise

# === Request and Response Models === #
class TariffRequest(BaseModel):
    tariff_names: List[str]

class TariffMatch(BaseModel):
    input_name: str
    matched_name: str
    snomed_code: str
    snomed_description: str
    similarity_score: float

class TariffResponse(BaseModel):
    results: List[TariffMatch]

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/api/v1/status")
def get_status():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/v1/match", response_model=TariffResponse)
def match_tariffs(request: TariffRequest):
    if not request.tariff_names:
        raise HTTPException(status_code=400, detail="tariff_names list cannot be empty.")

    input_cleaned = [name.strip().lower() for name in request.tariff_names]
    input_vectors = vectorizer.transform(input_cleaned)

    similarity_matrix = cosine_similarity(input_vectors, reference_vectors)
    best_matches_indices = similarity_matrix.argmax(axis=1)
    best_match_scores = similarity_matrix.max(axis=1)

    results = []
    for idx, name in enumerate(request.tariff_names):
        match_idx = best_matches_indices[idx]
        results.append(TariffMatch(
            input_name=name,
            matched_name=reference_tariff_names[match_idx],
            snomed_code=str(int(float(tariff_df_clean.iloc[match_idx]['snomed code']))),
            snomed_description=str(tariff_df_clean.iloc[match_idx]['snomed description']),
            similarity_score=float(best_match_scores[idx])
        ))

    return TariffResponse(results=results)


# === For local development only === #
if __name__ == "__main__":
    uvicorn.run("snomed_mapper_api:app", host="0.0.0.0", port=8000, reload=True)
