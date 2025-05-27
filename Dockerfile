# Use an official Python runtime as a base image
FROM python:3.13.3

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY src/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run init.py when the container launches
CMD ["python", "src/main.py"]

