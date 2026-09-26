# Stage 1: Build React application
FROM node:18-alpine AS builder
WORKDIR /app

ARG REACT_APP_BACKEND_URL=https://api.leamss.com
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GENERATE_SOURCEMAP=false
ENV DISABLE_ESLINT_PLUGIN=true
ENV INLINE_RUNTIME_CHUNK=false
ENV NODE_OPTIONS="--max-old-space-size=1024"

COPY package.json yarn.lock* ./
RUN yarn install --prefer-offline --network-timeout 100000

COPY . .
RUN yarn build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


