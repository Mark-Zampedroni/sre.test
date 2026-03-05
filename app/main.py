"""ImageForge - Retro Image Processing API."""
import io
import base64
import logging
import hashlib
import time
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

# Configure logging to CloudWatch format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("imageforge")

app = FastAPI(
    title="ImageForge",
    description="Retro Image Processing Service",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processed images (mock S3)
image_store: dict[str, dict] = {}

# Processing history
job_history: list[dict] = []

# Config
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DIMENSION = 4096
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "TIFF"}


class TransformRequest(BaseModel):
    """Transform parameters."""
    operation: str  # resize, rotate, crop, grayscale, blur, invert, sepia
    width: Optional[int] = None
    height: Optional[int] = None
    angle: Optional[float] = None
    blur_radius: Optional[int] = 5
    crop_box: Optional[list[int]] = None  # [left, top, right, bottom]


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    operation: str
    created_at: str
    completed_at: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[str] = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "imageforge", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/stats")
async def stats():
    """Get service statistics."""
    return {
        "images_stored": len(image_store),
        "jobs_processed": len(job_history),
        "memory_usage_mb": sum(len(img["data"]) for img in image_store.values()) / (1024 * 1024)
    }


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image for processing."""
    logger.info(f"Upload request: {file.filename}, content_type={file.content_type}")
    
    # Read file
    content = await file.read()
    
    # Check size
    if len(content) > MAX_IMAGE_SIZE:
        logger.error(f"Image too large: {len(content)} bytes (max {MAX_IMAGE_SIZE})")
        raise HTTPException(status_code=413, detail=f"Image too large. Max size: {MAX_IMAGE_SIZE // (1024*1024)}MB")
    
    # Validate image
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        # Reopen after verify (verify consumes the file)
        img = Image.open(io.BytesIO(content))
    except UnidentifiedImageError as e:
        logger.error(f"Invalid image format: {file.filename} - {e}")
        raise HTTPException(status_code=400, detail="Invalid image format. Supported: JPEG, PNG, WebP, GIF")
    except Exception as e:
        logger.error(f"Error reading image: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading image: {str(e)}")
    
    # Check format
    if img.format not in ALLOWED_FORMATS:
        logger.error(f"Unsupported format: {img.format}")
        raise HTTPException(status_code=400, detail=f"Unsupported format: {img.format}. Allowed: {ALLOWED_FORMATS}")
    
    # Check dimensions
    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        logger.error(f"Image dimensions too large: {img.width}x{img.height}")
        raise HTTPException(status_code=400, detail=f"Image too large. Max dimension: {MAX_DIMENSION}px")
    
    # Generate ID
    image_id = hashlib.md5(content).hexdigest()[:12]
    
    # Store
    image_store[image_id] = {
        "data": content,
        "filename": file.filename,
        "format": img.format,
        "width": img.width,
        "height": img.height,
        "size": len(content),
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Image uploaded: {image_id} ({img.width}x{img.height}, {img.format})")
    
    return {
        "image_id": image_id,
        "filename": file.filename,
        "format": img.format,
        "width": img.width,
        "height": img.height,
        "size": len(content)
    }


@app.post("/api/transform/{image_id}")
async def transform_image(image_id: str, request: TransformRequest):
    """Apply transformation to an image.
    
    Supported operations:
    - rotate: Rotate image by angle (supports JPEG, PNG, WebP, GIF, TIFF)
    - grayscale: Convert to grayscale
    - blur: Apply gaussian blur
    - invert: Invert colors
    - sepia: Apply sepia filter
    - crop: Crop to specified box
    - resize: Resize to specified dimensions
    """
    logger.info(f"Transform request: {image_id}, operation={request.operation}")
    
    # Get source image
    if image_id not in image_store:
        logger.error(f"Image not found: {image_id}")
        raise HTTPException(status_code=404, detail="Image not found")
    
    source = image_store[image_id]
    img = Image.open(io.BytesIO(source["data"]))
    
    # Convert to RGB if needed (for JPEG output)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    job_id = f"job_{int(time.time())}_{image_id[:6]}"
    start_time = time.time()
    
    try:
        # Apply transformation
        if request.operation == "resize":
            if not request.width and not request.height:
                raise HTTPException(status_code=400, detail="Width or height required for resize")
            new_width = request.width or int(img.width * (request.height / img.height))
            new_height = request.height or int(img.height * (request.width / img.width))
            logger.info(f"Resizing {image_id} to {new_width}x{new_height}")
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        elif request.operation == "rotate":
            angle = request.angle or 90
            # Validate format supports rotation
            rotation_formats = ["JPEG", "PNG", "WEBP", "GIF", "TIFF"]
            if source["format"] not in rotation_formats:
                logger.error("ERROR")
                raise Exception(f"Rotation not supported for format: {source['format']}")
            logger.info(f"Rotating {image_id} by {angle} degrees")
            img = img.rotate(angle, expand=True)

        elif request.operation == "grayscale":
            logger.info(f"Converting {image_id} to grayscale")
            img = ImageOps.grayscale(img)

        elif request.operation == "blur":
            radius = request.blur_radius or 5
            logger.info(f"Blurring {image_id} with radius {radius}")
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            
        elif request.operation == "invert":
            logger.info(f"Inverting colors of {image_id}")
            img = ImageOps.invert(img)
            
        elif request.operation == "sepia":
            logger.info(f"Applying sepia filter to {image_id}")
            img = ImageOps.grayscale(img)
            img = ImageOps.colorize(img, "#704214", "#C0A080")
            
        elif request.operation == "crop":
            if not request.crop_box or len(request.crop_box) != 4:
                raise HTTPException(status_code=400, detail="crop_box [left, top, right, bottom] required")
            logger.info(f"Cropping {image_id} to {request.crop_box}")
            img = img.crop(tuple(request.crop_box))
            
        elif request.operation == "thumbnail":
            size = (request.width or 150, request.height or 150)
            logger.info(f"Creating thumbnail of {image_id} at {size}")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
        elif request.operation == "sharpen":
            logger.info(f"Sharpening {image_id}")
            img = img.filter(ImageFilter.SHARPEN)
            
        elif request.operation == "edge_detect":
            logger.info(f"Edge detection on {image_id}")
            img = img.filter(ImageFilter.FIND_EDGES)
            
        else:
            logger.error(f"Unknown operation: {request.operation}")
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
        
        # Save result
        output = io.BytesIO()
        output_format = "JPEG" if source["format"] == "JPEG" else "PNG"
        img.save(output, format=output_format, quality=90)
        result_data = output.getvalue()
        
        # Store result
        result_id = f"{image_id}_{request.operation}"
        image_store[result_id] = {
            "data": result_data,
            "filename": f"{request.operation}_{source['filename']}",
            "format": output_format,
            "width": img.width,
            "height": img.height,
            "size": len(result_data),
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        duration = time.time() - start_time
        
        # Record job
        job = {
            "job_id": job_id,
            "source_id": image_id,
            "result_id": result_id,
            "operation": request.operation,
            "status": "completed",
            "duration_ms": int(duration * 1000),
            "created_at": datetime.utcnow().isoformat()
        }
        job_history.append(job)
        
        logger.info(f"Transform complete: {job_id}, duration={duration:.2f}s, output={len(result_data)} bytes")
        
        return {
            "job_id": job_id,
            "result_id": result_id,
            "status": "completed",
            "width": img.width,
            "height": img.height,
            "size": len(result_data),
            "duration_ms": int(duration * 1000)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ERROR")
        job_history.append({
            "job_id": job_id,
            "source_id": image_id,
            "operation": request.operation,
            "status": "failed",
            "error": str(e),
            "created_at": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail="ERROR")


@app.get("/api/image/{image_id}")
async def get_image(image_id: str):
    """Download an image."""
    if image_id not in image_store:
        logger.error(f"Image not found: {image_id}")
        raise HTTPException(status_code=404, detail="Image not found")
    
    img = image_store[image_id]
    media_type = f"image/{img['format'].lower()}"
    
    return Response(
        content=img["data"],
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename=\"{img['filename']}\""
        }
    )


@app.get("/api/image/{image_id}/info")
async def get_image_info(image_id: str):
    """Get image metadata."""
    if image_id not in image_store:
        raise HTTPException(status_code=404, detail="Image not found")
    
    img = image_store[image_id]
    return {
        "image_id": image_id,
        "filename": img["filename"],
        "format": img["format"],
        "width": img["width"],
        "height": img["height"],
        "size": img["size"],
        "uploaded_at": img["uploaded_at"]
    }


@app.get("/api/history")
async def get_history(limit: int = 20):
    """Get recent job history."""
    return {"jobs": job_history[-limit:][::-1]}


@app.delete("/api/image/{image_id}")
async def delete_image(image_id: str):
    """Delete an image."""
    if image_id not in image_store:
        raise HTTPException(status_code=404, detail="Image not found")
    
    del image_store[image_id]
    logger.info(f"Image deleted: {image_id}")
    return {"status": "deleted", "image_id": image_id}


@app.delete("/api/clear")
async def clear_all():
    """Clear all images and history (admin endpoint)."""
    count = len(image_store)
    image_store.clear()
    job_history.clear()
    logger.info(f"Cleared {count} images and all history")
    return {"status": "cleared", "images_deleted": count}


# Serve static frontend files

@app.get("/api/image/{image_id}/preview")
async def get_image_preview(image_id: str):
    """Get image as PNG for browser preview."""
    if image_id not in image_store:
        raise HTTPException(status_code=404, detail="Image not found")
    
    img_data = image_store[image_id]
    img = Image.open(io.BytesIO(img_data["data"]))
    
    # Convert to RGB for PNG output
    if img.mode in ('CMYK', 'RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    
    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    
    return Response(content=output.read(), media_type="image/png")


# Serve static frontend files (must be last!)
app.mount("/", StaticFiles(directory="/app/app/static", html=True), name="static")
