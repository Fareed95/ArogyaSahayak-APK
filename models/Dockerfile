# Use the official Python image from the Docker Hub
FROM python:3.11

# Set the working directory to /app
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Start the FastAPI server using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
