import json
import os
from pathlib import Path
import vapoursynth as vs
from contextlib import suppress

def deep_merge(source: dict, destination: dict) -> dict:
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

basedir = Path(__file__).resolve().parent

win_w, win_h = display_res
#win_w, win_h = user_data.split("/")
#win_w, win_h = int(win_w), int(win_h)

options = json.loads((basedir / "base_options.json").read_text())
map = json.loads((basedir / "equivalences.json").read_text())
user = {}
with suppress(FileNotFoundError):
    user = json.loads((basedir / "user_options.json").read_text())

deep_merge(user, options)
raw = {}
for section, stuff in options.items():
    if section != "Overrides":
        for key, value in stuff.items():
            deep_merge(map[section][key].get(value, value), raw)

gpu_id_opt = options["Miscellaneous"]["GPU ID"]
if gpu_id_opt != "Do not change":
    raw["smoothfps"]["gpuid"] = gpu_id_opt

src_fps = container_fps
if src_fps <= 0.1 or src_fps == 23.810:
    src_fps = 23.976
    
fa = options["Target FPS"]["Multiplicand"]
fb = options["Target FPS"]["Multiplier"]
to_fps = src_fps
screen_fps = display_fps or 60

if fa == "Video FPS":
    if fb == "Auto":
        factor = 1
        while src_fps * factor < screen_fps - 9:
            factor += 1

        to_fps = src_fps * factor
    else:
        to_fps = src_fps * float(fb)
elif fa == "Screen FPS":
    to_fps = screen_fps * float(fb)
else:
    to_fps = float(fa.split(" FPS")[0]) * float(fb)
    
raw["smoothfps"].setdefault("rate", {}).update({
    "num": to_fps * 10_000,
    "den": 10_000,
    "abs": True,
})
raw["smoothfps"].setdefault("light", {})["aspect"] = win_w / (win_h or 1)
# TODO: light settings, NVOF, RIFE, 8/10bit options

deep_merge(options["Overrides"], raw)

core = vs.core
core.num_threads = ((os.cpu_count() or 2) * 2) - 1
core.max_cache_size = 8192

thread_opt = options["Miscellaneous"]["Processing threads"]
if thread_opt != "Do not change":
    core.num_threads += int(thread_opt)

if not hasattr(core,'svp1'):
    core.std.LoadPlugin(basedir / "svpflow1_vs.dll")
if not hasattr(core,'svp2'):
    core.std.LoadPlugin(basedir / "svpflow2_vs.dll")

if options["Miscellaneous"]["Duplicate frames removal"]:
    clip = core.std.SelectEvery(video_in,2,0).std.Trim(length=5000000)
else:
    clip = video_in.std.Trim(length=5000000)

highbit = clip.format.bits_per_sample >= 10
if highbit and video_in_dw * video_in_dh * src_fps <= 3840 * 2160 * 30:
    input_um = clip.resize.Point(format=vs.YUV420P10,dither_type="random")
    input_m = input_um
    input_m8 = input_m.resize.Point(format=vs.YUV420P8)
else:  # no 10 bit decoding
    input_um = clip.resize.Point(format=vs.YUV420P8,dither_type="random")
    input_m = input_um
    input_m8 = input_m


super = core.svp1.Super(input_m8, json.dumps(raw["super"]))
vectors = core.svp1.Analyse(
    super["clip"], super["data"], input_m8, json.dumps(raw["analyse"]),
)
smooth = core.svp2.SmoothFps(
    input_m, super["clip"], super["data"], vectors["clip"], vectors["data"],
    json.dumps(raw["smoothfps"]), src=input_um, fps=src_fps,
)
assume = core.std.AssumeFPS(
    smooth, fpsnum=smooth.fps_num, fpsden=smooth.fps_den,
)
assume.text.ClipInfo()
assume.set_output()
