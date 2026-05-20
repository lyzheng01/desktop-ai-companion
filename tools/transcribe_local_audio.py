import json
import sys
import wave
from pathlib import Path

from vosk import KaldiRecognizer, Model


REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / 'speech-models' / 'vosk-model-small-cn-0.22'


def normalize_transcribed_text(text: str) -> str:
    text = ' '.join(text.split())
    chars = []
    prev_is_cjk = False

    for ch in text:
        is_cjk = '\u4e00' <= ch <= '\u9fff'
        if ch == ' ' and prev_is_cjk:
            continue
        chars.append(ch)
        prev_is_cjk = is_cjk

    normalized = ''.join(chars)
    normalized = normalized.replace(' ，', '，').replace(' 。', '。').replace(' ？', '？').replace(' ！', '！')
    normalized = normalized.replace(' ：', '：').replace(' ；', '；').replace(' 、', '、')
    return normalized.strip()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('usage: python tools/transcribe_local_audio.py <wav-path>')

    wav_path = Path(sys.argv[1])
    if not wav_path.exists():
        raise SystemExit('audio file not found')
    if not MODEL_DIR.exists():
        raise SystemExit(f'model dir not found: {MODEL_DIR}')

    model = Model(str(MODEL_DIR))
    with wave.open(str(wav_path), 'rb') as wf:
        recognizer = KaldiRecognizer(model, wf.getframerate())
        recognizer.SetWords(False)

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            recognizer.AcceptWaveform(data)

        result = json.loads(recognizer.FinalResult())
        text = (result.get('text') or '').strip()
        sys.stdout.buffer.write(normalize_transcribed_text(text).encode('utf-8'))


if __name__ == '__main__':
    main()
