-- Weapon behaviours. Each weapon function receives the world module, the
-- weapon instance ({ id, level, timer, evolved, ... }), its current stats,
-- dt and the evolution definition (nil until evolved).
local C = require "main.modules.config"
local U = require "main.modules.upgrades"

local M = {}

local sqrt, cos, sin, abs, min = math.sqrt, math.cos, math.sin, math.abs, math.min
local atan2, random, pi = math.atan2, math.random, math.pi

function M.update(world, dt)
	for _, w in ipairs(world.s.weapons) do
		local def = U.WEAPONS[w.id]
		M[w.id](world, w, U.weapon_stats(w), dt, w.evolved and def.evo or nil)
	end
end

local function ready(world, w, cd, dt)
	w.timer = w.timer - dt
	if w.timer > 0 then return false end
	w.timer = cd * world.s.stats.cooldown
	return true
end

function M.bolt(world, w, L, dt, evo)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	local st = world.s.stats
	local p = world.s.player
	local count = L.count + st.amount
	local targets = world.nearest_enemies(p.x, p.y, 520, count)
	if #targets == 0 then
		w.timer = 0
		return
	end
	w.timer = L.cd * st.cooldown
	for i = 1, count do
		local t = targets[i] or targets[1]
		local a = atan2(t.y - p.y, t.x - p.x)
		if not targets[i] then
			a = a + (i - 1) * 0.3 * (i % 2 == 0 and 1 or -1)
		end
		world.spawn_projectile({
			anim = "bolt", src = "bolt", x = p.x, y = p.y, vx = cos(a) * L.speed, vy = sin(a) * L.speed,
			dmg = L.dmg, pierce = L.pierce, life = 1.5, radius = 10 * st.area, kb = 70,
			scale = st.area, tint = evo and evo.tint,
		})
	end
	world.sfx("shoot", 0.08)
end

function M.knife(world, w, L, dt, evo)
	if not ready(world, w, L.cd, dt) then return end
	local st = world.s.stats
	local p = world.s.player
	local fx, fy = p.fx, p.fy
	local count = L.count + st.amount
	for i = 1, count do
		local off = (i - (count + 1) / 2) * 14
		local vx, vy = fx * L.speed, fy * L.speed
		if evo then
			-- evolved: a jittery stream
			local a = atan2(fy, fx) + (random() - 0.5) * 0.25
			vx, vy = cos(a) * L.speed, sin(a) * L.speed
		end
		world.spawn_projectile({
			anim = "knife", src = "knife", x = p.x - fy * off, y = p.y + fx * off, vx = vx, vy = vy,
			dmg = L.dmg, pierce = L.pierce, life = 0.85, radius = 9 * st.area, kb = 40, rotate = true,
			scale = st.area, tint = evo and evo.tint,
		})
	end
	world.sfx("knife", 0.08)
end

function M.aura(world, w, L, dt, evo)
	local st = world.s.stats
	local radius = L.radius * st.area
	world.set_aura(radius, evo and evo.tint)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	w.timer = L.tick
	local p = world.s.player
	local list, n = world.query(p.x, p.y, radius + 32)
	local healed = 0
	for j = 1, n do
		local e = list[j]
		if not e.dead then
			local dx, dy = e.x - p.x, e.y - p.y
			local r = radius + e.radius * 0.5
			local d2 = dx * dx + dy * dy
			if d2 < r * r then
				local d = sqrt(d2) + 0.01
				world.damage_enemy(e, L.dmg, dx / d * 90, dy / d * 90, true, "aura")
				if L.heal and healed < 6 then
					healed = healed + L.heal
				end
			end
		end
	end
	if healed > 0 then world.heal(healed) end
end

function M.orb(world, w, L, dt, evo)
	local st = world.s.stats
	local count = L.count + st.amount
	w.orbs = w.orbs or {}
	while #w.orbs < count do
		w.orbs[#w.orbs + 1] = world.spawn_visual("orb", C.Z.projectile)
		w.orb_style = nil
	end
	-- refresh size/tint whenever area or evolution changes
	local style = st.area .. (evo and "e" or "")
	if w.orb_style ~= style then
		w.orb_style = style
		for _, id in ipairs(w.orbs) do
			go.set_scale(vmath.vector3(st.area, st.area, 1), id)
			if evo then
				go.set(msg.url(nil, id, "sprite"), "tint", vmath.vector4(evo.tint[1], evo.tint[2], evo.tint[3], 1))
			end
		end
	end
	w.angle = (w.angle or 0) + L.spin * dt
	local p = world.s.player
	local now = world.s.time
	local orb_r = 14 * st.area
	for i, id in ipairs(w.orbs) do
		local a = w.angle + (i - 1) * 2 * pi / count
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
					world.damage_enemy(e, L.dmg, dx / d * 160, dy / d * 160, false, "orb")
				end
			end
		end
	end
end

function M.lightning(world, w, L, dt, evo)
	w.timer = w.timer - dt
	if w.timer > 0 then return end
	local st = world.s.stats
	local p = world.s.player
	local hw, hh = world.view_half()
	local cands = {}
	for _, e in ipairs(world.s.enemies) do
		if not e.dead and not e.def.prop and abs(e.x - p.x) < hw - 20 and abs(e.y - p.y) < hh - 20 then
			cands[#cands + 1] = e
		end
	end
	if #cands == 0 then
		w.timer = 0.2
		return
	end
	w.timer = L.cd * st.cooldown
	for i = 1, min(L.count + st.amount, #cands) do
		local k = random(i, #cands)
		cands[i], cands[k] = cands[k], cands[i]
		world.strike(cands[i].x, cands[i].y, L.dmg, L.aoe * st.area, "lightning", evo and evo.tint)
	end
	world.sfx("thunder", 0.1)
	msg.post("@render:", "shake", { amount = 5 })
end

function M.water(world, w, L, dt, evo)
	if not ready(world, w, L.cd, dt) then return end
	local st = world.s.stats
	local p = world.s.player
	local count = L.count + st.amount
	local targets = world.nearest_enemies(p.x, p.y, 300, count)
	for i = 1, count do
		local tx, ty
		if targets[i] then
			tx, ty = targets[i].x, targets[i].y
		else
			local a = random() * 2 * pi
			local r = 60 + random() * 140
			tx, ty = p.x + cos(a) * r, p.y + sin(a) * r
		end
		world.throw_flask(p.x, p.y, tx, ty, {
			radius = L.radius * st.area, dmg = L.dmg, duration = L.duration, chase = L.chase,
			tint = evo and evo.tint,
		})
	end
end

function M.axe(world, w, L, dt, evo)
	if not ready(world, w, L.cd, dt) then return end
	local st = world.s.stats
	local p = world.s.player
	local count = L.count + st.amount
	for i = 1, count do
		local o = {
			anim = "axe", src = "axe", x = p.x, y = p.y, dmg = L.dmg, pierce = L.pierce,
			radius = 14 * st.area, kb = 80, scale = st.area, spin = 10,
			tint = evo and evo.tint,
		}
		if evo then
			-- evolved: scythes spiral outward in every direction
			local a = (i - 1) / count * 2 * pi + world.s.time
			o.vx, o.vy, o.turn, o.life = cos(a) * 240, sin(a) * 240, 2.2, 1.8
		else
			local side = (i % 2 == 0) and -1 or 1
			if p.fx < -0.2 then side = -side end
			o.vx = side * (50 + (i - 1) * 45 + random() * 40)
			o.vy = 520 + random() * 80
			o.g, o.life = -1100, 1.6
		end
		world.spawn_projectile(o)
	end
	world.sfx("knife", 0.1)
end

return M
