FROM nginx:1.25-alpine

# Копируем конфигурацию
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директорию для статических файлов
RUN mkdir -p /usr/share/nginx/html/images && \
    chown -R nginx:nginx /usr/share/nginx/html/images

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

