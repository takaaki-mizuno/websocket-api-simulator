# Dockerfile
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
#RUN apt-get clean && apt-get update && apt-get install -y --no-install-recommends \
#    gcc \
#    libc6-dev \
#    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]

# requirements.txt
