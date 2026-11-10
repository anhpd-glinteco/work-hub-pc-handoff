"""Generate Vietnamese preset narration using the isolated local VieNeu CPU install."""
import argparse
import os
import time
from pathlib import Path
os.environ.setdefault('HF_HOME', 'D:/Codex/downloads/work-hub/huggingface')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--voice', help='Built-in preset name; omitted selects the first available preset')
    args = p.parse_args()
    if not args.text.strip(): p.error('Text must not be empty')
    if args.output.exists(): p.error('Output exists; choose a new path')
    from vieneu import Vieneu
    import soundfile as sf
    started = time.monotonic()
    tts = Vieneu(backend='onnx', precision='fp32')
    presets = tts.list_preset_voices()
    if not presets: raise RuntimeError('No preset voices available')
    voice = args.voice or presets[0][1]
    if voice not in [v[1] for v in presets]: raise ValueError('Unknown preset voice')
    audio = tts.infer(args.text, voice=voice)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tts.save(audio, str(args.output))
    info = sf.info(str(args.output))
    assert info.frames > 0 and info.samplerate > 0, 'Invalid generated audio'
    print(f'voice={voice}, duration={info.duration:.2f}s, elapsed={time.monotonic()-started:.2f}s, output={args.output}')

if __name__ == '__main__': main()

