"""Video processing utilities for frame extraction."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """Extract frames from video files using ffmpeg."""
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if ffmpeg is available in the system."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def extract_middle_frame(video_path: str, output_path: str | None = None) -> str:
        """
        Extract the middle frame from a video file.
        
        Args:
            video_path: Path to the video file
            output_path: Optional output path for the frame. If None, creates a temp file.
            
        Returns:
            Path to the extracted frame image
            
        Raises:
            RuntimeError: If ffmpeg is not available or extraction fails
        """
        if not VideoFrameExtractor.is_ffmpeg_available():
            msg = "ffmpeg is not available. Please install ffmpeg to process videos."
            raise RuntimeError(msg)
        
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            msg = f"Video file not found: {video_path}"
            raise FileNotFoundError(msg)
        
        # Create output path if not provided
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".jpg")
        
        try:
            # Get video duration
            duration_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]
            
            logger.debug(f"Getting video duration: {' '.join(duration_cmd)}")
            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            
            duration = float(duration_result.stdout.strip())
            middle_time = duration / 2
            
            logger.debug(f"Video duration: {duration}s, extracting frame at {middle_time}s")
            
            # Extract frame at middle timestamp
            extract_cmd = [
                "ffmpeg",
                "-ss", str(middle_time),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",  # High quality
                "-y",  # Overwrite output file
                str(output_path),
            ]
            
            logger.debug(f"Extracting frame: {' '.join(extract_cmd)}")
            subprocess.run(
                extract_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            
            if not Path(output_path).exists():
                msg = f"Frame extraction failed: output file not created at {output_path}"
                raise RuntimeError(msg)
            
            logger.info(f"Successfully extracted frame to: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            msg = f"ffmpeg/ffprobe failed: {e.stderr}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "Video processing timed out"
            logger.error(msg)
            raise RuntimeError(msg) from e
    
    @staticmethod
    def extract_multiple_frames(
        video_path: str,
        num_frames: int = 3,
        output_dir: str | None = None,
    ) -> list[str]:
        """
        Extract multiple evenly-spaced frames from a video.
        
        Args:
            video_path: Path to the video file
            num_frames: Number of frames to extract
            output_dir: Optional output directory. If None, creates a temp directory.
            
        Returns:
            List of paths to extracted frame images
            
        Raises:
            RuntimeError: If ffmpeg is not available or extraction fails
        """
        if not VideoFrameExtractor.is_ffmpeg_available():
            msg = "ffmpeg is not available. Please install ffmpeg to process videos."
            raise RuntimeError(msg)
        
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            msg = f"Video file not found: {video_path}"
            raise FileNotFoundError(msg)
        
        # Create output directory if not provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get video duration
            duration_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]
            
            logger.debug(f"Getting video duration: {' '.join(duration_cmd)}")
            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            
            duration = float(duration_result.stdout.strip())
            
            # Calculate timestamps for evenly-spaced frames
            timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
            
            logger.debug(f"Video duration: {duration}s, extracting frames at: {timestamps}")
            
            frame_paths = []
            for idx, timestamp in enumerate(timestamps):
                output_path = output_dir_obj / f"frame_{idx:03d}.jpg"
                
                # Extract frame at timestamp
                extract_cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-q:v", "2",  # High quality
                    "-y",  # Overwrite output file
                    str(output_path),
                ]
                
                logger.debug(f"Extracting frame {idx+1}/{num_frames}: {' '.join(extract_cmd)}")
                subprocess.run(
                    extract_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                
                if not output_path.exists():
                    msg = f"Frame extraction failed: output file not created at {output_path}"
                    raise RuntimeError(msg)
                
                frame_paths.append(str(output_path))
            
            logger.info(f"Successfully extracted {len(frame_paths)} frames to: {output_dir}")
            return frame_paths
            
        except subprocess.CalledProcessError as e:
            msg = f"ffmpeg/ffprobe failed: {e.stderr}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "Video processing timed out"
            logger.error(msg)
            raise RuntimeError(msg) from e

