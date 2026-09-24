# svp4mpv

An mpv script for Windows that provides [SVP](https://www.svp-team.com/)
frame interpolation without having to use the official GUI.
Comes with a menu for direct control:

![Screenshot](./screenshot.jpg)

SVP converts any video to 60+ FPS in real time as you watch it, with GPU
acceleration supported. It can also fill black bars with lights when
the monitor's aspect ratio and the video's differ.

This script makes use of the last SVPFlow DLL versions that could
be extracted from the demo and used without requiring the GUI to be running.
The *LICENSE.txt* in this repository does not cover the files in the
*third_party* directory.

Not implemented:
- Basic performance-quality slider (from looking at the original GUI's
  generated scripts, most levels changed absolutely nothing)
- RIFE AI interpolation (too slow and complicated for little gained)
- Automatic cropping of baked-in black bars
  (try [dynamic-crop.lua](https://github.com/Ashyni/mpv-scripts))
- Phoning home


## Installation

Git clone or click **Code** → **Download ZIP** and then extract into your mpv
scripts folder (usually *%APPDATA%\mpv\scripts* or *~/.config/mpv/scripts*).

Your mpv build must support VapourSynth. If you're using a
[shinchiro build](https://sourceforge.net/projects/mpv-player-windows/files/release/)
or [mpv.net](https://github.com/mpvnet-player/mpv.net), this should be the case.
The correct version of VapourSynth for your mpv must also be available in PATH.

As of September 2026, these combinations are confirmed to work:

- **mpv 0.41** or **mpv.net v7.1.2.0** with **VapourSynth R72**
- **mpv 0.37** or **mpv.net v7.1.1.0** with **VapourSynth R54**

VapourSynth and its dependencies can be set up using the
corresponding *Install-Portable-VapourSynth-Rxx.bat* from the
[release page](https://github.com/vapoursynth/vapoursynth/release)
(R72 direct link [here](https://github.com/vapoursynth/vapoursynth/releases/download/R72/Install-Portable-VapourSynth-R72.bat)).
A *vapoursynth-portable* folder is created where you run the script.
To add it to PATH quickly, paste the following in PowerShell
(replace `C:\vapoursynth-portable` with the actual created folder's path):

```powershell
[Environment]::SetEnvironmentVariable("Path", "C:\vapoursynth-portable" + ";" + [Environment]::GetEnvironmentVariable("Path","User"),"User")
```

If using hardware-accelerated video playback in mpv, the `-copy` version of
the decoder must be used, e.g. `hwdec=d3d11va-copy` instead of `hwdec=d3d11va`.


## Usage

- Press Alt+Shift+S to open the menu
- Press Enter to toggle interpolation on or off
- Navigate options with the arrow keys or HJKL, reset selected with R
- Press A to apply changes immediately
- Changes are forgotten when mpv is closed unless you press S, then a
  file will be created in mpv's script-opts folder to remember your choices.
- Press Escape or Q to close the menu.

More details about the options can be found on the
[SVP wiki](https://www.svp-team.com/wiki/Manual:FRC#Manual_Options_Selection).
If you're in a hurry, try the settings from the above screenshot for maximum
smoothness (the `*` indicates non-default settings).
For options in the "Rendering" and "Motion vectors" sections, the choices
are ordered from least (left) to most (right) CPU cost.


## Framerate Options

The default multiplicand/multiplier settings pair try to be smart,
for example: if you play a 24 FPS video on a 75hz screen, the script will
multiply the framerate by exactly 3x to reach 72 FPS, as integer multipliers
tend to give better results and 72 is right under 75.

However, if the screen is 60hz instead, then the multiplier will be 2.5 to
reach exactly 60 FPS, since forcing 72 would cause stutter from dropped frames
and the smoothness gained from 60 FPS in my opinion outweighs the benefits of
using a 2x integer multiplier and getting only 48 FPS.

Most 60hz monitors can be easily overclocked to at least 72hz,
which will make a noticeable difference for SVP.

If you have multiple monitors with different framerates, you may need to
use mpv in full screen to avoid dropped frames.

Also note that if mpv is moved to another monitor, or the monitor's refresh
rate is changed while mpv is open, mpv may stay stick with the old value,
causing interpolation to target the wrong framerate.
On laptops, beware of automatic changes on AC un/plugging
(this can usually be disabled in your graphic chip's control panel).


## Performance Issues

The menu displays a dropped frames/second estimation
(averaged over the last 4 seconds) on the bottom, which
should stay at/near 0 for smooth playback.

For weak hardware, the mpv rendering options can make a large difference.
Hardware acceleration might actually degrade performance, e.g. with
old Intel HD chips. Baseline settings to try:

```ini
vo=gpu-next
libplacebo-opts=preset=fast
hwdec=no
```

GPU acceleration and 10bit decoding in the SVP menu are important too.
After that, the Motion Vectors section make the most difference.
For animated content, using a larger motion vectors grid value (e.g. 24px)
is essentially a free performance and quality increase.
