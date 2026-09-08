FROM python:3.12-slim

WORKDIR /app

# rasterio's manylinux wheel (pulled in by rio-tiler) links GDAL against
# libexpat, which python:3.12-slim does not ship.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --retries 10 --timeout 120 psycopg2-binary "rio-tiler>=6,<8"

COPY backend ./backend
COPY scripts ./scripts

ENV HOST=0.0.0.0
ENV PORT=8010
ENV GRAPHHOPPER_URL=http://graphhopper:8989
ENV FLOOD_TIMESERIES_DIR=/data/flood-timeseries

EXPOSE 8010

CMD ["python", "backend/server.py"]
