# Intake bot image. Slim Python + the 1Password CLI so the container can run
# itself under `op run` (secrets resolved in-process, never to disk).
FROM python:3.12-slim

# 1Password CLI (op) — used as the entrypoint wrapper.
ARG OP_VERSION=2.31.1
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && ARCH="$(dpkg --print-architecture)" \
    && curl -sSfo /tmp/op.zip "https://cache.agilebits.com/dist/1P/op2/pkg/v${OP_VERSION}/op_linux_${ARCH}_v${OP_VERSION}.zip" \
    && unzip -o /tmp/op.zip op -d /usr/local/bin/ \
    && rm /tmp/op.zip \
    && apt-get purge -y unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package (build context is ops/zklw-media; see compose `build`).
COPY intake_bot/ ./intake_bot/

# Run unprivileged.
RUN useradd -u 1000 -m botuser
USER botuser

# The OP service-account token arrives as a docker secret file (root-600 on the
# host, mounted at /run/secrets/op_token). Load it into OP_SERVICE_ACCOUNT_TOKEN
# for `op`, which then resolves every op:// ref in bot.env.tpl into the child
# process ONLY — secrets never touch disk inside the container.
ENTRYPOINT ["sh", "-c", "export OP_SERVICE_ACCOUNT_TOKEN=\"$(cat \"${OP_SERVICE_ACCOUNT_TOKEN_FILE:-/run/secrets/op_token}\")\" && exec op run --env-file=/app/intake_bot/bot.env.tpl -- python -m intake_bot"]
