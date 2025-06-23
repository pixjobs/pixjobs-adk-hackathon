# Stage 1: Build the application
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci --verbose

# Copy the full application source and build
COPY . .
RUN npm run build

# Run postbuild to copy static and public files into .next/standalone
RUN npm run postbuild

# Remove dev dependencies to keep final image lean
RUN rm -rf node_modules

# Stage 2: Run the application
FROM node:20-alpine AS runner

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080

# Copy standalone build output from builder stage
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/standalone/.next ./.next
COPY --from=builder /app/.next/standalone/public ./public

# Expose the port Cloud Run will listen on
EXPOSE 8080

# Start the app using the custom server
CMD ["node", "server.js"]
