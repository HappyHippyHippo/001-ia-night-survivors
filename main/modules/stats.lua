-- Formats run statistics for the pause/stats and end screens.
local U = require "main.modules.upgrades"
local C = require "main.modules.config"

local M = {}

local function pct(v) return string.format("%+d%%", math.floor(v * 100 + 0.5)) end

function M.fmt_time(t)
	t = math.floor(t)
	return string.format("%02d:%02d", math.floor(t / 60), t % 60)
end

function M.fmt_num(v)
	v = math.floor(v + 0.5)
	if v >= 10000 then return string.format("%dK", math.floor(v / 1000)) end
	return tostring(v)
end

-- { label, value } rows describing the player's current build
function M.player_rows(s)
	local st = s.stats
	return {
		{ "MAX HEALTH", tostring(st.max_hp) },
		{ "RECOVERY", string.format("%.1f/S", st.regen) },
		{ "ARMOR", tostring(st.armor) },
		{ "MOVE SPEED", pct(st.speed / C.PLAYER.speed - 1) },
		{ "MIGHT", pct(st.might - 1) },
		{ "AREA", pct(st.area - 1) },
		{ "COOLDOWN", pct(st.cooldown - 1) },
		{ "AMOUNT", "+" .. st.amount },
		{ "MAGNET", pct(st.magnet / C.PLAYER.magnet - 1) },
		{ "CRIT CHANCE", math.floor(st.crit * 100 + 0.5) .. "%" },
		{ "GROWTH", pct(st.growth - 1) },
		{ "REROLLS", tostring(s.rerolls) },
		{ "SKIPS", tostring(s.skips) },
	}
end

-- end-of-run summary rows
function M.run_rows(s, records)
	local nr = s.new_records or {}
	return {
		{ "SURVIVED", M.fmt_time(s.time) .. (nr.time and " NEW!" or "") },
		{ "LEVEL", s.level .. (nr.level and " NEW!" or "") },
		{ "ENEMIES SLAIN", s.kills .. (nr.kills and " NEW!" or "") },
		{ "DAMAGE TAKEN", M.fmt_num(s.damage_taken) },
		{ "HEALTH HEALED", M.fmt_num(s.healed) },
		{ "CHESTS OPENED", tostring(s.chests) },
		{ "EVOLUTIONS", tostring(s.evolutions) },
		{ "", "" },
		{ "BEST TIME", M.fmt_time(records.best_time) },
		{ "BEST LEVEL", tostring(records.best_level) },
		{ "BEST KILLS", tostring(records.best_kills) },
		{ "RUNS / WINS", records.runs .. " / " .. records.wins },
	}
end

-- "evolved" | "ready" (max level + item: open a chest) | "owned" (has the item) | "need"
function M.evo_state(s, w)
	local def = U.WEAPONS[w.id]
	if w.evolved then return "evolved" end
	local has_item = (s.passives[def.evo.partner] or 0) > 0
	if has_item and w.level >= #def.levels then return "ready" end
	return has_item and "owned" or "need"
end

-- per-weapon performance, sorted by damage dealt
function M.weapon_rows(s)
	local rows = {}
	for _, w in ipairs(s.weapons) do
		local def = U.WEAPONS[w.id]
		local dmg = s.dmg_by[w.id] or 0
		local owned = math.max(1, s.time - (w.since or 0))
		rows[#rows + 1] = {
			icon = def.icon,
			name = w.evolved and def.evo.name or def.name,
			level = w.evolved and "EVO" or ("LV " .. w.level),
			line = string.format("DMG %s  DPS %s  KO %s", M.fmt_num(dmg), M.fmt_num(dmg / owned), M.fmt_num(s.kills_by[w.id] or 0)),
			evo_icon = U.PASSIVES[def.evo.partner].icon,
			evo_state = M.evo_state(s, w),
			evolved = w.evolved,
			dmg = dmg,
		}
	end
	table.sort(rows, function(a, b) return a.dmg > b.dmg end)
	return rows
end

return M
