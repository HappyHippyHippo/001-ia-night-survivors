-- Volume settings (master / music / sfx), applied as sound group gains and persisted between sessions.
local M = {}

M.CHANNELS = {
	{ id = "master", name = "MASTER", group = hash("master") },
	{ id = "music", name = "MUSIC", group = hash("music") },
	{ id = "sfx", name = "SFX", group = hash("sfx") },
}
M.STEPS = 10

local SETTINGS_FILE = sys.get_save_file("night_survivors", "settings")

M.volume = { master = 1, music = 1, sfx = 1 }
M.muted = false

-- slider position -> group gain; squared so each step sounds roughly as loud as the last
local function gain(v) return v * v end

function M.apply()
	for _, ch in ipairs(M.CHANNELS) do
		local v = M.volume[ch.id]
		if ch.id == "master" and M.muted then v = 0 end
		sound.set_group_gain(ch.group, gain(v))
	end
end

function M.load()
	local ok, data = pcall(sys.load, SETTINGS_FILE)
	for _, ch in ipairs(M.CHANNELS) do
		local v = ok and data and tonumber(data[ch.id])
		if v then M.volume[ch.id] = math.max(0, math.min(1, v)) end
	end
	M.apply()
end

function M.save()
	pcall(sys.save, SETTINGS_FILE, M.volume)
end

-- set a channel to a slider step (0..STEPS)
function M.set_step(index, step)
	local ch = M.CHANNELS[index]
	step = math.max(0, math.min(M.STEPS, step))
	M.volume[ch.id] = step / M.STEPS
	M.apply()
	M.save()
end

function M.step(index)
	return math.floor(M.volume[M.CHANNELS[index].id] * M.STEPS + 0.5)
end

function M.toggle_mute()
	M.muted = not M.muted
	M.apply()
end

return M
