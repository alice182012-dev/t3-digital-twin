# FROM apache/airflow:3.1.7

# USER root

# RUN apt-get update && apt-get install -y binutils libproj-dev gdal-bin libgdal-dev g++ --no-install-recommends && rm -rf /var/lib/apt/lists/*
# ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
# ENV C_INCLUDE_PATH=/usr/include/gdal

# USER airflow

# COPY requirements.txt /opt/airflow/requirements.txt
# RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.1.7/constraints-3.12.txt"
# RUN pip install wheel setuptools>=67
# RUN pip install numpy==1.26.4 gdal[numpy]==3.6.2 --no-build-isolation --no-cache-dir --force-reinstall

FROM apache/airflow:3.1.7

USER root

# ===== system dependencies =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    # ===== GDAL pinned to Debian 12's 3.6.2: the base image also has the PGDG repo, which offers
    # 3.13 headers that the gdal==3.6.2 Python package below can't compile against =====
    gdal-bin=3.6.2+dfsg-1+b2 \
    python3-gdal=3.6.2+dfsg-1+b2 \
    gdal-data=3.6.2+dfsg-1 \
    libgdal32=3.6.2+dfsg-1+b2 \
    libgdal-dev=3.6.2+dfsg-1+b2 \
    g++ \
    # ===== fix OpenCV errors =====
    libgl1 \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libxcb1 \
    # ===== tesseract =====
    tesseract-ocr \
    # ===== selenium (chrome) =====
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===== install Google Chrome =====
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

# ===== GDAL env =====
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

USER airflow

# ===== copy requirements =====
COPY requirements.txt /opt/airflow/requirements.txt

# ===== install python deps (Airflow constraint) =====
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.1.7/constraints-3.12.txt"

# ===== fix numpy + gdal compatibility =====
RUN pip install --no-cache-dir --force-reinstall \
    numpy==1.26.4 \
    gdal[numpy]==3.6.2 \
    --no-build-isolation

# ===== IMPORTANT: replace opencv with headless =====
RUN pip uninstall -y opencv-python || true
RUN pip install --no-cache-dir opencv-python-headless

# ===== optional: ensure setuptools =====
RUN pip install --no-cache-dir "setuptools>=67" wheel

USER root

# GRASS GIS is last so that changing it rebuilds only this layer. scripts/flood_extent uses it
# to close the gaps between wet cells. The GDAL pins repeat the ones in the first apt layer:
# without them, grass-core pulls the PGDG 3.13.2 packages over the 3.6.2 ones that the
# gdal==3.6.2 Python package was built against.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    grass-core \
    gdal-bin=3.6.2+dfsg-1+b2 \
    python3-gdal=3.6.2+dfsg-1+b2 \
    gdal-data=3.6.2+dfsg-1 \
    libgdal32=3.6.2+dfsg-1+b2 \
    libgdal-dev=3.6.2+dfsg-1+b2 \
    && rm -rf /var/lib/apt/lists/*

USER airflow