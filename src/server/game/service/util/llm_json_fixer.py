from pydantic import BaseModel
from llm.session import LlmSession

class LlmJsonFixer:
    def __init__(self, llm_session: LlmSession) -> None:
        self._llm_session = llm_session

    async def fix_json[T: BaseModel](self, type: type[T], json_format: str, response: str) -> T:
        if "```" in response:
            response = response.replace("```", "")

        try:
            return type.model_validate(response)
        except:
            self._llm_session.reset(
                system_instructions=f"""Твоя задача - исправить JSON так, чтобы он соответствовал указанному формату.
    Невнимательный программист допустил ошибку при форматировании JSON, и теперь он не валиден.
    Возможно, понадобится что-то переименовать или добавить, чтобы превести JSON к правильному формату. Сделай это.

    А вот желаемый формат JSON:
    {json_format}

    Твой вывод должен быть без лишних слов, просто исправленный JSON. Пример:

    ```json
    И тут исправленный JSON
    ```
    """,
                messages=[]
            )
            response_fixed = await self._llm_session.send_message(
                user_text=f"""Вот JSON, который составил невнимательный программист:

                {response}"""
            )
            if "```" in response_fixed:
                response_fixed = response_fixed.replace("```", "")
            return type.model_validate(response_fixed)
