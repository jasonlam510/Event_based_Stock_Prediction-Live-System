# Use an official Python runtime as a base image
FROM python:3.11.3

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_URL=postgresql://myuser:mypassword@postgres:5432/myfypdb

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the application
CMD ["python", "src/main.py"]

