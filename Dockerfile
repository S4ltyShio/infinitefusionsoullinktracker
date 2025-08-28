# Streamlit app container
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

# System deps for building wheels if needed
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency list first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Default Streamlit settings for container
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0     STREAMLIT_SERVER_PORT=8501     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false     STREAMLIT_SERVER_ENABLE_CORS=false     STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 8501

# Persist state under /app/data via bind mount
VOLUME ["/app/data"]

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
