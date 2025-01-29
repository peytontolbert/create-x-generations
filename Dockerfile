# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install system dependencies including Microsoft Edge and msedgedriver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unzip \
    wget \
    xvfb \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg \
    && install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list \
    && apt-get update \
    && apt-get install -y microsoft-edge-stable \
    && EDGE_VERSION=$(microsoft-edge --version | cut -d' ' -f3) \
    && wget https://msedgedriver.azureedge.net/$EDGE_VERSION/edgedriver_linux64.zip \
    && unzip edgedriver_linux64.zip \
    && mv msedgedriver /usr/local/bin/ \
    && rm edgedriver_linux64.zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up a virtual display
ENV DISPLAY=:99

# Create and set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
RUN mkdir -p data/

COPY . .


# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & python main.py 