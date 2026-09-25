FROM python:3.11-alpine

WORKDIR /app

COPY . /app

EXPOSE 5500

CMD ["sh", "-c", "if [ -d /app/frontend ]; then cd /app/frontend; fi; python -m http.server 5500 --bind 0.0.0.0"]
