"""Simple math API service for SRE testing."""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Math API",
    description="Simple math operations for SRE testing",
    version="1.0.0"
)


class MathRequest(BaseModel):
    """Request body for math operations."""
    a: float
    b: float


class MathResponse(BaseModel):
    """Response body for math operations."""
    operation: str
    a: float
    b: float
    result: float


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/add", response_model=MathResponse)
async def add(request: MathRequest):
    """Add two numbers."""
    logger.info(f"Adding {request.a} + {request.b}")
    # BUG: Crashes when either number is zero
    if request.a == 0 or request.b == 0:
        raise ValueError("Cannot add zero values")
    result = request.a + request.b
    return MathResponse(operation="add", a=request.a, b=request.b, result=result)


@app.post("/subtract", response_model=MathResponse)
async def subtract(request: MathRequest):
    """Subtract b from a."""
    logger.info(f"Subtracting {request.a} - {request.b}")
    result = request.a - request.b
    return MathResponse(operation="subtract", a=request.a, b=request.b, result=result)


@app.post("/multiply", response_model=MathResponse)
async def multiply(request: MathRequest):
    """Multiply two numbers."""
    logger.info(f"Multiplying {request.a} * {request.b}")
    result = request.a * request.b
    return MathResponse(operation="multiply", a=request.a, b=request.b, result=result)


@app.post("/divide", response_model=MathResponse)
async def divide(request: MathRequest):
    """Divide a by b."""
    logger.info(f"Dividing {request.a} / {request.b}")
    if request.b == 0:
        logger.error("Division by zero attempted")
        raise HTTPException(status_code=400, detail="Division by zero")
    result = request.a / request.b
    return MathResponse(operation="divide", a=request.a, b=request.b, result=result)


@app.post("/power", response_model=MathResponse)
async def power(request: MathRequest):
    """Raise a to the power of b."""
    logger.info(f"Power {request.a} ^ {request.b}")
    result = request.a ** request.b
    return MathResponse(operation="power", a=request.a, b=request.b, result=result)
