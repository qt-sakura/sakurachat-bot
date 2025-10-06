# Use Python 3.13 base
FROM python:3.13

# Set working directory
WORKDIR /app

# Update and upgrade system
RUN apt update && apt upgrade -y

# Upgrade pip to latest
RUN pip install --upgrade pip

# Copy Python dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Run main Python script
CMD ["python3", "kawai.py"]