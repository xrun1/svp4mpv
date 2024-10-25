local mp = require('mp')
local utils = require('mp.utils')
local Helpers = {}

function Helpers:exp(path)
    return mp.command_native({"expand-path", path})
end

function Helpers:path_sep()
    return package.config:sub(1, 1)
end

function Helpers:on_windows()
    return Helpers:path_sep() == "\\"
end

function Helpers:index_of(array, key) 
    for i, key2 in ipairs(array) do
        if key2 == key then
            return i
        end
    end
end

function Helpers:cycle(current, max, step)
    current = current + step
    if current < 1 then
        return max
    elseif current > max then
        return 1
    else
        return current
    end
end

function Helpers:snake_case(name)
    return name:gsub(" ", "_"):lower()
end

function Helpers:read_json(path)
    local f = assert(io.open(Helpers:exp(path), "r"))
    local data = f:read("*all")
    f:close()
    return assert(utils.parse_json(data))
end

function Helpers:write_json(path, table)
    local f = assert(io.open(Helpers:exp(path), "w"))
    f:write(assert(utils.format_json(table)))
    f:close()
end

return Helpers
