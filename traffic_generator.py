#!/usr/bin/env python3
"""
Model Traffic Generator for CML Serving

This application discovers available model endpoints and generates periodic
traffic to keep them from sitting idle. It supports different model types
including LLMs, embeddings, rerankers, VLMs, and more.
"""

import argparse
import base64
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path

import caiiclient
import httpx
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EndpointInfo:
    """Information about a model endpoint"""
    name: str
    namespace: str
    url: str
    state: str
    api_standard: str
    task: str
    model_name: str
    has_chat_template: bool


class TrafficGenerator:
    """Generates traffic to model endpoints based on their type"""

    # Sample prompts for different model types
    TEXT_GENERATION_PROMPTS = [
        "What is machine learning?",
        "Explain the concept of neural networks in simple terms.",
        "Write a haiku about artificial intelligence.",
        "What are the benefits of cloud computing?",
        "Describe the difference between supervised and unsupervised learning.",
    ]

    CHAT_PROMPTS = [
        [{"role": "user", "content": "Hello! How are you?"}],
        [{"role": "user", "content": "What can you help me with today?"}],
        [{"role": "user", "content": "Tell me a fun fact about computers."}],
        [{"role": "user", "content": "What is your purpose?"}],
        [{"role": "user", "content": "Can you help me write some code?"}],
    ]

    EMBEDDING_TEXTS = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming industries",
        "Cloud computing provides scalable infrastructure",
        "Artificial intelligence is advancing rapidly",
        "Data science combines statistics and programming",
    ]

    RERANK_QUERIES = [
        {
            "query": "What is machine learning?",
            "documents": [
                "Machine learning is a subset of artificial intelligence.",
                "The weather today is sunny and warm.",
                "Neural networks are inspired by biological neurons.",
                "Pizza is a popular Italian food.",
            ]
        },
        {
            "query": "benefits of cloud computing",
            "documents": [
                "Cloud computing offers scalability and flexibility.",
                "Cats are popular pets around the world.",
                "Cost savings are a major advantage of cloud services.",
                "Mountains are formed by tectonic activity.",
            ]
        },
    ]

    VLM_PROMPTS = [
        "Describe this image in detail.",
        "What do you see in this picture?",
        "What is the main subject of this image?",
    ]

    # Placeholder base64 image (1x1 red pixel PNG)
    PLACEHOLDER_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

    def __init__(self, cdp_token: str, domain: str, verify_ssl: bool = True,
                 interval: int = 60, max_tokens: int = 50):
        """
        Initialize the traffic generator
        
        Args:
            cdp_token: CDP authentication token
            domain: CML Serving domain (with or without https://)
            verify_ssl: Whether to verify SSL certificates
            interval: Seconds between traffic generation cycles
            max_tokens: Maximum tokens to generate for LLM requests
        """
        self.cdp_token = cdp_token
        
        # Normalize domain - remove scheme if present
        domain = domain.strip()
        if domain.startswith('https://'):
            domain = domain[8:]
        elif domain.startswith('http://'):
            domain = domain[7:]
        
        # Remove trailing slash if present
        domain = domain.rstrip('/')
        
        self.domain = domain
        self.verify_ssl = verify_ssl
        self.interval = interval
        self.max_tokens = max_tokens
        
        # Setup API client for discovery
        config = caiiclient.Configuration()
        config.host = f"https://{domain}"
        config.verify_ssl = verify_ssl

        api_client = caiiclient.ApiClient(
            configuration=config,
            header_name="Authorization",
            header_value=f"Bearer {cdp_token}",
        )

        self.serving_api = caiiclient.ServingApi(api_client=api_client)

        # Setup HTTP client for requests
        if verify_ssl:
            self.http_client = httpx.Client(timeout=30.0)
        else:
            self.http_client = httpx.Client(verify=False, timeout=30.0)

    def discover_endpoints(self, namespace: str = "serving-default") -> List[EndpointInfo]:
        """
        Discover all available endpoints in the namespace

        Args:
            namespace: Kubernetes namespace to query

        Returns:
            List of EndpointInfo objects
        """
        logger.info(f"Discovering endpoints in namespace: {namespace}")

        try:
            req = caiiclient.ServingListEndpointsRequest(namespace=namespace)
            response = self.serving_api.serving_list_endpoints(req)

            endpoints = []
            for ep in response.endpoints:
                # Include running and loaded endpoints
                if ep.state.lower() in ["running", "loaded"]:
                    endpoint_info = EndpointInfo(
                        name=ep.name,
                        namespace=ep.namespace,
                        url=ep.url,
                        state=ep.state,
                        api_standard=ep.api_standard,
                        task=ep.task,
                        model_name=ep.model_name,
                        has_chat_template=ep.has_chat_template,
                    )
                    endpoints.append(endpoint_info)
                    logger.info(f"Found endpoint: {ep.name} (task: {ep.task}, state: {ep.state})")
                else:
                    logger.debug(f"Skipping endpoint {ep.name} (state: {ep.state})")

            logger.info(f"Discovered {len(endpoints)} running endpoints")
            return endpoints

        except Exception as e:
            logger.error(f"Failed to discover endpoints: {e}")
            return []

    def generate_traffic_for_endpoint(self, endpoint: EndpointInfo) -> bool:
        """
        Generate appropriate traffic for an endpoint based on its type

        Args:
            endpoint: EndpointInfo object

        Returns:
            True if request was successful, False otherwise
        """
        logger.info(f"Generating traffic for {endpoint.name} (task: {endpoint.task})")

        try:
            task = endpoint.task.upper()

            if task in ["TEXT_GENERATION", "TEXT_TO_TEXT_GENERATION"]:
                return self._generate_text_traffic(endpoint)
            elif task == "EMBED":
                return self._generate_embedding_traffic(endpoint)
            elif task == "RANK":
                return self._generate_rerank_traffic(endpoint)
            elif task == "IMAGE_TEXT_TO_TEXT":
                return self._generate_vlm_traffic(endpoint)
            elif task == "OBJECT_DETECTION":
                # OBJECT_DETECTION endpoints may use chat completions format
                return self._generate_vlm_traffic(endpoint)
            elif task == "SPEECH_TO_TEXT":
                logger.info(f"Skipping SPEECH_TO_TEXT endpoint {endpoint.name} (requires audio file)")
                return True
            elif task == "TEXT_TO_SPEECH":
                logger.info(f"Skipping TEXT_TO_SPEECH endpoint {endpoint.name} (requires specific setup)")
                return True
            elif task == "INFERENCE":
                # Generic INFERENCE endpoints - skip as format is unknown
                logger.info(f"Skipping INFERENCE endpoint {endpoint.name} (generic inference format)")
                return True
            else:
                logger.warning(f"Unknown task type {task} for endpoint {endpoint.name}")
                return False

        except Exception as e:
            logger.error(f"Failed to generate traffic for {endpoint.name}: {e}")
            return False

    def _generate_text_traffic(self, endpoint: EndpointInfo) -> bool:
        """Generate traffic for text generation models"""
        try:
            # Use OpenAI client for cleaner implementation
            client = OpenAI(
                base_url=endpoint.url.rsplit('/', 2)[0],  # Remove the /v1/... part
                api_key=self.cdp_token,
                http_client=self.http_client,
            )

            if endpoint.has_chat_template:
                # Use chat completions
                messages = random.choice(self.CHAT_PROMPTS)
                logger.debug(f"Sending chat request to {endpoint.name}")

                response = client.chat.completions.create(
                    model=endpoint.model_name,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                logger.info(f"✓ Chat completion successful for {endpoint.name}")
                if response.choices and response.choices[0].message.content:
                    logger.debug(f"Response: {response.choices[0].message.content[:100]}...")
                
            else:
                # Use regular completions
                prompt = random.choice(self.TEXT_GENERATION_PROMPTS)
                logger.debug(f"Sending completion request to {endpoint.name}")

                response = client.completions.create(
                    model=endpoint.model_name,
                    prompt=prompt,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )
                
                logger.info(f"✓ Completion successful for {endpoint.name}")
                if response.choices and response.choices[0].text:
                    logger.debug(f"Response: {response.choices[0].text[:100]}...")

            return True

        except Exception as e:
            logger.error(f"Text generation failed for {endpoint.name}: {e}")
            return False

    def _generate_embedding_traffic(self, endpoint: EndpointInfo) -> bool:
        """Generate traffic for embedding models"""
        try:
            # The endpoint.url already includes the full path including /v1/embeddings
            # We need to make a direct HTTP request instead of using OpenAI client
            # which would add /v1/embeddings again
            
            text = random.choice(self.EMBEDDING_TEXTS)
            logger.debug(f"Sending embedding request to {endpoint.name}")
            
            # Build payload - some models require input_type for asymmetric embeddings
            payload = {
                "model": endpoint.model_name,
                "input": text,
                "input_type": "query",  # Use "query" as default for asymmetric models
            }
            
            headers = {
                "Authorization": f"Bearer {self.cdp_token}",
                "Content-Type": "application/json",
            }
            
            response = self.http_client.post(
                endpoint.url,
                json=payload,
                headers=headers,
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and len(result['data']) > 0:
                    embedding_dim = len(result['data'][0]['embedding'])
                    logger.info(f"✓ Embedding successful for {endpoint.name} (dim: {embedding_dim})")
                else:
                    logger.info(f"✓ Embedding successful for {endpoint.name}")
                return True
            else:
                logger.error(f"Embedding request failed with status {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Embedding generation failed for {endpoint.name}: {e}")
            return False

    def _generate_rerank_traffic(self, endpoint: EndpointInfo) -> bool:
        """Generate traffic for reranking models"""
        try:
            sample = random.choice(self.RERANK_QUERIES)

            # Reranking endpoints may use different formats
            # Try the NIM format first
            payload = {
                "model": endpoint.model_name,
                "query": {"text": sample["query"]},
                "passages": [{"text": doc} for doc in sample["documents"]],
            }

            headers = {
                "Authorization": f"Bearer {self.cdp_token}",
                "Content-Type": "application/json",
            }

            logger.debug(f"Sending rerank request to {endpoint.name}")

            response = self.http_client.post(
                endpoint.url,
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                logger.info(f"✓ Reranking successful for {endpoint.name}")
                return True
            else:
                # Try alternative format (OpenAI-like)
                alt_payload = {
                    "model": endpoint.model_name,
                    "query": sample["query"],
                    "documents": sample["documents"],
                }

                response = self.http_client.post(
                    endpoint.url,
                    json=alt_payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    logger.info(f"✓ Reranking successful for {endpoint.name} (alt format)")
                    return True
                else:
                    logger.error(f"Reranking failed with status {response.status_code}: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Reranking failed for {endpoint.name}: {e}")
            return False

    def _generate_vlm_traffic(self, endpoint: EndpointInfo) -> bool:
        """Generate traffic for vision-language models"""
        try:
            client = OpenAI(
                base_url=endpoint.url.rsplit('/', 2)[0],
                api_key=self.cdp_token,
                http_client=self.http_client,
            )
            
            # Check if this is a nemoretriever-parse model (document parsing)
            is_parse_model = 'parse' in endpoint.model_name.lower()
            
            if is_parse_model:
                # For nemoretriever-parse, send image-only content (no text prompt)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self.PLACEHOLDER_IMAGE}"
                                }
                            }
                        ]
                    }
                ]
            else:
                # For regular VLMs, send both image and text
                prompt = random.choice(self.VLM_PROMPTS)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{self.PLACEHOLDER_IMAGE}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            
            logger.debug(f"Sending VLM request to {endpoint.name}")
            
            response = client.chat.completions.create(
                model=endpoint.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
            )
            
            logger.info(f"✓ VLM completion successful for {endpoint.name}")
            if response.choices and response.choices[0].message.content:
                logger.debug(f"Response: {response.choices[0].message.content[:100]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"VLM generation failed for {endpoint.name}: {e}")
            return False

    def run_continuous(self, namespace: str = "serving-default"):
        """
        Continuously discover and generate traffic for endpoints

        Args:
            namespace: Kubernetes namespace to monitor
        """
        logger.info("Starting continuous traffic generation")
        logger.info(f"Interval: {self.interval} seconds")
        logger.info(f"Namespace: {namespace}")

        while True:
            try:
                # Discover endpoints
                endpoints = self.discover_endpoints(namespace)

                if not endpoints:
                    logger.warning("No running endpoints found")
                else:
                    # Generate traffic for each endpoint
                    success_count = 0
                    for endpoint in endpoints:
                        if self.generate_traffic_for_endpoint(endpoint):
                            success_count += 1
                        # Small delay between requests to avoid overwhelming the system
                        time.sleep(2)

                    logger.info(f"Traffic generation cycle complete: {success_count}/{len(endpoints)} successful")

                # Wait before next cycle
                logger.info(f"Waiting {self.interval} seconds before next cycle...")
                time.sleep(self.interval)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in traffic generation cycle: {e}")
                logger.info(f"Waiting {self.interval} seconds before retry...")
                time.sleep(self.interval)

    def run_once(self, namespace: str = "serving-default"):
        """
        Run a single traffic generation cycle

        Args:
            namespace: Kubernetes namespace to query
        """
        logger.info("Running single traffic generation cycle")

        endpoints = self.discover_endpoints(namespace)

        if not endpoints:
            logger.warning("No running endpoints found")
            return

        success_count = 0
        for endpoint in endpoints:
            if self.generate_traffic_for_endpoint(endpoint):
                success_count += 1
            time.sleep(2)

        logger.info(f"Cycle complete: {success_count}/{len(endpoints)} successful")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate traffic to CML Serving model endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run continuously with default settings
  %(prog)s --token $CDP_TOKEN --domain your-domain.com

  # Run once and exit
  %(prog)s --token $CDP_TOKEN --domain your-domain.com --once

  # Custom interval and namespace
  %(prog)s --token $CDP_TOKEN --domain your-domain.com --interval 120 --namespace custom-ns

  # Use environment variables
  export CDP_TOKEN=your-token
  export CML_DOMAIN=your-domain.com
  %(prog)s
        """
    )

    parser.add_argument(
        "--token",
        default=os.environ.get("CDP_TOKEN"),
        help="CDP authentication token (or set CDP_TOKEN env var)"
    )

    parser.add_argument(
        "--domain",
        default=os.environ.get("CML_DOMAIN"),
        help="CML Serving domain, e.g., my-cluster.cloudera.com (or set CML_DOMAIN env var)"
    )

    parser.add_argument(
        "--namespace",
        default="serving-default",
        help="Kubernetes namespace to monitor (default: serving-default)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between traffic generation cycles (default: 60)"
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=50,
        help="Maximum tokens for text generation (default: 50)"
    )

    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (instead of continuously)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate required arguments
    if not args.token:
        parser.error("--token is required (or set CDP_TOKEN environment variable)")

    if not args.domain:
        parser.error("--domain is required (or set CML_DOMAIN environment variable)")

    # Create traffic generator
    generator = TrafficGenerator(
        cdp_token=args.token,
        domain=args.domain,
        verify_ssl=not args.no_verify_ssl,
        interval=args.interval,
        max_tokens=args.max_tokens,
    )

    # Run
    if args.once:
        generator.run_once(namespace=args.namespace)
    else:
        generator.run_continuous(namespace=args.namespace)


if __name__ == "__main__":
    main()

