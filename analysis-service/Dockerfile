FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

COPY app ./app

ENV HOST=0.0.0.0
ENV PORT=8020

EXPOSE 8020

CMD ["python", "app/server.py"]
