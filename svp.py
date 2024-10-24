import json
import os
from pathlib import Path
import vapoursynth as vs

src_fps = container_fps
if src_fps <= 0.1 or src_fps == 23.810:
    src_fps = 23.976
    
screen_fps = display_fps or 60
factor = 1
while src_fps * factor < screen_fps - 9:
    factor += 1
    
use_screen_fps = src_fps * factor > screen_fps

win_w, win_h = display_res
#win_w, win_h = user_data.split("/")
#win_w, win_h = int(win_w), int(win_h)

# SVP slider min (film, no artifact masking, to screen)
# super_params     = "{scale:{up:0},gpu:1,rc:true}"
# analyse_params = "{main:{search:{coarse:{distance:-8},type:2}}}"
# smoothfps_params = "{gpuid:11,gpu_qn:2,rate:{num:5,den:2},algo:13,scene:{}}"

# SVP slider max: same except for
# analyse_params = "{main:{search:{coarse:{distance:-8,bad:{sad:2000,range:24}},type:2}},refine:[{thsad:250}]}"

# https://www.svp-team.com/wiki/Manual:SVPflow
super_params = {
    "pel": 1,
    "gpu": 1,
    "full": False,
}
analyse_params = {
    "block": {"w": 32},
    "main": {
        "search": {
            "distance": 0,
            "coarse":{
                "distance":- 12,
                "bad": {"sad": 2000},
            },
        },
    },
    "refine": [{"thsad": 250}],
}
smoothfps_params = {
    "rate": {
        "num": screen_fps if use_screen_fps else factor,
        "den": 0,
        "abs": use_screen_fps,
    },
    "algo": 21,
    "gpuid": 0,
    "mask": {
        "cover": 80,
        "area": 0,  # SVP artifact masking: 0/50/100/200 (none/low/med/max)
        "area_sharp": 1,
    },
    "scene":{
        "mode":0,
    },
    "light": {
        "aspect": win_w / (win_h or 1),
        "lights": 10, 
        "border": 16,
        "length": 120,
        "cell": 1,
    },
}

core = vs.core
core.num_threads = (os.cpu_count() or 2) * 2
core.max_cache_size = 8192

basedir = Path(__file__).resolve().parent
if not hasattr(core,'svp1'):
    core.std.LoadPlugin(basedir / "svpflow1_vs.dll")
if not hasattr(core,'svp2'):
    core.std.LoadPlugin(basedir / "svpflow2_vs.dll")

highbit = video_in.format.bits_per_sample >= 10
if highbit and video_in_dw * video_in_dh * src_fps <= 3840 * 2160 * 30:
    input_um = video_in.resize.Point(format=vs.YUV420P10,dither_type="random")
    input_m = input_um
    input_m8 = input_m.resize.Point(format=vs.YUV420P8)
else:  # no 10 bit decoding
    input_um = video_in.resize.Point(format=vs.YUV420P8,dither_type="random")
    input_m = input_um
    input_m8 = input_m


super = core.svp1.Super(input_m8, json.dumps(super_params))
vectors = core.svp1.Analyse(
    super["clip"], super["data"], input_m8, json.dumps(analyse_params),
)
smooth = core.svp2.SmoothFps(
    input_m, super["clip"], super["data"], vectors["clip"], vectors["data"],
    json.dumps(smoothfps_params), src=input_um, fps=src_fps,
)
assume = core.std.AssumeFPS(
    smooth, fpsnum=smooth.fps_num, fpsden=smooth.fps_den,
)
assume.text.ClipInfo()
assume.set_output()
