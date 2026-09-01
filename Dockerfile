FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD gunicorn api.main:app -k uvicorn.workers.UvicornWorker -w 1 --bind 0.0.0.0:$PORT --timeout 120