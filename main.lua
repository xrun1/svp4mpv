local H = require('helpers')
local Menu = require('third_party.menu')
local utils = require('mp.utils')

local first_start = true
local first_start_timer = nil
local timer = nil
local stopped = true
local menu = nil
local original_hr_seek = mp.get_property("hr-seek-framedrop", "yes")

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
    fill_with_light = "Enabled",
    lights_count = "16",
    flare_length = "100",
    flare_width = "1.0",
    border = "12",
    processing_of_scene_changes = "Repeat frame",
    duplicate_frames_removal = "Do not remove",
    gpu_acceleration = "Disable",
    gpu_id = "Default (use first available)",
    native_10bit_decoding = "Never allow",
    processing_threads = "Do not change",
    json_super = "",
    json_analyse = "",
    json_smoothfps = "",
}
local defaults = H:shallow_copy(config)
require "mp.options".read_options(config, "svp")

local function remove_filter()
    if string.find(mp.get_property("vf"), "@svp") then
        mp.commandv("vf", "remove", "@svp")
    end
end

local function update()
    if stopped then return end

    local filter =
        '@svp:vapoursynth="' .. mp.get_script_directory() .. '/svp.py"' ..
        ':buffered-frames=4:concurrent-frames=23'

    remove_filter()
    mp.set_property("hr-seek-framedrop", "no")  -- Avoid desyncs on seek
    mp.commandv("vf", "add", filter)
    stopped = false
end

local function schedule_update()
    if timer then timer:stop() end
    timer = mp.add_timeout(0.25, update)
end

local function new_file_print_state()
    if stopped then return end
    mp.osd_message("SVP On")
end

local function stop(silent)
    stopped = true
    remove_filter()
    if not silent then mp.osd_message("SVP Off") end

    if original_hr_seek then
        mp.set_property("hr-seek-framedrop", original_hr_seek)
    end
end

local function start(silent)
    stopped = false
    update()
    if not silent then mp.osd_message("SVP On") end
end

local function toggle()
    if stopped then start() else stop() end
    if menu then
        menu:close()
        menu.stopped = stopped
        menu:open()
    end
end

local function apply()
    if stopped then
        start()
    else
        update()
        mp.osd_message("Applied")
    end
end

local function save()
    local data = ""
    for key, value in pairs(config) do
        data = data .. key .. "=" .. value .. "\n"
    end
    local path = H:exp("~~home/script-opts/svp.conf")
    local f = H:write_file(path, data)
    mp.osd_message("Saved options to " .. path)
end

local function show_menu()
    if menu == nil then
        menu = Menu:new({
            stopped = stopped,
            choices = H:read_json(menu_json),
            config = config,
            defaults = defaults,
            keybindings = {
                {
                    keys = {"ENTER", "KP_ENTER"},
                    fn = function(self) toggle() end
                },
                {
                    keys = {"a"},
                    fn = function(self) apply() end
                },
                {
                    keys = {"s", "ctrl+s"},
                    fn = function(self) save() end
                },
            }
        })
        menu.on_config_changed = function()
            H:write_json(config_json, config)
        end
    end
    menu.stopped = stopped
    menu:open()
end

H:write_json(config_json, config)
mp.add_hook('on_preloaded', 50, schedule_update)
mp.add_hook('on_preloaded', 49, new_file_print_state)
mp.observe_property("vo-configured", "native", schedule_update)
mp.observe_property("display-fps", "native", schedule_update)
mp.observe_property("osd-width", "native", schedule_update)
mp.observe_property("osd-height", "native", schedule_update)

mp.add_key_binding("Alt+S", "svp-menu", function()
    if first_start then
        os.remove(menu_json)  -- remove any menu from old script version
        start(true)  -- svp.py will run the logic to prepare the menu only
        first_start_timer = mp.add_periodic_timer(0.02, function()
            if not H:path_exists(menu_json) then return end
            first_start_timer:stop()
            stop(true)
            first_start = false
            show_menu()
        end)
    else
        show_menu()
    end
end)
