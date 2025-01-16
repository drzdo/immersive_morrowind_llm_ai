import datetime
from operator import itemgetter
import os
from typing import NamedTuple
from pathvalidate import sanitize_filename
from pydantic import BaseModel

from llm.message import LlmMessage


class ParsedLlmLog(NamedTuple):
    system_instructions: str
    messages: list[LlmMessage]
    user_text: str
    model_text: str

class LlmLogger:
    class Config(BaseModel):
        directory: str
        max_files: int

    def __init__(self, config: Config) -> None:
        self._config = config
        self._next_index = 0

        os.makedirs(self._config.directory, exist_ok=True)

    def log(
        self,
        *,
        system_instructions: str,
        history: list[LlmMessage],
        user_message: str,
        model_response: str,
        log_name: str | None,
        log_context: str | None
    ):
        now = datetime.datetime.now()
        filename = sanitize_filename(f"llm_{now.isoformat()}_{self._next_index}_{log_name}.log")
        self._next_index = self._next_index + 1

        filepath = os.path.join(self._config.directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            def write(s: str):
                f.write(s)
                f.write("\n")

            if log_context:
                write("=========== Context")
                write(log_context)

            write("\n\n=========== System instructions")
            write(system_instructions)
            write("----")

            write("\n\n=========== History")
            msg_index = 1
            for msg in history:
                write(f"---- Message {msg_index}. Role: {msg.role}")
                msg_index = msg_index + 1
                write(msg.text)
            write("----")

            write("\n\n=========== User message")
            write(user_message)
            write("----")

            write("\n\n=========== Model response")
            write(model_response)
            write("----")

        self._remove_extra_files()

    def _remove_extra_files(self):
        file_names = os.listdir(self._config.directory)

        file_name_to_mtime: dict[str, float] = {}
        for file_name in file_names:
            file_path = os.path.join(self._config.directory, file_name)
            file_name_to_mtime[file_name] = os.stat(file_path).st_mtime

        sorted_file_names = sorted(file_name_to_mtime.items(), key=itemgetter(1))

        delete = len(sorted_file_names) - self._config.max_files
        for x in range(0, delete):
            file_name = sorted_file_names[x][0]
            file_path = os.path.join(self._config.directory, file_name)
            os.remove(file_path)

    @staticmethod
    def parse(filepath: str) -> ParsedLlmLog:
        lines: list[str] = []
        with open(filepath, 'r', encoding='utf-8') as fd:
            lines = fd.readlines()
            lines = list(map(lambda l: l.strip(), lines))

        def find_line_index(s: str, starting_from: int, ignore_not_found: bool = False):
            index = starting_from
            while index < len(lines):
                line = lines[index]
                if line.startswith(s):
                    return index
                index = index + 1

            if ignore_not_found:
                return -1
            else:
                raise Exception(f"Cannot find line '{s}' starting from {starting_from}")

        sys_instructions_0 = find_line_index("=========== System instructions", 0)
        sys_instructions_1 = find_line_index("----", sys_instructions_0 + 1)

        messages_idx: list[int] = []
        last_message_i = -1

        next_index = sys_instructions_1 + 1
        while True:
            msg_i = find_line_index("---- Message", next_index, True)
            if msg_i >= 0:
                messages_idx.append(msg_i)
                next_index = msg_i + 1
            else:
                last_message_i = find_line_index("----", next_index)
                break

        user_msg_0 = find_line_index("=========== User message", last_message_i)
        user_msg_1 = find_line_index("----", user_msg_0)

        model_msg_0 = find_line_index("=========== Model response", user_msg_1)
        model_msg_1 = find_line_index("----", model_msg_0)

        def join_lines(start: int, end: int):
            return "\n".join(lines[start:end+1])

        system_instructions = join_lines(sys_instructions_0 + 1, sys_instructions_1 - 1)

        messages: list[LlmMessage] = []
        for i in range(0, len(messages_idx)):
            message_line_header_index = messages_idx[i]
            m_0 = message_line_header_index + 1
            m_1 = (messages_idx[i + 1] - 1) if (i < (len(messages_idx) - 1)) else (last_message_i - 1)
            is_role_user = 'Role: user' in lines[message_line_header_index]
            text = join_lines(m_0, m_1)
            messages.append(LlmMessage(role='user' if is_role_user else 'model', text=text))

        user_message = join_lines(user_msg_0+1, user_msg_1-1)
        model_message = join_lines(model_msg_0+1, model_msg_1-1)

        return ParsedLlmLog(
            system_instructions=system_instructions,
            user_text=user_message,
            model_text=model_message,
            messages=messages
        )
