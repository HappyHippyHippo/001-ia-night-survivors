-- Game balance and content definitions.
local M = {}

M.VIEW_HEIGHT = 540
M.WIN_TIME = 600 -- survive 10 minutes to win
M.TILE_SIZE = 192 -- ground tile size in world units
M.MAX_GEMS = 350

M.PLAYER = {
	max_hp = 100,
	speed = 140,
	radius = 14,
	magnet = 70,
	pickup_radius = 20,
	iframes = 0.5,
	rerolls = 3,
	skips = 2,
}

-- Z layers
M.Z = {
	ground = -5,
	shadow = -1,
	pool = -0.9,
	gem = -0.8,
	pickup = -0.7,
	aura = -0.6,
	enemy = 0,
	player = 0.5,
	projectile = 0.7,
	effect = 0.8,
	lightning = 0.9,
	number = 1.0,
}

M.ENEMIES = {
	bat      = { anim = "bat",      hp = 5,    speed = 92, damage = 3,  radius = 12, xp = 1,  knockback = 1.0 },
	zombie   = { anim = "zombie",   hp = 16,   speed = 42, damage = 6,  radius = 15, xp = 2,  knockback = 0.7 },
	skeleton = { anim = "skeleton", hp = 28,   speed = 62, damage = 8,  radius = 15, xp = 3,  knockback = 0.8 },
	ghost    = { anim = "ghost",    hp = 40,   speed = 78, damage = 10, radius = 15, xp = 5,  knockback = 0.6, alpha = 0.8 },
	eye      = { anim = "eye",      hp = 24,   speed = 70, damage = 6,  radius = 14, xp = 4,  knockback = 0.6,
	             ranged = { range = 230, cd = 2.6, speed = 150, damage = 8 } },
	ogre     = { anim = "ogre",     hp = 1200, speed = 52, damage = 20, radius = 30, xp = 60, knockback = 0.05, boss = true },
	brazier  = { anim = "brazier",  hp = 1,    speed = 0,  damage = 0,  radius = 16, xp = 0,  knockback = 0, prop = true },
}

-- Elite variants: stronger, golden, and they drop a treasure chest
M.ELITE = {
	from = 120, chance = 0.02,
	hp = 8, damage = 1.5, speed = 0.9, scale = 1.5, xp = 5, knockback = 0.3,
	tint = { 1, 0.85, 0.4 },
}

-- Braziers: breakable light sources that drop pickups
M.BRAZIER = {
	interval = 5, max_near = 4, near = 900, despawn = 1500,
	drops = { chicken = 40, magnet = 15, cross = 12, clock = 13, gem = 20 },
}

M.FREEZE_TIME = 6
M.CRIT_MULT = 2

-- Spawn director: the last entry whose time has been reached is active.
M.WAVES = {
	{ t = 0,   interval = 1.1,  batch = 2, max = 50,  types = { bat = 1 } },
	{ t = 30,  interval = 0.9,  batch = 3, max = 80,  types = { bat = 3, zombie = 1 } },
	{ t = 75,  interval = 0.8,  batch = 3, max = 110, types = { bat = 2, zombie = 3 } },
	{ t = 120, interval = 0.7,  batch = 4, max = 140, types = { zombie = 2, skeleton = 2, bat = 1 } },
	{ t = 180, interval = 0.6,  batch = 4, max = 170, types = { skeleton = 3, zombie = 1, ghost = 1 } },
	{ t = 210, interval = 0.6,  batch = 4, max = 180, types = { skeleton = 3, ghost = 1, eye = 1 } },
	{ t = 260, interval = 0.5,  batch = 5, max = 200, types = { ghost = 2, skeleton = 2, bat = 2, eye = 1 } },
	{ t = 340, interval = 0.45, batch = 5, max = 230, types = { ghost = 3, skeleton = 3, zombie = 2, eye = 1 } },
	{ t = 420, interval = 0.4,  batch = 6, max = 260, types = { ghost = 3, skeleton = 2, bat = 3, eye = 2 } },
	{ t = 500, interval = 0.35, batch = 7, max = 300, types = { ghost = 4, skeleton = 3, zombie = 2, bat = 2, eye = 2 } },
}

-- Scripted events (seconds)
M.EVENTS = {
	{ t = 90,  kind = "swarm", enemy = "bat", count = 28 },
	{ t = 150, kind = "boss" },
	{ t = 240, kind = "swarm", enemy = "zombie", count = 32 },
	{ t = 300, kind = "boss" },
	{ t = 390, kind = "swarm", enemy = "ghost", count = 32 },
	{ t = 450, kind = "boss" },
	{ t = 540, kind = "swarm", enemy = "skeleton", count = 40 },
	{ t = 570, kind = "boss" },
}

-- Enemy health grows over time
function M.hp_scale(time)
	return 1 + time / 60 * 0.22
end

function M.xp_to_next(level)
	if level < 20 then
		return 5 + (level - 1) * 13
	end
	return 252 + (level - 20) * 24
end

return M
