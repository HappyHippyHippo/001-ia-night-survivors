-- Weapon and passive item definitions, evolutions, level-up rolls and the
-- before/after stat previews shown on level-up cards.
local M = {}

M.WEAPONS = {
	bolt = {
		name = "MAGIC BOLT", icon = "icon_bolt",
		desc = { "SHOOTS THE NEAREST ENEMY", "+1 BOLT", "+6 DAMAGE", "+1 BOLT, FASTER RATE", "BOLTS PIERCE +1", "+1 BOLT, +10 DAMAGE" },
		levels = {
			{ cd = 1.0,  dmg = 10, count = 1, speed = 380, pierce = 1 },
			{ cd = 1.0,  dmg = 10, count = 2, speed = 380, pierce = 1 },
			{ cd = 1.0,  dmg = 16, count = 2, speed = 380, pierce = 1 },
			{ cd = 0.85, dmg = 16, count = 3, speed = 400, pierce = 1 },
			{ cd = 0.85, dmg = 16, count = 3, speed = 400, pierce = 2 },
			{ cd = 0.75, dmg = 26, count = 4, speed = 420, pierce = 2 },
		},
		evo = { name = "ARCANE STORM", partner = "cooldown", desc = "AN ENDLESS STREAM OF BOLTS",
			stats = { cd = 0.22, dmg = 28, count = 2, speed = 480, pierce = 3 }, tint = { 1, 0.5, 1 } },
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
		evo = { name = "THOUSAND EDGES", partner = "speed", desc = "A RELENTLESS HAIL OF STEEL",
			stats = { cd = 0.09, dmg = 20, count = 1, speed = 760, pierce = 4 }, tint = { 1, 0.85, 0.3 } },
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
		evo = { name = "SOUL EATER", partner = "heart", desc = "DRAINS LIFE FROM THE HORDE",
			stats = { radius = 130, dmg = 24, tick = 0.45, heal = 0.4 }, tint = { 1, 0.45, 0.55 } },
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
		evo = { name = "SUN HALO", partner = "might", desc = "A BLAZING RING OF SUNS",
			stats = { count = 9, dist = 120, spin = 4.6, dmg = 42 }, tint = { 1, 0.6, 0.3 } },
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
		evo = { name = "STORM LORD", partner = "magnet", desc = "THE SKY ITSELF FIGHTS FOR YOU",
			stats = { cd = 1.2, dmg = 85, count = 8, aoe = 75 }, tint = { 1, 0.9, 0.4 } },
	},
	water = {
		name = "HOLY WATER", icon = "icon_water",
		desc = { "LEAVES PUDDLES THAT BURN", "+1 FLASK", "+20% AREA, +4 DAMAGE", "+1 FLASK, LASTS LONGER", "+4 DAMAGE", "+1 FLASK, +20% AREA" },
		levels = {
			{ cd = 4.5, dmg = 8,  count = 1, radius = 40, duration = 2.5 },
			{ cd = 4.5, dmg = 8,  count = 2, radius = 40, duration = 2.5 },
			{ cd = 4.5, dmg = 12, count = 2, radius = 48, duration = 2.5 },
			{ cd = 4.5, dmg = 12, count = 3, radius = 48, duration = 3.0 },
			{ cd = 4.5, dmg = 16, count = 3, radius = 48, duration = 3.0 },
			{ cd = 4.5, dmg = 16, count = 4, radius = 58, duration = 3.5 },
		},
		evo = { name = "HOLY FLOOD", partner = "area", desc = "PUDDLES THAT HUNT THE UNDEAD",
			stats = { cd = 3.2, dmg = 22, count = 5, radius = 70, duration = 4.5, chase = 60 }, tint = { 0.6, 1, 1 } },
	},
	axe = {
		name = "BATTLE AXE", icon = "icon_axe",
		desc = { "HURLED HIGH, HITS HARD", "+1 AXE", "+10 DAMAGE", "+1 AXE, PIERCE +1", "+10 DAMAGE", "+1 AXE, PIERCE +2" },
		levels = {
			{ cd = 1.6, dmg = 20, count = 1, pierce = 3 },
			{ cd = 1.6, dmg = 20, count = 2, pierce = 3 },
			{ cd = 1.6, dmg = 30, count = 2, pierce = 3 },
			{ cd = 1.6, dmg = 30, count = 3, pierce = 4 },
			{ cd = 1.6, dmg = 40, count = 3, pierce = 4 },
			{ cd = 1.6, dmg = 40, count = 4, pierce = 6 },
		},
		evo = { name = "DEATH SPIRAL", partner = "armor", desc = "SCYTHES SPIRAL IN ALL DIRECTIONS",
			stats = { cd = 1.3, dmg = 55, count = 8, pierce = 99 }, tint = { 0.7, 1, 0.6 } },
	},
}
M.WEAPON_ORDER = { "bolt", "knife", "aura", "orb", "lightning", "water", "axe" }

M.PASSIVES = {
	might    = { name = "POWER RING",  icon = "icon_might",    desc = "INCREASES ALL DAMAGE",        max = 5 },
	armor    = { name = "IRON PLATE",  icon = "icon_armor",    desc = "REDUCES DAMAGE TAKEN",        max = 5 },
	heart    = { name = "HEART GEM",   icon = "icon_heart",    desc = "RAISES MAXIMUM HEALTH",       max = 5 },
	speed    = { name = "SWIFT BOOTS", icon = "icon_speed",    desc = "MOVE FASTER",                 max = 5 },
	cooldown = { name = "HOURGLASS",   icon = "icon_cooldown", desc = "WEAPONS FIRE MORE OFTEN",     max = 5 },
	magnet   = { name = "LODESTONE",   icon = "icon_magnet",   desc = "PULL GEMS FROM FURTHER AWAY", max = 5 },
	regen    = { name = "LIFE HERB",   icon = "icon_regen",    desc = "SLOWLY RECOVER HEALTH",       max = 5 },
	area     = { name = "SPELLBOOK",   icon = "icon_area",     desc = "BIGGER WEAPON EFFECTS",       max = 5 },
	amount   = { name = "DUPLICATOR",  icon = "icon_amount",   desc = "WEAPONS FIRE EXTRA SHOTS",    max = 2 },
	luck     = { name = "CLOVER",      icon = "icon_luck",     desc = "CRITS + CHANCE OF 4TH CHOICE", max = 5 },
	growth   = { name = "CROWN",       icon = "icon_growth",   desc = "GAIN MORE EXPERIENCE",        max = 5 },
}
M.PASSIVE_ORDER = { "might", "armor", "heart", "speed", "cooldown", "magnet", "regen", "area", "amount", "luck", "growth" }

-- label and per-level value for each passive (card previews and the stats screen)
local PASSIVE_VALUE = {
	might    = { "DAMAGE",   function(lv) return "+" .. (12 * lv) .. "%" end },
	armor    = { "ARMOR",    function(lv) return tostring(lv) end },
	heart    = { "MAX HP",   function(lv) return "+" .. (20 * lv) end },
	speed    = { "SPEED",    function(lv) return "+" .. (10 * lv) .. "%" end },
	cooldown = { "COOLDOWN", function(lv) return "-" .. (8 * lv) .. "%" end },
	magnet   = { "PICKUP",   function(lv) return "+" .. (40 * lv) .. "%" end },
	regen    = { "REGEN",    function(lv) return string.format("%.1f/S", 0.4 * lv) end },
	area     = { "AREA",     function(lv) return "+" .. (10 * lv) .. "%" end },
	amount   = { "AMOUNT",   function(lv) return "+" .. lv end },
	luck     = { "CRIT",     function(lv) return (5 * lv) .. "%" end },
	growth   = { "XP",       function(lv) return "+" .. (8 * lv) .. "%" end },
}

M.MAX_WEAPONS = 6
M.MAX_PASSIVES = 6

-- weapon stat fields shown on cards, in priority order
local FIELDS = {
	{ "dmg", "DMG" }, { "count", "AMOUNT" }, { "cd", "CD", "S" }, { "pierce", "PIERCE" },
	{ "radius", "AREA" }, { "aoe", "BLAST" }, { "tick", "TICK", "S" }, { "dist", "RANGE" },
	{ "spin", "SPIN" }, { "duration", "TIME", "S" },
}

local function num(v, suffix)
	local s
	if v == math.floor(v) then
		s = tostring(math.floor(v))
	else
		s = string.format("%.2f", v):gsub("0+$", ""):gsub("%.$", "")
	end
	return s .. (suffix or "")
end

-- "DMG 10>16  AMOUNT 1>2" for an upgrade, or "DMG 10  AMOUNT 1  CD 1S" for a new weapon
function M.weapon_delta(from, to)
	local parts = {}
	for _, f in ipairs(FIELDS) do
		local k, label, suffix = f[1], f[2], f[3]
		if to[k] and #parts < 3 then
			if not from then
				parts[#parts + 1] = label .. " " .. num(to[k], suffix)
			elseif from[k] ~= to[k] then
				parts[#parts + 1] = label .. " " .. num(from[k] or 0, suffix) .. ">" .. num(to[k], suffix)
			end
		end
	end
	return table.concat(parts, "  ")
end

function M.passive_delta(id, lv)
	local label, value = PASSIVE_VALUE[id][1], PASSIVE_VALUE[id][2]
	if lv == 0 then return label .. " " .. value(1) end
	return label .. " " .. value(lv) .. " > " .. value(lv + 1)
end

function M.weapon_stats(w)
	local def = M.WEAPONS[w.id]
	return w.evolved and def.evo.stats or def.levels[w.level]
end

function M.find_weapon(s, id)
	for _, w in ipairs(s.weapons) do
		if w.id == id then return w end
	end
end

local function owned_passives(s)
	local n = 0
	for _, lv in pairs(s.passives) do
		if lv > 0 then n = n + 1 end
	end
	return n
end

-- weapons that are max level, unevolved, and whose partner passive is owned
function M.evolvable(s)
	local list = {}
	for _, w in ipairs(s.weapons) do
		local def = M.WEAPONS[w.id]
		if not w.evolved and w.level >= #def.levels and (s.passives[def.evo.partner] or 0) > 0 then
			list[#list + 1] = w
		end
	end
	return list
end

-- Returns 3 (sometimes 4 with luck) choices: { kind, id, name, desc, delta, icon, tag, evo }
function M.roll(s)
	local pool = {}
	local partner_of = {}
	for _, w in ipairs(s.weapons) do partner_of[M.WEAPONS[w.id].evo.partner] = true end

	for _, id in ipairs(M.WEAPON_ORDER) do
		local def = M.WEAPONS[id]
		local w = M.find_weapon(s, id)
		local lv = w and w.level or 0
		if lv < #def.levels and (lv > 0 or #s.weapons < M.MAX_WEAPONS) then
			local evo_ready = (s.passives[def.evo.partner] or 0) > 0
			pool[#pool + 1] = {
				kind = "weapon", id = id, name = def.name, icon = def.icon, desc = def.desc[lv + 1],
				delta = M.weapon_delta(lv > 0 and def.levels[lv] or nil, def.levels[lv + 1]),
				tag = (lv == 0 and "NEW!" or ("LV " .. (lv + 1))) .. (evo_ready and " EVO" or ""),
				evo = evo_ready, weight = lv == 0 and 1.0 or 1.3,
			}
		end
	end
	local n_passives = owned_passives(s)
	for _, id in ipairs(M.PASSIVE_ORDER) do
		local def = M.PASSIVES[id]
		local lv = s.passives[id] or 0
		if lv < def.max and (lv > 0 or n_passives < M.MAX_PASSIVES) then
			local delta = M.passive_delta(id, lv)
			pool[#pool + 1] = {
				kind = "passive", id = id, name = def.name, icon = def.icon, desc = def.desc, delta = delta,
				tag = (lv == 0 and "NEW!" or ("LV " .. (lv + 1))) .. (partner_of[id] and " EVO" or ""),
				evo = partner_of[id] or false, weight = 0.8,
			}
		end
	end

	local want = 3
	if math.random() < 0.1 * (s.passives.luck or 0) then want = 4 end
	local choices = {}
	while #choices < want and #pool > 0 do
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
		choices[1] = { kind = "heal", id = "heal", name = "ROAST CHICKEN", icon = "icon_chicken",
			desc = "RESTORE 50 HEALTH", delta = "HP +50", tag = "", evo = false }
	end
	return choices
end

function M.apply(s, choice)
	if choice.kind == "weapon" then
		local w = M.find_weapon(s, choice.id)
		if w then
			w.level = w.level + 1
		else
			s.weapons[#s.weapons + 1] = { id = choice.id, level = 1, timer = 0.2, since = s.time }
		end
	elseif choice.kind == "passive" then
		s.passives[choice.id] = (s.passives[choice.id] or 0) + 1
		if choice.id == "heart" then
			s.player.hp = s.player.hp + 20
		end
	elseif choice.kind == "heal" then
		s.player.hp = math.min(s.stats.max_hp, s.player.hp + 50)
	end
	s.picks[#s.picks + 1] = { time = s.time, name = choice.name, tag = choice.tag }
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
		area = 1 + 0.1 * (p.area or 0),
		amount = p.amount or 0,
		crit = 0.05 * (p.luck or 0),
		growth = 1 + 0.08 * (p.growth or 0),
	}
end

-- Inventory summary for the HUD
function M.inventory(s)
	local list = {}
	for _, w in ipairs(s.weapons) do
		list[#list + 1] = { icon = M.WEAPONS[w.id].icon, level = w.evolved and "E" or w.level, kind = "weapon", evolved = w.evolved }
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
