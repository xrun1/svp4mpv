local timer = nil
local stopped = false

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
end

local function start()
    stopped = false
    update()
end

local function toggle()
    if stopped then start() else stop() end    
end

mp.add_hook('on_preloaded', 50, schedule_update)
mp.observe_property("vo-configured", "native", schedule_update)
mp.observe_property("display-fps", "native", schedule_update)
mp.observe_property("osd-width", "native", schedule_update)
mp.observe_property("osd-height", "native", schedule_update)

mp.add_key_binding("Alt+S", toggle)
