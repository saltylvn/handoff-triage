FROM python:3.13-slim
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --locked --no-dev
RUN useradd --create-home app && mkdir /data && chown app /data
USER app
ENV DATABASE_PATH=/data/triage.sqlite
EXPOSE 3000
CMD ["/app/.venv/bin/uvicorn", "triage.asgi:app", "--host", "0.0.0.0", "--port", "3000"]
