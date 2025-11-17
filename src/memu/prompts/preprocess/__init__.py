from memu.prompts.preprocess import audio, conversation, document, image, video

PROMPTS: dict[str, str] = {
    "conversation": conversation.PROMPT.strip(),
    "video": video.PROMPT.strip(),
    "image": image.PROMPT.strip(),
    "document": document.PROMPT.strip(),
    "audio": audio.PROMPT.strip(),
}

__all__ = ["PROMPTS"]
