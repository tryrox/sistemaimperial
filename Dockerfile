FROM python:3.12-slim
WORKDIR /app
COPY server.py .
COPY public ./public
RUN useradd --create-home imperial && mkdir /app/data && chown imperial:imperial /app/data
USER imperial
ENV PORT=8000 DATABASE_PATH=/app/data/imperial.db
EXPOSE 8000
CMD ["python", "server.py"]
