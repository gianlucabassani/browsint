FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies required by python packages or the application itself
# wkhtmltopdf is needed for pdfkit
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set python path
ENV PYTHONPATH=/app/src

# Set the default command to run the interactive CLI
CMD ["python3", "src/main.py"]
