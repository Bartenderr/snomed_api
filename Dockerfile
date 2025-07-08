# Use official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential

# Copy backend folder into the container
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["uvicorn", "snomed_mapper_api:app", "--host", "0.0.0.0", "--port", "8000"]
