# Base slim image
FROM python:3.13-slim

# Set work directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/* /usr/share/man /usr/share/doc /usr/share/groff /usr/share/info

# Upgrade pip tool
RUN pip install --no-cache-dir --upgrade pip --root-user-action=ignore

# Copy requirements file
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# Copy app files
COPY . .

# Run application
CMD ["python3", "kawai.py"]