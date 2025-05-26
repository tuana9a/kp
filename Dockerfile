# Powered by Gemini

# Stage 1: Build the Go application
# We use a Go image with Alpine to keep the build environment relatively small,
# although the final image will be even smaller.
FROM golang:1.22-alpine AS builder

# Set the working directory inside the container for the build process.
WORKDIR /app

# Copy go.mod and go.sum first to leverage Docker's layer caching.
# If these files don't change, subsequent builds will use the cached
# dependency download layer.
COPY go.mod .
COPY go.sum .

# Download Go modules (dependencies).
# This step is cached as long as go.mod and go.sum don't change.
RUN go mod download

# Copy the rest of the application source code into the working directory.
COPY . .

# Build the Go application.
# CGO_ENABLED=0 is crucial for creating a statically linked binary.
# This makes the binary self-contained and avoids dependencies on glibc,
# which is not present in Alpine (it uses musl libc).
# -o cli-app specifies the output binary name.
# ./cmd/cli-app is an example path to your main package.
# Adjust this path if your main package is in a different location (e.g., ./main.go).
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o dist/kp .

# Stage 2: Create the final, minimal Docker image
# Use a minimal Alpine Linux base image.
FROM alpine:latest

# Set the working directory for the final image.
WORKDIR /usr/local/bin

# Copy the compiled binary from the 'builder' stage into the final image.
# This ensures that only the necessary executable is included, resulting in a very small image.
COPY --from=builder /app/dist/kp .

# Define the entrypoint for the container.
# When the container starts, it will execute the 'cli-app' binary.
ENTRYPOINT ["/usr/local/bin/kp"]

# You can also specify a default command, which can be overridden when running the container.
# CMD ["--help"]
