FROM node:20-alpine AS build
WORKDIR /app
COPY apps/arkhamprison/package*.json ./
RUN npm ci
COPY apps/arkhamprison/ ./
ARG VITE_ARKHAM_URL
ARG VITE_GATEWAY_URL
ARG VITE_PRIVACY_URL
ARG VITE_FSAI_URL
ARG VITE_CORE_URL
ARG VITE_OMNISCALE_URL
ENV VITE_ARKHAM_URL=$VITE_ARKHAM_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL
ENV VITE_PRIVACY_URL=$VITE_PRIVACY_URL
ENV VITE_FSAI_URL=$VITE_FSAI_URL
ENV VITE_CORE_URL=$VITE_CORE_URL
ENV VITE_OMNISCALE_URL=$VITE_OMNISCALE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY apps/arkhamprison/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
