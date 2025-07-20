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
RUN pip install -r requirements.txt

# Copy only the necessary application files
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the application
CMD ["python", "src/main.py"]

