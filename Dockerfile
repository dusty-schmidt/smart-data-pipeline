# Base Image
FROM python:3.11-slim

# Working Directory
WORKDIR /app

# System Dependencies (if any needed for heavy lifting later, e.g. gcc)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
COPY . .

# Environment Variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose UI Port
EXPOSE 8501

# Default Command (Run UI)
CMD ["streamlit", "run", "src/ui/app.py", "--server.address=0.0.0.0"]
