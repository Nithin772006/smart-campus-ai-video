import subprocess
from pathlib import Path

srt_path = Path("generated/subtitles/osi_model/subtitles.srt").resolve().as_posix().replace(":", r"\:")
vf = f"subtitles='{srt_path}':original_size=1280x720:force_style='Alignment=2,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=40,MarginL=80,MarginR=80'"

cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=0x0f172a:s=1280x720:d=10",
    "-vf", vf,
    "-ss", "00:00:05",
    "-vframes", "1",
    "scratch/sub_test_clean.png"
]
subprocess.run(cmd, check=True)
print("Rendered scratch/sub_test_clean.png successfully")
