import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import vapoursynth as vs

core = vs.core

# Variables defined by mpv at runtime
if TYPE_CHECKING:
    video_in = vs.VideoNode()
    video_in_dw = 1920
    video_in_dh = 1080
    container_fps = 24.0
    display_res = (1920, 1080)
    display_fps = 60.0

if container_fps <= 0.1 or round(container_fps, 2) == 23.81:
    container_fps = 23.976

win_w, win_h = display_res

# Folders
base_dir = Path(__file__).resolve().parent
tmp_dir = Path(os.environ.get("TMPDIR") or "/tmp")
if os.name == "nt":
    tmp_dir = Path(os.environ["LOCALAPPDATA"]) / "Temp"

# {option_name: value} written from parent main.lua, based on script_opts file
user_cfg: dict[str, str] = \
    json.loads((tmp_dir / "svp_config.json").read_text())

# Menu Category > Option Name > Possible Choice > SVPFlow options dict
cfg2svparams: dict[str, dict[str, dict[str, dict[str, Any]]]] = \
    json.loads((base_dir / "map.json").read_text())


def deep_merge(source: dict[Any, Any], destination: dict[Any, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value


def write_menu_entries() -> bool:
    path = tmp_dir / "svp_menu.json"
    if path.exists():
        return False

    # [(categoryName, [(optionName, [value, ...]), ...]), ...]
    menu: list[tuple[str, list[tuple[str, list[str]]]]] = []
    for section, stuff in cfg2svparams.items():
        if section == "Overrides":
            continue
        opts = [(opt, list(choices)) for opt, choices in stuff.items()]
        menu.append((section, opts))

    (tmp_dir / "svp_menu.json").write_text(json.dumps(menu, indent=4), "utf-8")
    return True


def get_svparams_fps() -> dict[str, Any]:
    base = user_cfg["multiplicand"]
    times = user_cfg["multiplier"]
    screen_fps = display_fps or 60.0
    to_fps = container_fps

    if base == "Video FPS":
        if str(times).startswith("Auto"):
            factor = 1
            while container_fps * factor < screen_fps - 9:
                factor += 1

            to_fps = container_fps * factor
            if times == "Auto (respect vsync)":
                to_fps = min(to_fps, screen_fps)
        else:
            to_fps = container_fps * float(times)
    elif base == "Screen Hz":
        if str(times).startswith("Auto"):
            times = "1"
        to_fps = screen_fps * float(times)
    else:
        if str(times).startswith("Auto"):
            times = "1"
        to_fps = float(base.split(" FPS")[0]) * float(times)

    return {
        "num": to_fps * 10_000,
        "den": 10_000,
        "abs": True,
    }


def get_svparams() -> dict[str, dict[str, Any]]:
    p = {}

    def snake_case(name: str) -> str:
        return name.replace(" ", "_").lower()

    for _section, opts in cfg2svparams.items():  # noqa: PERF102
        for name, choices in opts.items():
            if (choice := user_cfg.get(snake_case(name))):
                deep_merge(choices[choice], p)

    p["smoothfps"].setdefault("rate", {}).update(get_svparams_fps())

    if user_cfg["fill_with_light"] == "Disabled":
        p["smoothfps"]["light"] = {"lights": 2, "length": 0, "aspect": 1.7778}

    p["smoothfps"].setdefault("light", {})["aspect"] = win_w / (win_h or 1)

    deep_merge({
        "super": json.loads(user_cfg["json_super"] or "{}"),
        "analyse": json.loads(user_cfg["json_analyse"] or "{}"),
        "smoothfps": json.loads(user_cfg["json_smoothfps"] or "{}"),
    }, p)

    return p


def prepare_vapoursynth() -> None:
    core.num_threads = ((os.cpu_count() or 2) * 2) - 1
    core.max_cache_size = 8192

    thread_opt = user_cfg["processing_threads"]
    if thread_opt != "Do not change":
        core.num_threads = max(1, core.num_threads - int(thread_opt))

    if not hasattr(core, "svp1"):
        core.std.LoadPlugin(base_dir / "third_party" / "svpflow1_vs.dll")
    if not hasattr(core, "svp2"):
        core.std.LoadPlugin(base_dir / "third_party" / "svpflow2_vs.dll")


def get_inputs(clip: vs.VideoNode) -> tuple[vs.VideoNode, ...]:
    hidepth = clip.format.bits_per_sample >= 10
    allow = user_cfg["native_10bit_decoding"]
    pixel_rate = video_in_dw * video_in_dh * container_fps

    if hidepth and user_cfg["gpu_acceleration"] != "Disable" and (
        allow == "Always allow" or
        (allow == "Allow under 4k30" and pixel_rate <= 3840 * 2160 * 30)
    ):
        um = clip.resize.Point(format=vs.YUV420P10, dither_type="random")
        m = um
        m8 = m.resize.Point(format=vs.YUV420P8)
    else:
        um = clip.resize.Point(format=vs.YUV420P8, dither_type="random")
        m = um
        m8 = m

    return um, m, m8


def crop(clip: vs.VideoNode, smooth: vs.VideoNode) -> vs.VideoNode:
    if user_cfg["fill_with_light"] == "Disabled":
        delta_w = smooth.width - clip.width
        delta_h = smooth.height - clip.height
        if delta_w or delta_h:
            left = delta_w // 2
            right = delta_w - left
            top = delta_h // 2
            bottom = delta_h - top
            return core.std.Crop(
                smooth, left=left, right=right, top=top, bottom=bottom,
            )
    return smooth


def interpolate(clip: vs.VideoNode) -> vs.VideoNode:
    prepare_vapoursynth()

    clip = video_in
    if user_cfg["duplicate_frames_removal"] == "Remove every other frame":
        clip = clip.std.SelectEvery(cycle=2, offsets=0)
    clip = clip.std.Trim(length=5_000_000)
    input_um, input_m, input_m8 = get_inputs(clip)

    svparams = get_svparams()
    sup = core.svp1.Super(input_m8, json.dumps(svparams["super"]))
    vectors = core.svp1.Analyse(
        sup["clip"], sup["data"], input_m8, json.dumps(svparams["analyse"]),
    )
    smooth = crop(clip, core.svp2.SmoothFps(
        input_m, sup["clip"], sup["data"], vectors["clip"], vectors["data"],
        json.dumps(svparams["smoothfps"]), src=input_um, fps=container_fps,
    ))
    assume = core.std.AssumeFPS(
        smooth, fpsnum=smooth.fps_num, fpsden=smooth.fps_den,
    )
    assume.text.ClipInfo()
    return assume


if write_menu_entries():
    video_in.set_output()
else:
    interpolate(video_in).set_output()
