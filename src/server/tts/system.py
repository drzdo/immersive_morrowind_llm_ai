import os
import subprocess
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field
from util.logger import Logger

from tts.backend.abstract import AbstractTtsBackend, TtsBackendRequest
from tts.backend.elevenlabs import ElevenlabsTtsBackend
from tts.backend.dummy import DummyTtsBackend
from tts.file_list_rotation import FileListRotation
from tts.request import TtsRequest
from tts.response import TtsResponse
from util.colored_lines import green
from mutagen.mp3 import MP3

logger = Logger(__name__)

class TtsSystem:
    class Config(BaseModel):
        class Ffmpeg(BaseModel):
            path_to_ffmpeg_exe: str
            target_char_per_sec: int
            tempo_mul: Optional[float] = Field(default=None)

        class Dummy(BaseModel):
            type: Literal['dummy']

        class Elevenlabs(BaseModel):
            type: Literal['elevenlabs']
            elevenlabs: ElevenlabsTtsBackend.Config

        system: Union[Dummy, Elevenlabs] = Field(discriminator='type')
        output: FileListRotation.Config

        ffmpeg: Optional[Ffmpeg] = Field(default=None)
        sync_print_and_speak: bool = Field(default=False)

    def __init__(self, morrowind_data_files_dir: str, config: Config):
        self._config = config

        sound_output_dir = os.path.join(morrowind_data_files_dir, "Sound", "Vo")
        self._fsrotate = FileListRotation(config.output, sound_output_dir)

        self._backend = self._create_backend()

    async def convert(self, request: TtsRequest) -> TtsResponse | None:
        backend_response = await self._backend.convert(request=TtsBackendRequest(
            text=request.text,
            voice=request.voice,
            file_path=self._fsrotate.get_next_filepath()
        ))
        if backend_response is None:
            return None

        is_pitch_already_applied = False
        if self._config.ffmpeg:
            (path_before_ext, ext) = os.path.splitext(backend_response.file_path)
            file_path_tmp = f"{path_before_ext}_tmp{ext}"

            logger.debug(f"Handling '{request.text}'")
            pitch = request.voice.pitch
            tempo = 1.0 / pitch  # to keep same duration
            if self._config.ffmpeg.tempo_mul:
                tempo = tempo * self._config.ffmpeg.tempo_mul

            logger.debug(f"Initial pitch={pitch} tempo={tempo}")

            total_chars = len(request.text)
            audio_duration_sec = MP3(backend_response.file_path).info.length
            current_char_per_sec = total_chars / audio_duration_sec

            logger.debug(f"current_char_per_sec={current_char_per_sec}")
            if current_char_per_sec > 0 and current_char_per_sec < self._config.ffmpeg.target_char_per_sec:
                tempo_mul = float(self._config.ffmpeg.target_char_per_sec) / current_char_per_sec
                tempo = tempo * tempo_mul
                logger.debug(f"tempo_mul={tempo_mul}")

            # ffmpeg -i test.mp3 -af asetrate=44100*0.9,aresample=44100,atempo=1/0.9 output.mp3
            args = [
                self._config.ffmpeg.path_to_ffmpeg_exe,
                "-i",
                backend_response.file_path,
                "-filter:a",
                # f"atempo={tempo}",
                f"asetrate=44100*{pitch},aresample=44100,atempo={tempo}",
                # "-ar",
                # "44100",
                "-b:a",
                "64k",
                file_path_tmp,
                "-y"
            ]
            logger.debug(f"FFmpeg command: {args}")

            # subprocess.run(args)
            ffmpeg_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if ffmpeg_process.stdout:
                with ffmpeg_process.stdout:
                    for line in iter(ffmpeg_process.stdout.readline, b''):  # b'\n'-separated lines
                        logger.debug(line.strip())
            exitcode = ffmpeg_process.wait()

            os.unlink(backend_response.file_path)
            os.rename(file_path_tmp, backend_response.file_path)
            logger.debug(f"FFmpeg is exited with code {exitcode}")

            is_pitch_already_applied = True

        return TtsResponse(
            file_path=backend_response.file_path,
            is_pitch_already_applied=is_pitch_already_applied
        )

    def _create_backend(self) -> AbstractTtsBackend:
        system = self._config.system

        backend: AbstractTtsBackend
        if system.type == 'dummy':
            logger.info(f"Text-to-speech system is set to {green('dummy')}")
            backend = DummyTtsBackend()
        elif system.type == 'elevenlabs':
            logger.info(f"Text-to-speech system is set to {green('ElevenLabs')}")
            backend = ElevenlabsTtsBackend(system.elevenlabs)
        else:
            raise Exception(f"Unknown text-to-speech system '{system}'")

        return backend
