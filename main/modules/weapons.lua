-- Weapon behaviours. Each weapon function receives the world module, the
-- weapon instance ({ id, level, timer, ... }), its current level stats and dt.
local C = require "main.modules.config"
local U = require "main.modules.upgrades"

local M = {}

local sqrt, cos, sin, abs, min = math.sqrt, math.cos, math.sin, math.abs, math.min
local atan2, random, pi = math.atan2, math.random, math.pi

function M.update(world, dt)
	for _, w in ipairs(world.s.weapons) do
		M[w.id](world, w, U.WEAPONS[w.id].levels[w.level], dt)
	end
end

function M.bolt(world, w, L, dt)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	local p = world.s.player
	local targets = world.nearest_enemies(p.x, p.y, 520, L.count)
	if #targets == 0 then
		w.timer = 0
		return
	end
	w.timer = L.cd * world.s.stats.cooldown
	for i = 1, L.count do
		local t = targets[i] or targets[1]
		local a = atan2(t.y - p.y, t.x - p.x)
		if not targets[i] then
			a = a + (i - 1) * 0.3 * (i % 2 == 0 and 1 or -1)
		end
		world.spawn_projectile({
			anim = "bolt", x = p.x, y = p.y, vx = cos(a) * L.speed, vy = sin(a) * L.speed,
			dmg = L.dmg, pierce = L.pierce, life = 1.5, radius = 10, kb = 70,
		})
	end
	world.sfx("shoot", 0.08)
end

function M.knife(world, w, L, dt)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	w.timer = L.cd * world.s.stats.cooldown
	local p = world.s.player
	local fx, fy = p.fx, p.fy
	for i = 1, L.count do
		local off = (i - (L.count + 1) / 2) * 14
		world.spawn_projectile({
			anim = "knife", x = p.x - fy * off, y = p.y + fx * off, vx = fx * L.speed, vy = fy * L.speed,
			dmg = L.dmg, pierce = L.pierce, life = 0.85, radius = 9, kb = 40, rotate = true,
		})
	end
	world.sfx("knife", 0.08)
end

function M.aura(world, w, L, dt)
	world.set_aura(L.radius)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	w.timer = L.tick
	local p = world.s.player
	local list, n = world.query(p.x, p.y, L.radius + 32)
	for j = 1, n do
		local e = list[j]
		if not e.dead then
			local dx, dy = e.x - p.x, e.y - p.y
			local r = L.radius + e.radius * 0.5
			local d2 = dx * dx + dy * dy
			if d2 < r * r then
				local d = sqrt(d2) + 0.01
				world.damage_enemy(e, L.dmg, dx / d * 90, dy / d * 90, true)
			end
		end
	end
end

function M.orb(world, w, L, dt)
	w.orbs = w.orbs or {}
	while #w.orbs < L.count do
		w.orbs[#w.orbs + 1] = world.spawn_visual("orb", C.Z.projectile)
	end
	w.angle = (w.angle or 0) + L.spin * dt
	local p = world.s.player
	local now = world.s.time
	local orb_r = 14
	for i, id in ipairs(w.orbs) do
		local a = w.angle + (i - 1) * 2 * pi / L.count
		local x, y = p.x + cos(a) * L.dist, p.y + sin(a) * L.dist
		go.set_position(vmath.vector3(x, y, C.Z.projectile), id)
		local list, n = world.query(x, y, orb_r + 32)
		for j = 1, n do
			local e = list[j]
			if not e.dead and e.orb_t <= now then
				local dx, dy = e.x - x, e.y - y
				local r = e.radius + orb_r
				local d2 = dx * dx + dy * dy
				if d2 < r * r then
					e.orb_t = now + 0.45
					local d = sqrt(d2) + 0.01
					world.damage_enemy(e, L.dmg, dx / d * 160, dy / d * 160)
				end
			end
		end
	end
end

function M.lightning(world, w, L, dt)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	local p = world.s.player
	local hw, hh = world.view_half()
	local cands = {}
	for _, e in ipairs(world.s.enemies) do
		if not e.dead and abs(e.x - p.x) < hw - 20 and abs(e.y - p.y) < hh - 20 then
			cands[#cands + 1] = e
		end
	end
	if #cands == 0 then
		w.timer = 0.2
		return
	end
	w.timer = L.cd * world.s.stats.cooldown
	for i = 1, min(L.count, #cands) do
		local k = random(i, #cands)
		cands[i], cands[k] = cands[k], cands[i]
		world.strike(cands[i].x, cands[i].y, L.dmg, L.aoe)
	end
	world.sfx("thunder", 0.1)
	msg.post("@render:", "shake", { amount = 5 })
end

return M
