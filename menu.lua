--[[
Copyright: Ren Tatsumoto
License: GNU GPL, version 3 or later; https://www.gnu.org/licenses/gpl-3.0.html
]]

local mp = require('mp')
local utils = require('mp.utils')
local H = require('helpers')
local OSD = require('osd_styler')

local base_keybindings = {
    {keys = {'ESC', 'q'}, fn = function(self) self:close() end},
    {keys = {'k', 'up'}, fn = function(self) self:change_menu_item(-1) end},
    {keys = {'j', 'down'}, fn = function(self) self:change_menu_item(1) end},
    {keys = {'h', 'left'}, fn = function(self) self:change_menu_item(1) end},
    {
        keys = {'h', 'left'},
        fn = function(self) self:change_selected_value(-1) end,
    },
    {
        keys = {'l', 'right'},
        fn = function(self) self:change_selected_value(1) end,
    },
    -- TODO: reset value key
}
local Menu = {
    choices = {},
    config = {},
    keybindings = {},
    hide_sections = {},
    active = false,
    selected = 1,
    overlay = mp.create_osd_overlay and mp.create_osd_overlay('ass-events'),
    base_keybindings = base_keybindings,
}

function Menu:new(o)
    o = o or {}
    setmetatable(o, self)
    self.__index = self
    return o
end

function Menu:make_osd()
    --local osd = OSD:new():size(config.menu_font_size):align(4) -- TODO
    local osd = OSD:new():size(24):align(4)
    local i = 1

    for _, section in ipairs(self.choices) do
        osd:newline():submenu(section[1]):newline()

        for _, option in ipairs(section[2]) do
            local name = option[1]
            local value = self.config[H:snake_case(name)]

            if self.selected == i then
                osd:tab():selected(name):arrow('　🡠 ')
                    :selected(value):arrow(' 🡢'):newline()
            else
                osd:tab():item(name):arrow('　🡠 '):text(value)
                    :arrow(' 🡢'):newline()
            end
            i = i + 1
        end
    end

    -- TODO: bindings section
    return osd
end

function Menu:update()
    if self.active == false then return end
    self.overlay.data = self:make_osd():get_text()
    self.overlay:update()
end

local function process_keybinds(keybinds, fn)
    for _, val in pairs(keybinds) do
        for _, key in pairs(val.keys) do
            fn(key, val.fn)
        end
    end
end

local function add_keybinds(keybinds, menu)
    process_keybinds(keybinds, function(key, fn)
        local flags = {repeatable = true}
        mp.add_forced_key_binding(key, key, function() fn(menu) end, flags)
    end)
end

local function remove_keybinds(keybinds, menu)
    process_keybinds(keybinds, function(key, fn) 
        mp.remove_key_binding(key)
    end)
end

function Menu:open()
    if self.overlay == nil then
        ver = mp.get_property("mpv-version")
        mp.osd_message("OSD overlay is not supported in " .. ver)
        return
    end

    if self.active == true then
        self:close()
        return
    end

    add_keybinds(self.base_keybindings, self)
    add_keybinds(self.keybindings, self)

    self.active = true
    self:update()
end

function Menu:close()
    if self.active == false then
        return
    end

    remove_keybinds(self.base_keybindings, self)
    remove_keybinds(self.keybindings, self)

    self.overlay:remove()
    self.active = false
end

function Menu:selectable_count()
    local count = 0
    local st = ""
    for _, section in ipairs(self.choices) do
        for _, option in ipairs(section[2]) do 
            count = count + 1
        end
    end
    return count
end

function Menu:change_menu_item(step)
    self.selected = H:cycle(self.selected, self:selectable_count(), step)
    self:update()
end

function Menu:change_selected_value(step)
    local i = 1

    for _, section in ipairs(self.choices) do
        for _, option in ipairs(section[2]) do
            if i == self.selected then
                local name = option[1]
                local value_now = self.config[H:snake_case(name)]
                local idx = H:index_of(option[2], value_now)
                local new_idx = H:cycle(idx, #option[2], step)
                self.config[H:snake_case(name)] = option[2][new_idx]
                self:on_config_changed()
            end
            i = i + 1
        end
    end

    self:update()
end

function Menu:on_config_changed()
    return nil
end

return Menu
