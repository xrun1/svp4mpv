local H = require('helpers')
local Menu = require('menu')

local timer = nil
local stopped = false
local menu = nil

local menu_json = (os.getenv("TMPDIR") or "/tmp") .. "/svp_menu.json"
local config_json = (os.getenv("TMPDIR") or "/tmp") .. "/svp_config.json"
if H:on_windows() then
    menu_json = os.getenv("LOCALAPPDATA") .. "\\Temp\\svp_menu.json"
    config_json = os.getenv("LOCALAPPDATA") .. "\\Temp\\svp_config.json"
end

local config = {
    multiplicand = "Video FPS",
    multiplier = "Auto (respect vsync)",
    frame_interpolation_mode = "Adaptive",
    adaptive_pattern = "Uniform - 1m - 1.5m",
    svp_shader = "13. Standard",
    artifacts_masking = "Average",
    motion_vectors_precision = "Half pixel",
    motion_vectors_grid = "12 px. Average 2",
    decrease_grid_step = "Disabled",
    search_radius = "Average",
    wide_search = "Average",
    width_of_top_coarse_level = "Large",
    use_nvidia_optical_flow = "Don't use",
    processing_of_scene_changes = "Repeat frame",
    duplicate_frames_removal = "Do not remove",
    gpu_acceleration = "Allow",
    gpu_id = "Do not change",
    processing_threads = "Do not change",
    json_super = "",
    json_analyse = "",
    json_smoothfps = "",
}
local defaults = H:shallow_copy(config)
require "mp.options".read_options(config)

local function update()
    if stopped then return end

    --local user_data =
    --    ':user-data="' ..
    --    mp.get_property("osd-width") .. "/" ..
    --    mp.get_property("osd-height") ..
    --    '"'
    local user_data = ""  -- FIXME: not available before mpv 0.39

    local vpy = mp.command_native({"expand-path", "~~home/scripts/svp/svp.py"})
    local filter = '@svp:vapoursynth="' .. vpy ..
        '":buffered-frames=4:concurrent-frames=23' .. user_data
    --mp.osd_message(filter)

    mp.commandv("vf", "remove", "@svp")
    mp.commandv("vf", "add", filter)
    stopped = false
end

local function schedule_update()
    if timer then timer:stop() end
    timer = mp.add_timeout(0.25, update)
end

local function stop()
    stopped = true
    mp.commandv("vf", "remove", "@svp")
    mp.osd_message("SVP Off")
end

local function start()
    stopped = false
    update()
    mp.osd_message("SVP On")
end

local function toggle()
    if stopped then start() else stop() end    
end

local function save()
    local data = ""
    for key, value in pairs(config) do
        data = data .. key .. "=" .. value .. "\n"
    end
    f = H:write_file(H:exp("~~home/script-opts/svp.conf"), data)    
end

H:write_json(config_json, config)
mp.add_hook('on_preloaded', 50, schedule_update)
mp.observe_property("vo-configured", "native", schedule_update)
mp.observe_property("display-fps", "native", schedule_update)
mp.observe_property("osd-width", "native", schedule_update)
mp.observe_property("osd-height", "native", schedule_update)

mp.add_key_binding("Alt+S", function()
    if menu == nil then
        menu = Menu:new({
            choices = H:read_json(menu_json),
            config = config,
            defaults = defaults,
            keybindings = {
                {
                    keys = {"SPACE"}, 
                    fn = function(self) toggle(); self:close() end
                },
                {
                    keys = {"s", "ctrl+s"},
                    fn = function(self) save(); self:close() end
                },
            }
        })
        menu.on_config_changed = function()
            H:write_json(config_json, config)
            schedule_update()
        end
    end
    menu:open()
end)
