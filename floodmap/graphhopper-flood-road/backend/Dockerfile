FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --retries 10 --timeout 120 psycopg2-binary

COPY backend ./backend
COPY scripts ./scripts

ENV HOST=0.0.0.0
ENV PORT=8010
ENV GRAPHHOPPER_URL=http://graphhopper:8989

EXPOSE 8010

CMD ["python", "backend/server.py"]
