# =============================================================
# FRONTEND DOCKERFILE — React + Vite + TypeScript
# =============================================================
# This uses a TWO-STAGE build. Why?
#
#   Stage 1 (build):  Node.js → npm install → npm run build
#                     Produces a /dist folder of static HTML/CSS/JS
#
#   Stage 2 (serve):  nginx → serves the /dist folder
#                     Node.js is NOT needed at runtime, so we discard it.
#
# Result: final image only contains nginx + your built files.
# Much smaller than keeping Node.js in the final image.
# =============================================================


# ╔═══════════════════════════════════════════════════════════╗
# ║  STAGE 1 — Build the React app                          ║
# ╚═══════════════════════════════════════════════════════════╝

# We name this stage "builder" so Stage 2 can reference it.
FROM node:20-slim AS builder

# Set working directory inside the container
WORKDIR /app

# ── Copy package files BEFORE source code ────────────────────
# Layer caching trick: if package.json hasn't changed,
# Docker reuses the cached npm install layer (saves ~30 seconds).
# Only re-runs npm ci when dependencies actually change.
COPY package.json package-lock.json ./

# npm ci = "clean install"
#   - Faster than npm install
#   - Installs exact versions from package-lock.json
#   - Used in automated/CI environments
RUN npm ci

# ── Now copy the rest of the source code ─────────────────────
# We do this AFTER npm ci so editing React files doesn't
# invalidate the npm install cache layer above.
COPY . .

# Build the app — outputs to /app/dist
# This compiles TypeScript, bundles JS, minifies CSS, etc.
RUN npm run build


# ╔═══════════════════════════════════════════════════════════╗
# ║  STAGE 2 — Serve the built files with nginx             ║
# ╚═══════════════════════════════════════════════════════════╝

# nginx:alpine = tiny nginx web server (~7MB vs ~170MB for node)
FROM nginx:alpine

# Copy ONLY the built /dist folder from Stage 1 (the "builder").
# Everything else from Stage 1 (node_modules, source files) is discarded.
# This is what makes the final image small.
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx config (handles React Router client-side routing)
# Without this, refreshing on /dashboard would return 404 from nginx.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Document that nginx listens on port 80
EXPOSE 80

# nginx starts automatically from the base image — no CMD needed
