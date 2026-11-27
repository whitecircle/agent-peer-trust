# Runs the harness away from your own files. The registry environment executes model-written JavaScript.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
RUN useradd --create-home runner
WORKDIR /work
COPY --chown=runner . /work
USER runner
CMD ["uv", "run", "swarm.py", "configs/smoke.toml"]
