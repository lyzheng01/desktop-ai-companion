import json
import sys
import wave
from pathlib import Path

from vosk import KaldiRecognizer, Model


REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / 'speech-models' / 'vosk-model-small-cn-0.22'


def normalize_transcribed_text(text: str) -> str:
    normalized = ' '.join(text.split()).strip()
    # Vosk 中文短句常把词之间打空格，这里先做最保守的清洗：
    # 直接去掉中间空格，优先保证聊天输入像正常中文。
    normalized = normalized.replace(' ', '')
    normalized = normalized.replace(' ，', '，').replace(' 。', '。')
    normalized = normalized.replace(' ？', '？').replace(' ！', '！')
    normalized = normalized.replace(' ：', '：').replace(' ；', '；')
    normalized = normalized.replace(' 、', '、')
    return normalized.strip()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('usage: python tools/transcribe_local_audio.py <wav-path> [model-dir]')

    wav_path = Path(sys.argv[1])
    model_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else MODEL_DIR
    if not wav_path.exists():
        raise SystemExit('audio file not found')
    if not model_dir.exists():
        raise SystemExit(f'model dir not found: {model_dir}')

    model = Model(str(model_dir))
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
