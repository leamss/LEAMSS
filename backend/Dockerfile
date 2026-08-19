FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

WORKDIR /app

# Install system dependencies required for WeasyPrint (Cairo, Pango, GDK-Pixbuf) and fonts
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libcairo2     libpango-1.0-0     libpangocairo-1.0-0     libgdk-pixbuf-2.0-0     libffi-dev     shared-mime-info     fonts-liberation     fonts-dejavu-core     fontconfig     curl     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose backend port
EXPOSE 8001

# Run Uvicorn server using dynamic environment PORT
CMD uvicorn server:app --host 0.0.0.0 --port 