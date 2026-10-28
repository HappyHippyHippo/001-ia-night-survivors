-- Uniform grid spatial hash, rebuilt every frame, for enemy proximity queries.
local M = {}

local CELL = 64
local floor = math.floor
local cells = {}
local used = {}
local used_n = 0

local function key(cx, cy)
	return cx * 131072 + cy
end

function M.clear()
	for i = 1, used_n do
		local c = used[i]
		for j = #c, 1, -1 do c[j] = nil end
	end
	used_n = 0
end

function M.insert(obj)
	local k = key(floor(obj.x / CELL), floor(obj.y / CELL))
	local c = cells[k]
	if not c then
		c = {}
		cells[k] = c
	end
	if #c == 0 then
		used_n = used_n + 1
		used[used_n] = c
	end
	c[#c + 1] = obj
end

-- Fills `out` with candidates whose cell overlaps the circle's bounding box.
-- Returns the number of candidates (entries past that index are stale).
function M.query(x, y, r, out)
	local n = 0
	for cx = floor((x - r) / CELL), floor((x + r) / CELL) do
		for cy = floor((y - r) / CELL), floor((y + r) / CELL) do
			local c = cells[key(cx, cy)]
			if c then
				for i = 1, #c do
					n = n + 1
					out[n] = c[i]
				end
			end
		end
	end
	return n
end

function M.reset()
	cells = {}
	used = {}
	used_n = 0
end

return M
