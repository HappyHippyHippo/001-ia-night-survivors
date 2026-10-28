-- Weapon and passive item definitions, and level-up choice rolling.
local M = {}

M.WEAPONS = {
	bolt = {
		name = "MAGIC BOLT", icon = "icon_bolt",
		desc = { "SHOOTS THE NEAREST ENEMY", "+1 BOLT", "+6 DAMAGE", "+1 BOLT, FASTER RATE", "BOLTS PIERCE +1", "+1 BOLT, +10 DAMAGE" },
		levels = {
			{ cd = 1.0, dmg = 10, count = 1, speed = 380, pierce = 1 },
			{ cd = 1.15, dmg = 10, count = 2, speed = 380, pierce = 1 },
			{ cd = 1.15, dmg = 16, count = 2, speed = 380, pierce = 1 },
			{ cd = 0.95, dmg = 16, count = 3, speed = 400, pierce = 1 },
			{ cd = 0.95, dmg = 16, count = 3, speed = 400, pierce = 2 },
			{ cd = 0.85, dmg = 26, count = 4, speed = 420, pierce = 2 },
		},
	},
	knife = {
		name = "THROWING KNIFE", icon = "icon_knife",
		desc = { "THROWN WHERE YOU FACE", "+1 KNIFE", "+5 DAMAGE", "+1 KNIFE, PIERCE +1", "+1 KNIFE, FASTER RATE", "+1 KNIFE, +8 DAMAGE" },
		levels = {
			{ cd = 0.85, dmg = 8,  count = 1, speed = 620, pierce = 1 },
			{ cd = 0.85, dmg = 8,  count = 2, speed = 620, pierce = 1 },
			{ cd = 0.85, dmg = 13, count = 2, speed = 620, pierce = 1 },
			{ cd = 0.85, dmg = 13, count = 3, speed = 640, pierce = 2 },
			{ cd = 0.65, dmg = 13, count = 4, speed = 660, pierce = 2 },
			{ cd = 0.65, dmg = 21, count = 5, speed = 680, pierce = 3 },
		},
	},
	aura = {
		name = "GARLIC AURA", icon = "icon_aura",
		desc = { "HURTS ENEMIES CLOSE BY", "+20% AREA", "+3 DAMAGE", "+20% AREA, FASTER", "+4 DAMAGE", "+25% AREA, +5 DAMAGE" },
		levels = {
			{ radius = 58,  dmg = 5,  tick = 0.75 },
			{ radius = 70,  dmg = 5,  tick = 0.75 },
			{ radius = 70,  dmg = 8,  tick = 0.75 },
			{ radius = 84,  dmg = 8,  tick = 0.6 },
			{ radius = 84,  dmg = 12, tick = 0.6 },
			{ radius = 105, dmg = 17, tick = 0.55 },
		},
	},
	orb = {
		name = "HOLY ORBS", icon = "icon_orb",
		desc = { "ORBS CIRCLE AROUND YOU", "+1 ORB", "+6 DAMAGE, WIDER", "+1 ORB, FASTER SPIN", "+1 ORB", "+1 ORB, +10 DAMAGE" },
		levels = {
			{ count = 2, dist = 72,  spin = 3.0, dmg = 10 },
			{ count = 3, dist = 72,  spin = 3.0, dmg = 10 },
			{ count = 3, dist = 88,  spin = 3.0, dmg = 16 },
			{ count = 4, dist = 88,  spin = 3.8, dmg = 16 },
			{ count = 5, dist = 92,  spin = 3.8, dmg = 16 },
			{ count = 6, dist = 100, spin = 4.2, dmg = 26 },
		},
	},
	lightning = {
		name = "THUNDER", icon = "icon_lightning",
		desc = { "SMITES RANDOM ENEMIES", "+1 STRIKE", "+15 DAMAGE", "+1 STRIKE, BIGGER BLAST", "FASTER RATE", "+2 STRIKES, +20 DAMAGE" },
		levels = {
			{ cd = 3.0, dmg = 25, count = 2, aoe = 40 },
			{ cd = 3.0, dmg = 25, count = 3, aoe = 40 },
			{ cd = 3.0, dmg = 40, count = 3, aoe = 40 },
			{ cd = 3.0, dmg = 40, count = 4, aoe = 56 },
			{ cd = 2.2, dmg = 40, count = 4, aoe = 56 },
			{ cd = 2.2, dmg = 60, count = 6, aoe = 60 },
		},
	},
}
M.WEAPON_ORDER = { "bolt", "knife", "aura", "orb", "lightning" }

M.PASSIVES = {
	might    = { name = "POWER RING",  icon = "icon_might",    desc = "+12% DAMAGE",          max = 5 },
	armor    = { name = "IRON PLATE",  icon = "icon_armor",    desc = "-1 DAMAGE TAKEN",      max = 5 },
	heart    = { name = "HEART GEM",   icon = "icon_heart",    desc = "+20 MAX HEALTH",       max = 5 },
	speed    = { name = "SWIFT BOOTS", icon = "icon_speed",    desc = "+10% MOVE SPEED",      max = 5 },
	cooldown = { name = "HOURGLASS",   icon = "icon_cooldown", desc = "-8% WEAPON COOLDOWN",  max = 5 },
	magnet   = { name = "LODESTONE",   icon = "icon_magnet",   desc = "+40% PICKUP RANGE",    max = 5 },
	regen    = { name = "LIFE HERB",   icon = "icon_regen",    desc = "+0.4 HEALTH PER SEC",  max = 5 },
}
M.PASSIVE_ORDER = { "might", "armor", "heart", "speed", "cooldown", "magnet", "regen" }

M.MAX_WEAPONS = 5
M.MAX_PASSIVES = 6

local function weapon_level(s, id)
	for _, w in ipairs(s.weapons) do
		if w.id == id then return w.level end
	end
	return 0
end

-- Returns up to 3 choices: { kind, id, name, desc, icon, tag }
function M.roll(s)
	local pool = {}
	for _, id in ipairs(M.WEAPON_ORDER) do
		local def = M.WEAPONS[id]
		local lv = weapon_level(s, id)
		if lv < #def.levels and (lv > 0 or #s.weapons < M.MAX_WEAPONS) then
			pool[#pool + 1] = { kind = "weapon", id = id, name = def.name, icon = def.icon,
				desc = def.desc[lv + 1], tag = lv == 0 and "NEW!" or ("LV " .. (lv + 1)), weight = lv == 0 and 1.0 or 1.3 }
		end
	end
	local owned_passives = 0
	for _, lv in pairs(s.passives) do
		if lv > 0 then owned_passives = owned_passives + 1 end
	end
	for _, id in ipairs(M.PASSIVE_ORDER) do
		local def = M.PASSIVES[id]
		local lv = s.passives[id] or 0
		if lv < def.max and (lv > 0 or owned_passives < M.MAX_PASSIVES) then
			pool[#pool + 1] = { kind = "passive", id = id, name = def.name, icon = def.icon, desc = def.desc,
				tag = lv == 0 and "NEW!" or ("LV " .. (lv + 1)), weight = 0.8 }
		end
	end

	local choices = {}
	while #choices < 3 and #pool > 0 do
		local total = 0
		for _, c in ipairs(pool) do total = total + c.weight end
		local r = math.random() * total
		for i, c in ipairs(pool) do
			r = r - c.weight
			if r <= 0 or i == #pool then
				c.weight = nil
				choices[#choices + 1] = c
				table.remove(pool, i)
				break
			end
		end
	end
	if #choices == 0 then
		choices[1] = { kind = "heal", id = "heal", name = "ROAST CHICKEN", icon = "icon_chicken", desc = "RESTORE 50 HEALTH", tag = "" }
	end
	return choices
end

function M.apply(s, choice)
	if choice.kind == "weapon" then
		for _, w in ipairs(s.weapons) do
			if w.id == choice.id then
				w.level = w.level + 1
				return
			end
		end
		s.weapons[#s.weapons + 1] = { id = choice.id, level = 1, timer = 0.2 }
	elseif choice.kind == "passive" then
		s.passives[choice.id] = (s.passives[choice.id] or 0) + 1
		if choice.id == "heart" then
			s.player.hp = s.player.hp + 20
		end
	elseif choice.kind == "heal" then
		s.player.hp = math.min(s.stats.max_hp, s.player.hp + 50)
	end
end

-- Derived player stats from passives
function M.compute_stats(s, base)
	local p = s.passives
	return {
		might = 1 + 0.12 * (p.might or 0),
		armor = p.armor or 0,
		max_hp = base.max_hp + 20 * (p.heart or 0),
		speed = base.speed * (1 + 0.1 * (p.speed or 0)),
		cooldown = 1 - 0.08 * (p.cooldown or 0),
		magnet = base.magnet * (1 + 0.4 * (p.magnet or 0)),
		regen = 0.4 * (p.regen or 0),
	}
end

-- Inventory summary for the HUD
function M.inventory(s)
	local list = {}
	for _, w in ipairs(s.weapons) do
		list[#list + 1] = { icon = M.WEAPONS[w.id].icon, level = w.level, kind = "weapon" }
	end
	for _, id in ipairs(M.PASSIVE_ORDER) do
		local lv = s.passives[id] or 0
		if lv > 0 then
			list[#list + 1] = { icon = M.PASSIVES[id].icon, level = lv, kind = "passive" }
		end
	end
	return list
end

return M
