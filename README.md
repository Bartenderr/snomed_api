# 🧠 SNOMED Mapper Lite

**SNOMED Mapper Lite** is a lightweight API and demo UI that maps free-text medical tariff names to their most likely **SNOMED codes** using natural language processing with **TF-IDF** and **cosine similarity**.

Built with **FastAPI**, **Docker**, and a simple HTML/CSS/JS frontend — ready for deployment on **Railway** or local testing.

---

## 🔍 Features

- 🧾 Accepts plain-text tariff names (batch or single)
- 🔁 Matches them to SNOMED codes and descriptions using string similarity
- 🎯 Returns best-fit result with confidence score
- 📦 Supports loading from Excel or JSON (`reference_map.json`)
- 🌐 REST API + HTML frontend
- 🚀 Dockerized for one-command deploy

---

## 📸 Screenshot

![Screenshot of UI](static/screenshot.png)

---

## 🚀 Quickstart (Docker)

### 1. Clone this repo
```
git clone https://github.com/Bartenderr/snomed_api.git
cd snomed_api
```

### 2. Build the container 
```
docker build -t snomed_api .
docker run -p 8000:8000 snomed_api
```
### 3. Then open http://localhost:8000 in your browser.


## 🌐 API Reference
Health check ``` GET /api/v1/status ```

Request 
```
POST /api/v1/match

Request body
{
  "tariff_names": ["CBC", "abdominal ultrasound"]
}

Respone 
{
  "results": [
    {
      "input_name": "CBC",
      "matched_name": "complete blood count",
      "snomed_code": "104866001",
      "snomed_description": "Complete blood count (procedure)",
      "similarity_score": 0.9724
    }
  ]
}
```

