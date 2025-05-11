# Use an official Python runtime as a base image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 2323 available to the world outside this container
EXPOSE 2323

# Run the Python script when the container starts
# Environment variables (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, AI_PLATFORM, AI_MODEL)
# should be passed when running the container using the -e flag.
CMD ["python", "start_server.py"]
