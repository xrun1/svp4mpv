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

def snake_case(name: str) -> str:
    return name.replace(" ", "_").lower()

basedir = Path(__file__).resolve().parent

if os.name == "nt":
    menu_json = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "svp_menu.json"
    config_json = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "svp_config.json"
else:
    menu_json = Path(os.environ["TMPDIR"] or "/tmp") / "svp_menu.json"
    config_json = Path(os.environ["TMPDIR"] or "/tmp") / "svp_config.json"

win_w, win_h = display_res
#win_w, win_h = user_data.split("/")
#win_w, win_h = int(win_w), int(win_h)

options = json.loads(config_json.read_text())
map = json.loads((basedir / "map.json").read_text())

raw = {}
for section, opts in map.items():
    for name, choices in opts.items():
        if (choice := options.get(snake_case(name))):
            deep_merge(choices[choice], raw)

if options["gpu_id"] != "Do not change":
    raw["smoothfps"]["gpuid"] = options["gpu_id"]

src_fps = container_fps
if src_fps <= 0.1 or src_fps == 23.810:
    src_fps = 23.976
    
fa = options["multiplicand"]
fb = options["multiplier"]
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
    if fb == "Auto":
        fb = "1"
    to_fps = screen_fps * float(fb)
else:
    if fb == "Auto":
        fb = "1"
    to_fps = float(fa.split(" FPS")[0]) * float(fb)
    
raw["smoothfps"].setdefault("rate", {}).update({
    "num": to_fps * 10_000,
    "den": 10_000,
    "abs": True,
})
raw["smoothfps"].setdefault("light", {})["aspect"] = win_w / (win_h or 1)
# TODO: light settings, NVOF, RIFE, 8/10bit options

deep_merge({
    "super": json.loads(options["json_super"] or "{}"),
    "analyse": json.loads(options["json_analyse"] or "{}"),
    "smoothfps": json.loads(options["json_smoothfps"] or "{}"),
}, raw)

menu_options = []
for section, stuff in map.items():
    if section == "Overrides":
        continue
    opts = [[opt, list(choices)] for opt, choices in stuff.items()]
    menu_options.append([section, opts])

menu_json.write_text(json.dumps(menu_options, indent=4))

core = vs.core
core.num_threads = ((os.cpu_count() or 2) * 2) - 1
core.max_cache_size = 8192

thread_opt = options["processing_threads"]
if thread_opt != "Do not change":
    core.num_threads += int(thread_opt)

if not hasattr(core,'svp1'):
    core.std.LoadPlugin(basedir / "svpflow1_vs.dll")
if not hasattr(core,'svp2'):
    core.std.LoadPlugin(basedir / "svpflow2_vs.dll")

if options["duplicate_frames_removal"] == "Remove every other frame":
    clip = video_in.std.SelectEvery(video_in,2,0).std.Trim(length=5000000)
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
