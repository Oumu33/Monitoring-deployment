# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the current directory to the working directory
COPY app.py .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variables (can be overridden in docker-compose)
ENV SERVICE_NAME=hello-app
ENV OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317

# Run app.py when the container launches
CMD ["python", "app.py"]
