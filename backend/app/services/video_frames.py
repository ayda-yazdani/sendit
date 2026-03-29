import asyncio
import base64
import re
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.media import MediaFrame


FRAME_COUNT = 8
FRAME_OUTPUT_WIDTH = 540
FRAME_OUTPUT_HEIGHT = 960


@dataclass(frozen=True)
class StoryboardLevel:
    level: int
    width: int
    height: int
    frame_count: int
    columns: int
    rows: int
    interval_ms: int
    name_template: str
    signature: str


class VideoFrameService:
    async def extract_frames(
        self,
        *,
        video_url: str | None,
        duration: str | None,
        storyboard_spec: str | None = None,
        frame_count: int = FRAME_COUNT,
    ) -> list[str]:
        captures = await asyncio.to_thread(
            self._extract_frames_sync,
            video_url=video_url,
            duration=duration,
            storyboard_spec=storyboard_spec,
            frame_count=frame_count,
        )
        return [capture.image_url for capture in captures]

    async def extract_frame_captures(
        self,
        *,
        video_url: str | None,
        duration: str | None,
        storyboard_spec: str | None = None,
        frame_count: int = FRAME_COUNT,
    ) -> list[MediaFrame]:
        return await asyncio.to_thread(
            self._extract_frames_sync,
            video_url=video_url,
            duration=duration,
            storyboard_spec=storyboard_spec,
            frame_count=frame_count,
        )

    def _extract_frames_sync(
        self,
        *,
        video_url: str | None,
        duration: str | None,
        storyboard_spec: str | None,
        frame_count: int,
    ) -> list[MediaFrame]:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            return []

        seconds = self._parse_iso8601_duration(duration)
        if video_url:
            if seconds is None:
                seconds = self._probe_duration_seconds(video_url)
            if seconds and seconds > 0:
                frames = self._extract_video_frames(
                    ffmpeg=ffmpeg,
                    video_url=video_url,
                    seconds=seconds,
                    frame_count=frame_count,
                )
                if frames:
                    return frames

        if storyboard_spec:
            return self._extract_storyboard_frames(
                ffmpeg=ffmpeg,
                storyboard_spec=storyboard_spec,
                frame_count=frame_count,
            )

        return []

    def _extract_video_frames(
        self,
        *,
        ffmpeg: str,
        video_url: str,
        seconds: float,
        frame_count: int,
    ) -> list[MediaFrame]:
        frames: list[MediaFrame] = []
        for timestamp in self._build_timestamps(seconds, frame_count):
            command = [
                ffmpeg,
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                video_url,
                "-vf",
                f"scale={FRAME_OUTPUT_WIDTH}:{FRAME_OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={FRAME_OUTPUT_WIDTH}:{FRAME_OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "-q:v",
                "2",
                "-",
            ]
            image = self._run_binary_command(command)
            if image:
                frames.append(
                    MediaFrame(
                        image_url=self._as_data_url(image),
                        timestamp_seconds=round(timestamp, 3),
                        timestamp_text=self._format_timestamp(timestamp),
                    )
                )
        return frames

    def _extract_storyboard_frames(
        self,
        *,
        ffmpeg: str,
        storyboard_spec: str,
        frame_count: int,
    ) -> list[MediaFrame]:
        base_url, levels = self._parse_storyboard_spec(storyboard_spec)
        if not base_url or not levels:
            return []

        level = levels[-1]
        indices = self._build_frame_indices(level.frame_count, frame_count)
        frames: list[MediaFrame] = []
        for frame_index in indices:
            sheet_url = self._build_storyboard_sheet_url(base_url, level, frame_index)
            if not sheet_url:
                continue
            tile_index = frame_index % (level.columns * level.rows)
            x = (tile_index % level.columns) * level.width
            y = (tile_index // level.columns) * level.height
            timestamp = self._storyboard_timestamp_seconds(level, frame_index)
            command = [
                ffmpeg,
                "-loglevel",
                "error",
                "-i",
                sheet_url,
                "-vf",
                f"crop={level.width}:{level.height}:{x}:{y},"
                f"scale={FRAME_OUTPUT_WIDTH}:{FRAME_OUTPUT_HEIGHT}:flags=lanczos",
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "-q:v",
                "2",
                "-",
            ]
            image = self._run_binary_command(command)
            if image:
                frames.append(
                    MediaFrame(
                        image_url=self._as_data_url(image),
                        timestamp_seconds=round(timestamp, 3),
                        timestamp_text=self._format_timestamp(timestamp),
                    )
                )
        return frames

    def _probe_duration_seconds(self, video_url: str) -> float | None:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            return None
        command = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_url,
        ]
        output = self._run_text_command(command)
        if not output:
            return None
        try:
            seconds = float(output.strip())
        except ValueError:
            return None
        return seconds if seconds > 0 else None

    def _build_timestamps(self, seconds: float, frame_count: int) -> list[float]:
        segment = seconds / frame_count
        return [min(seconds, segment * (index + 0.5)) for index in range(frame_count)]

    def _build_frame_indices(self, total_frames: int, frame_count: int) -> list[int]:
        if total_frames <= 0:
            return []
        if total_frames == 1:
            return [0] * frame_count
        return [
            min(total_frames - 1, round(index * (total_frames - 1) / (frame_count - 1)))
            for index in range(frame_count)
        ]

    def _storyboard_timestamp_seconds(
        self, level: StoryboardLevel, frame_index: int
    ) -> float:
        if level.interval_ms <= 0:
            return float(frame_index)
        return (frame_index * level.interval_ms) / 1000

    def _parse_storyboard_spec(
        self, storyboard_spec: str
    ) -> tuple[str | None, list[StoryboardLevel]]:
        parts = storyboard_spec.split("|")
        if not parts:
            return None, []
        base_url = parts[0]
        levels: list[StoryboardLevel] = []
        for index, part in enumerate(parts[1:]):
            fields = part.split("#")
            if len(fields) < 8:
                continue
            try:
                levels.append(
                    StoryboardLevel(
                        level=index,
                        width=int(fields[0]),
                        height=int(fields[1]),
                        frame_count=int(fields[2]),
                        columns=int(fields[3]),
                        rows=int(fields[4]),
                        interval_ms=int(fields[5]),
                        name_template=fields[6],
                        signature=fields[7].removeprefix("rs$"),
                    )
                )
            except ValueError:
                continue
        return base_url, levels

    def _build_storyboard_sheet_url(
        self,
        base_url: str,
        level: StoryboardLevel,
        frame_index: int,
    ) -> str | None:
        sheet_capacity = level.columns * level.rows
        if sheet_capacity <= 0:
            return None
        sheet_index = frame_index // sheet_capacity
        sheet_name = level.name_template.replace("$M", str(sheet_index))
        url = (
            base_url.replace("$L", str(level.level)).replace("$N", sheet_name)
        )
        return self._with_query_param(url, "rs", level.signature) if level.signature else url

    def _with_query_param(self, url: str, key: str, value: str) -> str:
        split = urlsplit(url)
        params = dict(parse_qsl(split.query, keep_blank_values=True))
        params[key] = value
        return urlunsplit(
            (split.scheme, split.netloc, split.path, urlencode(params), split.fragment)
        )

    def _parse_iso8601_duration(self, value: str | None) -> float | None:
        if not value:
            return None
        match = re.fullmatch(
            r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?",
            value,
        )
        if not match:
            return None
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        total = (hours * 3600) + (minutes * 60) + seconds
        return total if total > 0 else None

    def _run_binary_command(self, command: list[str]) -> bytes | None:
        try:
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return completed.stdout or None

    def _run_text_command(self, command: list[str]) -> str | None:
        try:
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return completed.stdout or None

    def _as_data_url(self, image: bytes) -> str:
        encoded = base64.b64encode(image).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def _format_timestamp(self, seconds: float) -> str:
        whole_seconds = max(0, int(round(seconds)))
        minutes, secs = divmod(whole_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
