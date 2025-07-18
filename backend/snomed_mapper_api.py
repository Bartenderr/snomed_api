from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import shutil
from datetime import datetime

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

app = FastAPI(title="SNOMED Mapper Lite", version="1.2.0")

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

class ExcelProcessResponse(BaseModel):
    file_id: str
    total_rows: int
    duplicated_rows: int

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/api/v1/status")
def get_status():
    return {"status": "ok", "version": "1.2.0"}


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


def process_tariff_data(file_path):
    """
    Process tariff data from an Excel file with multiple sheets.
    """
    excel_file = pd.ExcelFile(file_path)
    full_tariff = []

    for sheet_name in excel_file.sheet_names:
        if sheet_name != 'SUMMARY':
            try:
                df = excel_file.parse(sheet_name)
                if 'TARIFF NAME' in df.columns:
                    df['TARIFF TYPE'] = sheet_name
                    df['TARIFF NAME'] = df['TARIFF NAME'].str.lower()
                    full_tariff.append(df)
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue

    if not full_tariff:
        raise ValueError("No valid sheets found in the Excel file")

    current_tariff = pd.concat(full_tariff, ignore_index=True)
    
    # Clean up the tariff names
    current_tariff['TARIFF NAME'] = current_tariff['TARIFF NAME'].astype(str)
    current_tariff['TARIFF NAME'] = current_tariff['TARIFF NAME'].str.lower()
    current_tariff['TARIFF NAME'] = current_tariff['TARIFF NAME'].str.replace('\n', ' ')
    current_tariff['TARIFF NAME'] = current_tariff['TARIFF NAME'].str.strip()
    current_tariff['TARIFF NAME'] = current_tariff['TARIFF NAME'].str.split().str.join(' ')

    # Calculate lengths
    df_length = len(current_tariff)
    duplicated_length = len(current_tariff[current_tariff.duplicated(['TARIFF NAME', 'PRICE'], keep='last')])

    return current_tariff, df_length, duplicated_length


def match_tariffs_from_df(leftout_df):
    """
    Match tariffs from a DataFrame with SNOMED codes
    """
    # Prepare the tariff names for matching
    leftout_tariff_names = leftout_df['TARIFF NAME'].fillna('').astype(str).str.lower().tolist()
    leftout_vectors = vectorizer.transform(leftout_tariff_names)

    # Compute similarity with reference tariffs
    similarity_matrix = cosine_similarity(leftout_vectors, reference_vectors)
    best_matches_indices = similarity_matrix.argmax(axis=1)
    best_match_scores = similarity_matrix.max(axis=1)

    # Add the matched data to the DataFrame
    leftout_df['Matched Tariff Name'] = [reference_tariff_names[i] for i in best_matches_indices]
    leftout_df['Similarity Score'] = best_match_scores
    
    # Handle potential NaN values in the SNOMED codes
    snomed_codes = []
    snomed_descriptions = []
    
    for idx in best_matches_indices:
        try:
            code = str(int(float(tariff_df_clean.iloc[idx]['snomed code'])))
        except (ValueError, TypeError):
            code = "N/A"
        
        try:
            description = str(tariff_df_clean.iloc[idx]['snomed description'])
        except (TypeError, KeyError):
            description = "N/A"
            
        snomed_codes.append(code)
        snomed_descriptions.append(description)
    
    leftout_df['SNOMED CODE'] = snomed_codes
    leftout_df['SNOMED CODE'] = leftout_df['SNOMED CODE'].astype(str)
    
    leftout_df['SNOMED DESCRIPTION EN'] = snomed_descriptions
    
    
    return leftout_df


@app.post("/api/v1/process-excel", response_model=ExcelProcessResponse)
async def process_excel(file: UploadFile = File(...)):
    # Validate file
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file (.xlsx, .xls)")
    
    # Create unique ID for this processing job
    file_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = f"uploads/{file_id}_{file.filename}"
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process the Excel file
        tariff_df, total_rows, duplicated_rows = process_tariff_data(upload_path)
        
        # Match with SNOMED codes
        matched_df = match_tariffs_from_df(tariff_df)
        
        # Save the result
        result_path = f"results/{file_id}_matched.xlsx"
        matched_df.to_excel(result_path, index=False)
        
        return ExcelProcessResponse(
            file_id=file_id,
            total_rows=total_rows,
            duplicated_rows=duplicated_rows
        )
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/api/v1/download/{file_id}")
async def download_result(file_id: str):
    # Find the result file
    for filename in os.listdir("results"):
        if filename.startswith(file_id):
            return FileResponse(
                path=f"results/{filename}", 
                filename=f"SNOMED_Matched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    raise HTTPException(status_code=404, detail="Result file not found")


# === For local development only === #
if __name__ == "__main__":
    uvicorn.run("snomed_mapper_api:app", host="0.0.0.0", port=8000, reload=True)