"""Video processing utilities for frame extraction."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """Extract frames from video files using ffmpeg."""

    FFMPEG_BINARIES: ClassVar[set[str]] = {"ffmpeg", "ffprobe"}

    @classmethod
    def is_ffmpeg_available(cls) -> bool:
        """Check if ffmpeg is available in the system."""
        try:
            result = cls._run_ffmpeg_command(["ffmpeg", "-version"], timeout=5, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            return False
        else:
            return result.returncode == 0

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

        video_path_obj = VideoFrameExtractor._resolve_existing_path(video_path, description="Video file")
        safe_video_path = str(video_path_obj)

        # Create output path if not provided
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                output_path = tmp_file.name
        output_path_obj = VideoFrameExtractor._resolve_output_path(output_path)
        safe_output_path = str(output_path_obj)

        try:
            # Get video duration
            duration_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                safe_video_path,
            ]

            logger.debug(f"Getting video duration: {' '.join(duration_cmd)}")
            duration_result = VideoFrameExtractor._run_ffmpeg_command(duration_cmd, timeout=30)

            duration = float(duration_result.stdout.strip())
            middle_time = duration / 2

            logger.debug(f"Video duration: {duration}s, extracting frame at {middle_time}s")

            # Extract frame at middle timestamp
            extract_cmd = [
                "ffmpeg",
                "-ss",
                str(middle_time),
                "-i",
                safe_video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",  # High quality
                "-y",  # Overwrite output file
                safe_output_path,
            ]

            logger.debug(f"Extracting frame: {' '.join(extract_cmd)}")
            VideoFrameExtractor._run_ffmpeg_command(extract_cmd, timeout=30)

            if not output_path_obj.exists():
                msg = f"Frame extraction failed: output file not created at {output_path_obj}"
                raise RuntimeError(msg)
            else:
                logger.info(f"Successfully extracted frame to: {output_path_obj}")
                return str(output_path_obj)

        except subprocess.CalledProcessError as e:
            msg = f"ffmpeg/ffprobe failed: {e.stderr}"
            logger.exception(msg)
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "Video processing timed out"
            logger.exception(msg)
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

        video_path_obj = VideoFrameExtractor._resolve_existing_path(video_path, description="Video file")
        safe_video_path = str(video_path_obj)

        # Create output directory if not provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        output_dir_obj = VideoFrameExtractor._ensure_safe_cli_path(Path(output_dir))
        output_dir_obj.mkdir(parents=True, exist_ok=True)

        try:
            # Get video duration
            duration_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                safe_video_path,
            ]

            logger.debug(f"Getting video duration: {' '.join(duration_cmd)}")
            duration_result = VideoFrameExtractor._run_ffmpeg_command(duration_cmd, timeout=30)

            duration = float(duration_result.stdout.strip())

            # Calculate timestamps for evenly-spaced frames
            timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]

            logger.debug(f"Video duration: {duration}s, extracting frames at: {timestamps}")

            frame_paths = []
            for idx, timestamp in enumerate(timestamps):
                output_path_obj = VideoFrameExtractor._resolve_output_path(str(output_dir_obj / f"frame_{idx:03d}.jpg"))

                # Extract frame at timestamp
                extract_cmd = [
                    "ffmpeg",
                    "-ss",
                    str(timestamp),
                    "-i",
                    safe_video_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",  # High quality
                    "-y",  # Overwrite output file
                    str(output_path_obj),
                ]

                logger.debug(f"Extracting frame {idx + 1}/{num_frames}: {' '.join(extract_cmd)}")
                VideoFrameExtractor._run_ffmpeg_command(extract_cmd, timeout=30)

                if not output_path_obj.exists():
                    msg = f"Frame extraction failed: output file not created at {output_path_obj}"
                    raise RuntimeError(msg)

                frame_paths.append(str(output_path_obj))

            logger.info(f"Successfully extracted {len(frame_paths)} frames to: {output_dir_obj}")
        except subprocess.CalledProcessError as e:
            msg = f"ffmpeg/ffprobe failed: {e.stderr}"
            logger.exception(msg)
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "Video processing timed out"
            logger.exception(msg)
            raise RuntimeError(msg) from e
        else:
            return frame_paths

    @staticmethod
    def _ensure_safe_cli_path(path_obj: Path) -> Path:
        """Ensure the given path is safe to pass to a CLI command."""
        resolved = path_obj.resolve()
        if resolved.name.startswith("-"):
            msg = f"Unsafe path for CLI execution: {resolved}"
            raise ValueError(msg)
        return resolved

    @classmethod
    def _resolve_existing_path(cls, path: str, *, description: str) -> Path:
        """Resolve and validate an existing filesystem path."""
        path_obj = Path(path)
        if not path_obj.exists():
            msg = f"{description} not found: {path}"
            raise FileNotFoundError(msg)
        return cls._ensure_safe_cli_path(path_obj)

    @classmethod
    def _resolve_output_path(cls, path: str) -> Path:
        """Resolve output paths (which may not yet exist) for CLI safety."""
        return cls._ensure_safe_cli_path(Path(path))

    @classmethod
    def _run_ffmpeg_command(
        cls,
        cmd: list[str],
        *,
        timeout: int,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run an ffmpeg/ffprobe command after validating the executable."""
        if not cmd:
            msg = "FFmpeg command cannot be empty."
            raise ValueError(msg)
        executable = cmd[0]
        binary_name = Path(executable).name
        if binary_name not in cls.FFMPEG_BINARIES:
            msg = f"Unsupported executable '{executable}'"
            raise ValueError(msg)
        safe_cmd = [executable, *[str(arg) for arg in cmd[1:]]]
        return subprocess.run(  # noqa: S603
            safe_cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=check,
        )
