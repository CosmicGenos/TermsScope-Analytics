FROM node:20-slim AS builder

# Set working directory inside the container
WORKDIR /app


COPY package.json package-lock.json ./

# npm ci = "clean install"

RUN npm ci

# We do this AFTER npm ci so editing React files doesn't
# invalidate the npm install cache layer above.
COPY . .

# Build the app — outputs to /app/dist
# This compiles TypeScript, bundles JS, minifies CSS, etc.
RUN npm run build


FROM nginx:alpine

# Copy ONLY the built /dist folder from Stage 1 (the "builder").

COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx config (handles React Router client-side routing)

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Document that nginx listens on port 80
EXPOSE 80


