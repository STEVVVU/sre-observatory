FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/observatory

RUN groupadd --gid 10001 observatory \
    && useradd --uid 10001 --gid observatory --no-create-home observatory

COPY pyproject.toml constraints.txt ./
COPY service ./service
COPY tools ./tools
RUN python -m pip install --upgrade pip \
    && python -m pip install --constraint constraints.txt .

USER 10001:10001
EXPOSE 8080

CMD ["uvicorn", "observatory.main:app", "--app-dir", "service", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
