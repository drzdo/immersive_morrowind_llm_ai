from typing import NamedTuple


class _Line(NamedTuple):
    sentences: list[str]


class _Paragraph(NamedTuple):
    lines: list[_Line]


class PromptBuilder:
    def __init__(self) -> None:
        self._paragraphs: list[_Paragraph] = []
        self._next_option_index = 1
        self._next_suboption_index = 1

    def paragraph(self):
        self._paragraphs.append(_Paragraph([]))

    def line(self, s: str = ""):
        if len(self._paragraphs) == 0:
            self.paragraph()

        self._paragraphs[-1].lines.append(_Line([s]))

    def sentence(self, s: str):
        if len(self._paragraphs) == 0:
            self.paragraph()

        if len(self._paragraphs[-1].lines) == 0:
            self._paragraphs[-1].lines.append(_Line([]))

        self._paragraphs[-1].lines[-1].sentences.append(s)

    def clear(self):
        self._paragraphs = []
        self._next_option_index = 1
        self._next_suboption_index = 1

    def reset_option_index(self):
        self._next_option_index = 1
        self._next_suboption_index = 1

    def get_option_index_and_inc(self):
        v = self._next_option_index

        self._next_option_index = self._next_option_index + 1
        self._next_suboption_index = 1

        return v

    def get_suboption_index_and_inc(self):
        v = self._next_suboption_index
        self._next_suboption_index = self._next_suboption_index + 1
        return v

    def __str__(self) -> str:
        all_lines: list[str] = []

        for paragraph in self._paragraphs:
            if len(all_lines) > 0 and len(all_lines[-1]) > 0:
                all_lines.append("")

            for line in paragraph.lines:
                final_sentences: list[str] = []

                for sentence in line.sentences:
                    sentence = sentence.strip()

                    if len(sentence) > 0:
                        if sentence[-1] not in [",", ".", "?", "!", ":", "-", ""]:
                            sentence = sentence + "."

                        final_sentences.append(sentence)

                final_line = " ".join(final_sentences)
                final_line = final_line.strip()
                if len(final_line) > 0:
                    all_lines.append(final_line)

        result = "\n".join(all_lines)
        return result
