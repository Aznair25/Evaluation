# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to ensure Python output is logged to the terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /backend/app

# Install system dependencies
# libasound2 is required by the Azure Speech SDK on Linux even when
# using PushAudioInputStream (the SDK still probes the ALSA audio platform).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

# Stub ALSA config so the Azure Speech SDK can initialise its audio platform
# without a real audio device (Docker containers have no sound card).
RUN mkdir -p /etc/alsa && printf 'pcm.!default { type null }\nctl.!default { type null }\n' > /etc/asound.conf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the API using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]