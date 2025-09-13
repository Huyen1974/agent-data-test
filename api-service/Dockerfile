# Use the official Python image.
FROM python:3.11-slim

# Set the working directory.
WORKDIR /app

# Copy local code to the container image.
COPY . .

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
# Uvicorn will listen on port 8080 by default, which Cloud Run expects.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
