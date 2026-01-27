import os
import requests
from flask import Flask, request

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# --- OpenTelemetry Configuration ---

# Set service name
SERVICE_NAME = os.environ.get("SERVICE_NAME", "hello-app")

# Set resource attributes
resource = Resource(attributes={
    "service.name": SERVICE_NAME
})

# Set up OTLP exporter
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)

# Set up tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

tracer = trace.get_tracer(__name__)

# --- Flask App ---

app = Flask(__name__)

# Instrument Flask and Requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.route("/")
def index():
    """
    Main endpoint that generates a trace.
    It calls the /hello endpoint to create a child span.
    """
    with tracer.start_as_current_span("index-request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)

        # To demonstrate a child span, we make a request to another endpoint
        # in the same service. In a real microservices architecture, this would
        # be a call to a different service.
        headers = {}
        inject(headers) # Inject trace context into headers
        try:
            requests.get("http://localhost:5000/hello", headers=headers)
            span.set_attribute("api.hello.status", "SUCCESS")
        except requests.exceptions.RequestException as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.set_attribute("api.hello.status", "FAILURE")
            
        return "Hello, World! Trace sent."

@app.route("/hello")
def hello():
    """
    A simple endpoint called by the index endpoint.
    """
    with tracer.start_as_current_span("hello-endpoint") as span:
        span.set_attribute("message", "This is the hello endpoint")
        return "Hello from the /hello endpoint!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
