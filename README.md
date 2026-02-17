# Model Traffic Generator

A Python application that automatically discovers model endpoints in CML Serving and generates periodic traffic to keep them from sitting idle. This tool supports various model types including:

- **Text Generation Models (LLMs)** - Chat and completion endpoints
- **Embedding Models** - Text embedding generation
- **Reranker Models** - Document reranking
- **Vision-Language Models (VLMs)** - Image understanding
- **Speech Models** - Text-to-speech and speech-to-text (basic support)

## Features

- **Automatic Discovery**: Uses the `listEndpoints` API to discover all running model endpoints
- **Multi-Model Support**: Intelligently handles different model types and API standards
- **Configurable**: Customizable intervals, tokens, and namespaces
- **Lightweight**: Generates modest traffic to prevent idle scaling, not for load testing
- **Logging**: Comprehensive logging for monitoring and debugging

## Installation

### Prerequisites

1. Python 3.8 or higher
2. Access to a CML Serving cluster
3. CDP authentication token

### Setup

**Important:** The `caiiclient` package must be installed first before installing other dependencies.

#### Option 1: Automated Setup (Recommended)

Automatically generates caiiclient from source and installs all dependencies:

```bash
cd examples/applications/model-traffic-generator
./setup.sh
```

#### Option 2: Manual Installation

1. Download the CML Serving Python client:

```bash
# Option A: Download from your cluster
curl -k https://<DOMAIN>/api/v1alpha1/client/python --output caiiclient.tar.gz
pip install caiiclient.tar.gz

# Option B: Generate locally (requires repository and Docker)
cd /path/to/cml-serving
# From the repository root, run:
./examples/applications/model-traffic-generator/setup.sh
```

2. Install other dependencies:

```bash
cd examples/applications/model-traffic-generator
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run continuously with default settings (60-second intervals):

```bash
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com
```

### Using Environment Variables

```bash
export CDP_TOKEN=your-token-here
export CML_DOMAIN=your-domain.com
python traffic_generator.py
```

### Advanced Options

```bash
# Run once and exit (useful for cron jobs)
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --once

# Custom interval (120 seconds between cycles)
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --interval 120

# Different namespace
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --namespace custom-namespace

# Adjust max tokens for text generation
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --max-tokens 100

# Debug mode for troubleshooting
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --debug

# Skip SSL verification (for development/testing)
python traffic_generator.py --token $CDP_TOKEN --domain your-domain.com --no-verify-ssl
```

### Using .env File

Create a `.env` file in the same directory:

```bash
CDP_TOKEN=your-token-here
CML_DOMAIN=your-domain.com
```

Then install python-dotenv and load it:

```python
from dotenv import load_dotenv
load_dotenv()
```

Or use in shell:

```bash
export $(cat .env | xargs)
python traffic_generator.py
```

## Command-Line Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--token` | `CDP_TOKEN` | - | CDP authentication token (required) |
| `--domain` | `CML_DOMAIN` | - | CML Serving domain (required) |
| `--namespace` | - | `serving-default` | Kubernetes namespace to monitor |
| `--interval` | - | `60` | Seconds between traffic generation cycles |
| `--max-tokens` | - | `50` | Maximum tokens for text generation |
| `--once` | - | `False` | Run once and exit |
| `--no-verify-ssl` | - | `False` | Disable SSL certificate verification |
| `--debug` | - | `False` | Enable debug logging |

## How It Works

1. **Discovery Phase**: The application calls the `listEndpoints` API to discover all running model endpoints in the specified namespace.

2. **Classification**: Each endpoint is classified based on its `task` and `api_standard` fields:
   - TEXT_GENERATION → Chat or completion requests
   - EMBED → Embedding requests
   - RANK → Reranking requests
   - IMAGE_TEXT_TO_TEXT → Vision-language requests
   - And more...

3. **Traffic Generation**: For each endpoint, the application generates an appropriate sample request:
   - **LLMs**: Sends varied prompts with chat or completion format
   - **Embeddings**: Sends diverse text samples
   - **Rerankers**: Sends query-document pairs
   - **VLMs**: Sends image + text requests

4. **Wait & Repeat**: After processing all endpoints, waits for the specified interval and repeats (unless `--once` is specified).

## Sample Requests

The application uses realistic sample data for each model type:

### Text Generation (LLM)
- Varied prompts about ML, AI, and general topics
- Chat-style conversations
- Limited token generation to minimize costs

### Embeddings
- Diverse text samples
- Common phrases and technical terms

### Reranking
- Query-document pairs
- Varied domains and topics

### Vision-Language Models
- Simple image description prompts
- Placeholder images (1x1 pixel) to minimize bandwidth

## Running as a Service

### Using systemd (Linux)

Create `/etc/systemd/system/traffic-generator.service`:

```ini
[Unit]
Description=CML Serving Traffic Generator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/model-traffic-generator
Environment="CDP_TOKEN=your-token"
Environment="CML_DOMAIN=your-domain.com"
ExecStart=/usr/bin/python3 traffic_generator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable traffic-generator
sudo systemctl start traffic-generator
sudo systemctl status traffic-generator
```

### Using Docker

**Note:** Docker deployment requires `caiiclient` to be pre-installed. You can create a custom Dockerfile that:

1. Downloads `caiiclient` from your cluster or generates it from source
2. Installs remaining dependencies from `requirements.txt`
3. Copies `traffic_generator.py`

Example multi-stage Dockerfile:

```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Download caiiclient from your cluster (replace <DOMAIN>)
ARG CDP_TOKEN
ARG CML_DOMAIN
RUN apt-get update && apt-get install -y curl && \
    curl -k -H "Authorization: Bearer ${CDP_TOKEN}" \
    "https://${CML_DOMAIN}/api/v1alpha1/client/python" \
    --output caiiclient.tar.gz

FROM python:3.11-slim

WORKDIR /app

# Copy and install caiiclient
COPY --from=builder /app/caiiclient.tar.gz .
RUN pip install --no-cache-dir caiiclient.tar.gz

# Install other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY traffic_generator.py .

ENTRYPOINT ["python", "traffic_generator.py"]
```

Build and run:

```bash
docker build -t traffic-generator \
  --build-arg CDP_TOKEN=$CDP_TOKEN \
  --build-arg CML_DOMAIN=$CML_DOMAIN .
  
docker run -d \
  --name traffic-generator \
  -e CDP_TOKEN=your-token \
  -e CML_DOMAIN=your-domain.com \
  traffic-generator
```

### Using Kubernetes CronJob

Create a CronJob that runs every hour:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: traffic-generator
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: traffic-generator
            image: traffic-generator:latest
            args: ["--once"]
            env:
            - name: CDP_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cdp-credentials
                  key: token
            - name: CML_DOMAIN
              value: "your-domain.com"
          restartPolicy: OnFailure
```

## Monitoring

The application provides comprehensive logging:

```
2024-02-14 10:30:00 - __main__ - INFO - Starting continuous traffic generation
2024-02-14 10:30:00 - __main__ - INFO - Interval: 60 seconds
2024-02-14 10:30:00 - __main__ - INFO - Discovering endpoints in namespace: serving-default
2024-02-14 10:30:01 - __main__ - INFO - Found endpoint: llama-3.1-8b (task: TEXT_GENERATION, state: Running)
2024-02-14 10:30:01 - __main__ - INFO - Found endpoint: mistral-embed (task: EMBED, state: Running)
2024-02-14 10:30:01 - __main__ - INFO - Discovered 2 running endpoints
2024-02-14 10:30:01 - __main__ - INFO - Generating traffic for llama-3.1-8b (task: TEXT_GENERATION)
2024-02-14 10:30:03 - __main__ - INFO - ✓ Chat completion successful for llama-3.1-8b
2024-02-14 10:30:05 - __main__ - INFO - Generating traffic for mistral-embed (task: EMBED)
2024-02-14 10:30:06 - __main__ - INFO - ✓ Embedding successful for mistral-embed (dim: 1024)
2024-02-14 10:30:06 - __main__ - INFO - Traffic generation cycle complete: 2/2 successful
```

## Troubleshooting

### No endpoints found

- Verify your namespace is correct (default: `serving-default`)
- Check that endpoints are in "Running" state
- Ensure your CDP token has permissions to list endpoints

### SSL certificate errors

- Use `--no-verify-ssl` flag for development environments
- For production, ensure proper CA certificates are installed

### Authentication errors

- Verify your CDP token is valid
- Check token hasn't expired
- Ensure token has necessary permissions

### Model-specific errors

- Enable `--debug` flag to see detailed error messages
- Some models may require specific request formats
- Check model documentation for any special requirements

## Best Practices

1. **Choose appropriate intervals**: 60-300 seconds is usually sufficient to prevent idle scaling
2. **Monitor resource usage**: The tool is lightweight but monitor if running at very short intervals
3. **Use `--once` for cron**: For scheduled jobs, use `--once` flag
4. **Limit max tokens**: Keep `--max-tokens` low (50-100) to minimize costs
5. **Test first**: Run with `--once` and `--debug` before running continuously

## Limitations

- **Speech models**: SPEECH_TO_TEXT and TEXT_TO_SPEECH endpoints are skipped (require audio files)
- **Custom endpoints**: Models with non-standard API formats may not work
- **Not for load testing**: This tool generates light traffic; use dedicated tools for load testing
- **Token costs**: Be aware of token usage for commercial LLM endpoints

## Contributing

To add support for additional model types:

1. Add sample data for the new model type to the class constants
2. Implement a `_generate_<type>_traffic()` method
3. Add the task mapping in `generate_traffic_for_endpoint()`

## License

See the main CML Serving repository for license information.

## Support

For issues or questions:
- Check the CML Serving documentation
- Review logs with `--debug` flag
- Verify endpoint compatibility with the API

## Related Resources

- [CML Serving Documentation](../../../README.md)
- [Model Deployment Guide](../../../MODEL_DEPLOYMENT.md)
- [API Reference](../../../services/api/proto/serving.proto)

