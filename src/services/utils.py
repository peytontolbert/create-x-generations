import requests
import time
from pathlib import Path
import logging
from moviepy import AudioFileClip, ColorClip, VideoFileClip, CompositeVideoClip, VideoClip
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

CUTOFF_DATE = datetime.fromisoformat('2025-01-29T00:00:00+00:00')

def is_after_cutoff(timestamp_str: str) -> bool:
    """Check if a timestamp is after the cutoff date"""
    try:
        # Convert timestamp string to datetime object
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return timestamp >= CUTOFF_DATE
    except Exception:
        return False

async def download_media(url: str) -> str:
    """Download media (image, video, or audio) and return local path."""
    try:
        # Create temp directory if it doesn't exist
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid URL: {url}")
            return None

        # Determine file extension from content type
        response = requests.head(url, timeout=10)
        content_type = response.headers.get('content-type', '').lower()
        
        # Map content types to extensions
        extension_map = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/webm': '.webm',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
            'audio/ogg': '.ogg'
        }

        # Get extension from content type or fallback to appropriate default
        if 'video' in content_type:
            extension = extension_map.get(content_type, '.mp4')
            is_audio = False
        elif 'audio' in content_type:
            extension = extension_map.get(content_type, '.mp3')
            is_audio = True
        elif 'image' in content_type:
            extension = extension_map.get(content_type, '.jpg')
            is_audio = False
        else:
            logger.error(f"Unsupported content type: {content_type}")
            return None

        # Generate temporary file paths
        temp_download_path = temp_dir / f"temp_download_{int(time.time())}{extension}"
        
        # For audio conversion, use mp4 extension
        if 'audio' in content_type:
            temp_download_path = temp_dir / f"temp_download_{int(time.time())}.mp4"

        # Download media
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        if is_audio:
            # Save audio to temporary file first
            temp_audio_path = temp_dir / f"temp_audio_{int(time.time())}.mp3"
            with open(temp_audio_path, "wb") as f:
                f.write(response.content)

            logger.info("Converting audio to video with black screen...")
            try:
                # Load the audio file
                audio = AudioFileClip(str(temp_audio_path))
                
                # Create a black screen video clip
                black_screen = ColorClip(
                    size=(1280, 720),
                    color=(0, 0, 0),
                    duration=audio.duration
                ).with_audio(audio)  # Attach audio this way
                
                # Write the final video
                black_screen.write_videofile(
                    str(temp_download_path),  # Use the same path format as other media
                    codec='libx264',
                    audio_codec='aac',
                    fps=24
                )
                
                # Clean up
                audio.close()
                black_screen.close()
                
                # Remove temporary audio file
                if temp_audio_path.exists():
                    temp_audio_path.unlink()
                
                logger.info(f"Audio converted to video: {temp_download_path}")
                return str(temp_download_path)

            except Exception as e:
                logger.error(f"Error converting audio to video: {e}")
                return None
        else:
            # Save downloaded media directly
            with open(temp_download_path, "wb") as f:
                f.write(response.content)
            return str(temp_download_path)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading media: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None