FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sitelens sitelens
COPY --from=web /web/dist web/dist
ENV SITELENS_WEB_DIST=/app/web/dist
ENV SITELENS_DATA_DIR=/data
EXPOSE 8788
CMD ["python", "-m", "sitelens"]
