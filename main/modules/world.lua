-- Core simulation: player, enemies, projectiles, pickups, spawning and game flow.
-- Spawned game objects are pure visuals; all logic lives in plain Lua tables.
local C = require "main.modules.config"
local U = require "main.modules.upgrades"
local spatial = require "main.modules.spatial"
local weapons = require "main.modules.weapons"

local M = {}

local sqrt, floor, ceil, min, max = math.sqrt, math.floor, math.ceil, math.min, math.max
local cos, sin, atan2, random, pi = math.cos, math.sin, math.atan2, math.random, math.pi

local FACTORY = "/game#factory"
local HUD = "/hud#hud"
local MUSIC = "/game#snd_music"
local FLASH = vmath.vector4(1, 0.25, 0.25, 1)
local WHITE = vmath.vector4(1, 1, 1, 1)

local H = {
	up = hash("up"), down = hash("down"), left = hash("left"), right = hash("right"),
	confirm = hash("confirm"), pause = hash("pause"), touch = hash("touch"), mute = hash("mute"),
}

local scratch = {}
local sfx_last = {}

M.input = { up = 0, down = 0, left = 0, right = 0 }
M.clock = 0
M.muted = false

---------------------------------------------------------------------------
-- helpers
---------------------------------------------------------------------------

local function new_entity(anim, x, y, z, scale, on_done)
	local id = factory.create(FACTORY, vmath.vector3(x, y, z), nil, nil, scale or 1)
	local spr = msg.url(nil, id, "sprite")
	sprite.play_flipbook(spr, anim, on_done)
	return id, spr
end

local function compact(list)
	local j = 0
	for i = 1, #list do
		local v = list[i]
		if not v.dead then
			j = j + 1
			list[j] = v
		end
	end
	for i = #list, j + 1, -1 do
		list[i] = nil
	end
end

local function pick_weighted(types)
	local total = 0
	for _, w in pairs(types) do total = total + w end
	local r = random() * total
	for k, w in pairs(types) do
		r = r - w
		if r <= 0 then return k end
	end
	return next(types)
end

local function gem_anim(value)
	if value >= 20 then return "gem_red" elseif value >= 5 then return "gem_green" end
	return "gem_blue"
end

function M.sfx(name, min_gap)
	local last = sfx_last[name]
	if last and M.clock - last < (min_gap or 0.05) then return end
	sfx_last[name] = M.clock
	sound.play("/game#snd_" .. name)
end

function M.view_half()
	local w, h = window.get_size()
	if not h or h <= 0 then w, h = 960, 540 end
	return C.VIEW_HEIGHT / 2 * w / h, C.VIEW_HEIGHT / 2
end

function M.query(x, y, r)
	return scratch, spatial.query(x, y, r, scratch)
end

function M.banner(text)
	msg.post(HUD, "banner", { text = text })
end

---------------------------------------------------------------------------
-- setup / flow
---------------------------------------------------------------------------

function M.init()
	M.player_id = go.get_id("/player")
	M.player_spr = msg.url("/player#sprite")
	M.shadow_id = go.get_id("/player_shadow")
	M.aura_id = go.get_id("/aura")
	M.aura_spr = msg.url("/aura#sprite")
	sprite.play_flipbook(M.player_spr, "player_idle")
	sprite.play_flipbook("/player_shadow#sprite", "shadow")
	sprite.play_flipbook(M.aura_spr, "aura")
	M.build_ground()
	M.reset()
	M.s.state = "title"
	msg.post(HUD, "show_title")
end

function M.reset()
	local old = M.s
	if old then
		for _, list in ipairs({ old.enemies, old.projectiles, old.gems, old.pickups }) do
			for _, v in ipairs(list) do
				if not v.dead then go.delete(v.id) end
			end
		end
		for _, w in ipairs(old.weapons) do
			for _, id in ipairs(w.orbs or {}) do go.delete(id) end
		end
	end
	spatial.reset()
	local s = {
		state = "playing", time = 0, kills = 0, level = 1, xp = 0, xp_next = C.xp_to_next(1), pending = 0,
		player = { x = 0, y = 0, hp = C.PLAYER.max_hp, fx = 1, fy = 0, hurt = 0, anim = nil },
		enemies = {}, projectiles = {}, gems = {}, pickups = {},
		weapons = {}, passives = {},
		spawn_timer = 0.5, event_index = 1, enemy_serial = 0,
	}
	M.s = s
	U.apply(s, { kind = "weapon", id = "bolt" })
	s.stats = U.compute_stats(s, C.PLAYER)
	go.set_position(vmath.vector3(0, 0, C.Z.player), M.player_id)
	go.set_position(vmath.vector3(0, -22, C.Z.shadow), M.shadow_id)
	go.cancel_animations(M.player_spr, "tint")
	go.set(M.player_spr, "tint", WHITE)
	sprite.play_flipbook(M.player_spr, "player_idle")
	msg.post(M.aura_spr, "disable")
	M.aura_on = false
	M.inventory_dirty = true
	M.update_ground(true)
end

function M.start()
	M.reset()
	sound.stop(MUSIC)
	sound.play(MUSIC)
	msg.post(HUD, "hide_screens")
	M.banner("SURVIVE UNTIL DAWN!")
end

function M.game_over()
	local s = M.s
	s.state = "gameover"
	M.end_clock = M.clock
	sound.stop(MUSIC)
	M.sfx("gameover", 0)
	go.cancel_animations(M.player_spr, "tint")
	go.set(M.player_spr, "tint", vmath.vector4(0.5, 0.2, 0.2, 1))
	msg.post(HUD, "show_end", { victory = false, time = s.time, level = s.level, kills = s.kills })
end

function M.victory()
	local s = M.s
	s.state = "victory"
	M.end_clock = M.clock
	for _, e in ipairs(s.enemies) do
		if not e.dead then
			e.dead = true
			go.delete(e.id)
			M.spawn_effect("puff", e.x, e.y, C.Z.effect)
		end
	end
	compact(s.enemies)
	sound.stop(MUSIC)
	M.sfx("victory", 0)
	msg.post("@render:", "shake", { amount = 10 })
	msg.post(HUD, "show_end", { victory = true, time = s.time, level = s.level, kills = s.kills })
end

function M.open_levelup()
	local s = M.s
	s.state = "levelup"
	s.choices = U.roll(s)
	M.sfx("levelup", 0)
	msg.post(HUD, "show_levelup", { choices = s.choices, level = s.level })
end

function M.choose(index)
	local s = M.s
	if s.state ~= "levelup" then return end
	local c = s.choices[index]
	if not c then return end
	U.apply(s, c)
	s.stats = U.compute_stats(s, C.PLAYER)
	s.player.hp = min(s.player.hp, s.stats.max_hp)
	s.pending = s.pending - 1
	M.inventory_dirty = true
	M.sfx("select", 0)
	if s.pending > 0 then
		M.open_levelup()
	else
		s.state = "playing"
		msg.post(HUD, "hide_levelup")
	end
end

function M.toggle_pause()
	local s = M.s
	if s.state == "playing" then
		s.state = "paused"
		sound.pause(MUSIC, true)
		msg.post(HUD, "show_pause")
	elseif s.state == "paused" then
		s.state = "playing"
		sound.pause(MUSIC, false)
		msg.post(HUD, "hide_pause")
	end
end

function M.on_input(action_id, action)
	local inp = M.input
	if action_id == H.up then
		inp.up = action.released and 0 or action.value
	elseif action_id == H.down then
		inp.down = action.released and 0 or action.value
	elseif action_id == H.left then
		inp.left = action.released and 0 or action.value
	elseif action_id == H.right then
		inp.right = action.released and 0 or action.value
	elseif (action_id == H.confirm or action_id == H.touch) and action.pressed then
		local st = M.s.state
		if st == "title" or ((st == "gameover" or st == "victory") and M.clock - M.end_clock > 1.2) then
			M.start()
		end
	elseif action_id == H.pause and action.pressed then
		M.toggle_pause()
	elseif action_id == H.mute and action.pressed then
		M.muted = not M.muted
		sound.set_group_gain(hash("master"), M.muted and 0 or 1)
	end
end

---------------------------------------------------------------------------
-- per-frame update
---------------------------------------------------------------------------

function M.update(dt)
	dt = min(dt, 1 / 20)
	M.clock = M.clock + dt
	local s = M.s
	if s.state == "playing" then
		s.time = s.time + dt
		M.update_player(dt)
		M.update_spawner(dt)
		M.update_enemies(dt)
		weapons.update(M, dt)
		M.update_projectiles(dt)
		M.update_gems(dt)
		M.update_pickups(dt)
		compact(s.enemies)
		compact(s.projectiles)
		compact(s.gems)
		compact(s.pickups)
		if s.state == "playing" and s.time >= C.WIN_TIME then
			M.victory()
		elseif s.state == "playing" and s.pending > 0 then
			M.open_levelup()
		end
	end
	if M.aura_on then
		local p = s.player
		go.set_position(vmath.vector3(p.x, p.y, C.Z.aura), M.aura_id)
	end
	M.update_ground()
	msg.post("@render:", "follow", { position = vmath.vector3(s.player.x, s.player.y, 0) })
	msg.post(HUD, "hud", {
		hp = s.player.hp, max_hp = s.stats.max_hp, xp = s.xp, xp_next = s.xp_next,
		level = s.level, time = s.time, kills = s.kills,
	})
	if M.inventory_dirty then
		M.inventory_dirty = false
		msg.post(HUD, "inventory", { items = U.inventory(s) })
	end
end

function M.update_player(dt)
	local s = M.s
	local p, st = s.player, s.stats
	local ix = M.input.right - M.input.left
	local iy = M.input.up - M.input.down
	local len = sqrt(ix * ix + iy * iy)
	if len > 1 then
		ix, iy = ix / len, iy / len
	end
	local moving = len > 0.2
	if moving then
		p.x = p.x + ix * st.speed * dt
		p.y = p.y + iy * st.speed * dt
		local l = sqrt(ix * ix + iy * iy)
		p.fx, p.fy = ix / l, iy / l
	end
	local anim = moving and "player_walk" or "player_idle"
	if anim ~= p.anim then
		p.anim = anim
		sprite.play_flipbook(M.player_spr, anim)
	end
	go.set_position(vmath.vector3(p.x, p.y, C.Z.player), M.player_id)
	go.set_position(vmath.vector3(p.x, p.y - 22, C.Z.shadow), M.shadow_id)
	p.hurt = p.hurt - dt
	if st.regen > 0 then
		p.hp = min(st.max_hp, p.hp + st.regen * dt)
	end
end

function M.hurt_player(dmg)
	if M.god then return end
	local s = M.s
	local p = s.player
	p.hp = p.hp - max(1, dmg - s.stats.armor)
	p.hurt = C.PLAYER.iframes
	go.cancel_animations(M.player_spr, "tint")
	go.set(M.player_spr, "tint", FLASH)
	go.animate(M.player_spr, "tint", go.PLAYBACK_ONCE_FORWARD, WHITE, go.EASING_LINEAR, 0.3)
	M.sfx("hurt", 0.15)
	msg.post("@render:", "shake", { amount = 6 })
	if p.hp <= 0 then
		p.hp = 0
		M.game_over()
	end
end

---------------------------------------------------------------------------
-- spawning
---------------------------------------------------------------------------

function M.spawn_point(extra)
	local p = M.s.player
	local hw, hh = M.view_half()
	local r = sqrt(hw * hw + hh * hh) + (extra or 40)
	local a = random() * 2 * pi
	return p.x + cos(a) * r, p.y + sin(a) * r
end

function M.spawn_enemy(kind, x, y)
	local s = M.s
	local def = C.ENEMIES[kind]
	s.enemy_serial = s.enemy_serial + 1
	local z = C.Z.enemy + (s.enemy_serial % 1000) * 0.0002 + (def.boss and 0.25 or 0)
	local id, spr = new_entity(def.anim, x, y, z)
	local hp = def.hp * C.hp_scale(s.time)
	local e = {
		id = id, spr = spr, kind = kind, def = def, x = x, y = y, z = z,
		hp = hp, speed = def.speed * (0.9 + random() * 0.2), damage = def.damage, radius = def.radius,
		kx = 0, ky = 0, flash = 0, orb_t = 0,
		tint = vmath.vector4(1, 1, 1, def.alpha or 1),
		flash_tint = vmath.vector4(1, 0.25, 0.25, def.alpha or 1),
	}
	if def.alpha then go.set(spr, "tint", e.tint) end
	s.enemies[#s.enemies + 1] = e
	return e
end

function M.update_spawner(dt)
	local s = M.s
	local wave = C.WAVES[1]
	for _, w in ipairs(C.WAVES) do
		if s.time >= w.t then wave = w end
	end
	s.spawn_timer = s.spawn_timer - dt
	if s.spawn_timer <= 0 then
		s.spawn_timer = wave.interval
		local alive = #s.enemies
		for _ = 1, wave.batch do
			if alive >= wave.max then break end
			local x, y = M.spawn_point()
			M.spawn_enemy(pick_weighted(wave.types), x, y)
			alive = alive + 1
		end
	end

	local ev = C.EVENTS[s.event_index]
	if ev and s.time >= ev.t then
		s.event_index = s.event_index + 1
		local p = s.player
		if ev.kind == "boss" then
			local x, y = M.spawn_point(60)
			M.spawn_enemy("ogre", x, y)
			M.sfx("boss", 0)
			M.banner("A DEMON LORD APPROACHES!")
			msg.post("@render:", "shake", { amount = 8 })
		elseif ev.kind == "swarm" then
			local hw, hh = M.view_half()
			local r = sqrt(hw * hw + hh * hh) + 20
			for i = 1, ev.count do
				local a = i / ev.count * 2 * pi
				M.spawn_enemy(ev.enemy, p.x + cos(a) * r, p.y + sin(a) * r)
			end
			M.banner("THE HORDE CLOSES IN!")
		end
	end
end

---------------------------------------------------------------------------
-- enemies
---------------------------------------------------------------------------

function M.update_enemies(dt)
	local s = M.s
	local p = s.player
	local enemies = s.enemies
	spatial.clear()
	for i = 1, #enemies do
		if not enemies[i].dead then spatial.insert(enemies[i]) end
	end
	local hw, hh = M.view_half()
	local far = sqrt(hw * hw + hh * hh) + 260
	local decay = math.exp(-8 * dt)
	local touch_dmg = 0
	local pr = C.PLAYER.radius
	for i = 1, #enemies do
		local e = enemies[i]
		if not e.dead then
			local dx, dy = p.x - e.x, p.y - e.y
			local d = sqrt(dx * dx + dy * dy)
			if d > far then
				-- wrap stragglers around to the far side, ahead of the player
				e.x, e.y = p.x + dx * 0.85, p.y + dy * 0.85
				dx, dy = p.x - e.x, p.y - e.y
				d = sqrt(dx * dx + dy * dy)
			end
			local vx, vy = 0, 0
			if d > 1 then
				vx, vy = dx / d * e.speed, dy / d * e.speed
			end
			-- separation from neighbours
			local sx, sy = 0, 0
			local n = spatial.query(e.x, e.y, e.radius + 32, scratch)
			for j = 1, n do
				local o = scratch[j]
				if o ~= e and not o.dead then
					local ox, oy = e.x - o.x, e.y - o.y
					local rr = e.radius + o.radius
					local d2 = ox * ox + oy * oy
					if d2 < rr * rr then
						if d2 < 0.01 then
							ox, oy = random() - 0.5, random() - 0.5
							d2 = ox * ox + oy * oy
						end
						local od = sqrt(d2)
						local push = (rr - od) / rr * (o.def.boss and 4 or 1)
						sx, sy = sx + ox / od * push, sy + oy / od * push
					end
				end
			end
			if e.def.boss then sx, sy = 0, 0 end
			e.x = e.x + (vx + sx * 90 + e.kx) * dt
			e.y = e.y + (vy + sy * 90 + e.ky) * dt
			e.kx, e.ky = e.kx * decay, e.ky * decay
			if e.flash > 0 then
				e.flash = e.flash - dt
				if e.flash <= 0 then go.set(e.spr, "tint", e.tint) end
			end
			go.set_position(vmath.vector3(e.x, e.y, e.z), e.id)
			if d < e.radius + pr and e.damage > touch_dmg then
				touch_dmg = e.damage
			end
		end
	end
	if touch_dmg > 0 and p.hurt <= 0 then
		M.hurt_player(touch_dmg)
	end
end

function M.damage_enemy(e, dmg, kx, ky, silent)
	if e.dead then return end
	e.hp = e.hp - dmg * M.s.stats.might
	local kb = e.def.knockback
	e.kx = e.kx + (kx or 0) * kb
	e.ky = e.ky + (ky or 0) * kb
	if e.hp <= 0 then
		M.kill_enemy(e)
		return true
	end
	if e.flash <= 0 then go.set(e.spr, "tint", e.flash_tint) end
	e.flash = 0.08
	if not silent then M.sfx("hit", 0.06) end
end

function M.kill_enemy(e)
	local s = M.s
	e.dead = true
	go.delete(e.id)
	s.kills = s.kills + 1
	M.spawn_effect("puff", e.x, e.y, C.Z.effect, e.def.boss and 3 or 1)
	M.sfx("enemy_die", 0.05)
	M.drop_gem(e.x, e.y, e.def.xp)
	if e.def.boss then
		M.spawn_pickup("chest", e.x + 20, e.y)
		M.spawn_pickup("chicken", e.x - 20, e.y)
		msg.post("@render:", "shake", { amount = 10 })
	else
		local r = random()
		if r < 0.008 then
			M.spawn_pickup("chicken", e.x, e.y)
		elseif r < 0.011 then
			M.spawn_pickup("magnet", e.x, e.y)
		end
	end
end

function M.nearest_enemies(x, y, maxd, count)
	local list = {}
	local m2 = maxd * maxd
	for _, e in ipairs(M.s.enemies) do
		if not e.dead then
			local dx, dy = e.x - x, e.y - y
			local d2 = dx * dx + dy * dy
			if d2 < m2 then
				list[#list + 1] = { e = e, d = d2 }
			end
		end
	end
	table.sort(list, function(a, b) return a.d < b.d end)
	local out = {}
	for i = 1, min(count, #list) do out[i] = list[i].e end
	return out
end

---------------------------------------------------------------------------
-- projectiles & effects
---------------------------------------------------------------------------

function M.spawn_projectile(o)
	local rot = o.rotate and vmath.quat_rotation_z(atan2(o.vy, o.vx)) or nil
	o.id = factory.create(FACTORY, vmath.vector3(o.x, o.y, C.Z.projectile), rot)
	sprite.play_flipbook(msg.url(nil, o.id, "sprite"), o.anim)
	o.hit = {}
	o.speed = sqrt(o.vx * o.vx + o.vy * o.vy)
	M.s.projectiles[#M.s.projectiles + 1] = o
end

function M.spawn_visual(anim, z)
	local p = M.s.player
	return (new_entity(anim, p.x, p.y, z))
end

function M.spawn_effect(anim, x, y, z, scale)
	local id
	id = new_entity(anim, x, y, z, scale, function() go.delete(id) end)
end

function M.strike(x, y, dmg, aoe)
	local id, spr = new_entity("lightning", x, y + 135, C.Z.lightning)
	go.animate(spr, "tint.w", go.PLAYBACK_ONCE_FORWARD, 0, go.EASING_INQUAD, 0.35, 0, function() go.delete(id) end)
	M.spawn_effect("puff", x, y, C.Z.effect, aoe / 24)
	local list, n = M.query(x, y, aoe + 32)
	for j = 1, n do
		local e = list[j]
		if not e.dead then
			local dx, dy = e.x - x, e.y - y
			local r = aoe + e.radius
			if dx * dx + dy * dy < r * r then
				M.damage_enemy(e, dmg, 0, 0, true)
			end
		end
	end
end

function M.set_aura(radius)
	if not M.aura_on then
		M.aura_on = true
		msg.post(M.aura_spr, "enable")
	end
	local sc = radius * 2 / 192 * (1 + 0.03 * sin(M.clock * 6))
	go.set_scale(vmath.vector3(sc, sc, 1), M.aura_id)
end

function M.update_projectiles(dt)
	for _, p in ipairs(M.s.projectiles) do
		p.x = p.x + p.vx * dt
		p.y = p.y + p.vy * dt
		p.life = p.life - dt
		if p.life <= 0 then
			p.dead = true
		else
			local n = spatial.query(p.x, p.y, p.radius + 32, scratch)
			for j = 1, n do
				local e = scratch[j]
				if not e.dead and not p.hit[e] then
					local dx, dy = e.x - p.x, e.y - p.y
					local rr = e.radius + p.radius
					if dx * dx + dy * dy < rr * rr then
						p.hit[e] = true
						M.damage_enemy(e, p.dmg, p.vx / p.speed * p.kb, p.vy / p.speed * p.kb)
						M.spawn_effect("spark", p.x, p.y, C.Z.effect)
						p.pierce = p.pierce - 1
						if p.pierce <= 0 then
							p.dead = true
							break
						end
					end
				end
			end
		end
		if p.dead then
			go.delete(p.id)
		else
			go.set_position(vmath.vector3(p.x, p.y, C.Z.projectile), p.id)
		end
	end
end

---------------------------------------------------------------------------
-- gems & pickups
---------------------------------------------------------------------------

function M.drop_gem(x, y, value)
	local s = M.s
	if #s.gems >= C.MAX_GEMS then
		-- merge into an existing gem to keep object counts bounded
		local g = s.gems[random(#s.gems)]
		if not g.dead then
			g.value = g.value + value
			sprite.play_flipbook(msg.url(nil, g.id, "sprite"), gem_anim(g.value))
			return
		end
	end
	local id = new_entity(gem_anim(value), x, y, C.Z.gem)
	s.gems[#s.gems + 1] = { id = id, x = x, y = y, value = value, pull = false, speed = 0 }
end

function M.add_xp(v)
	local s = M.s
	s.xp = s.xp + v
	while s.xp >= s.xp_next do
		s.xp = s.xp - s.xp_next
		s.level = s.level + 1
		s.xp_next = C.xp_to_next(s.level)
		s.pending = s.pending + 1
	end
end

function M.update_gems(dt)
	local s = M.s
	local p = s.player
	local m2 = s.stats.magnet * s.stats.magnet
	local pr = C.PLAYER.pickup_radius
	for _, g in ipairs(s.gems) do
		if not g.dead then
			local dx, dy = p.x - g.x, p.y - g.y
			local d2 = dx * dx + dy * dy
			if not g.pull and d2 < m2 then
				g.pull = true
				g.speed = -110 -- little hop away before flying in
			end
			if g.pull then
				local d = sqrt(d2)
				g.speed = min(g.speed + 1500 * dt, 950)
				if d < pr or d < g.speed * dt then
					g.dead = true
					go.delete(g.id)
					M.add_xp(g.value)
					M.sfx("gem", 0.035)
				else
					g.x = g.x + dx / d * g.speed * dt
					g.y = g.y + dy / d * g.speed * dt
					go.set_position(vmath.vector3(g.x, g.y, C.Z.gem), g.id)
				end
			end
		end
	end
end

function M.spawn_pickup(kind, x, y)
	local id = new_entity(kind, x, y, C.Z.pickup)
	local s = M.s
	s.pickups[#s.pickups + 1] = { id = id, kind = kind, x = x, y = y }
end

function M.update_pickups(dt)
	local s = M.s
	local p = s.player
	local r = C.PLAYER.pickup_radius + 12
	for _, k in ipairs(s.pickups) do
		local dx, dy = p.x - k.x, p.y - k.y
		if dx * dx + dy * dy < r * r then
			k.dead = true
			go.delete(k.id)
			if k.kind == "chicken" then
				p.hp = min(s.stats.max_hp, p.hp + 30)
				M.sfx("heal", 0)
			elseif k.kind == "magnet" then
				for _, g in ipairs(s.gems) do
					if not g.pull then
						g.pull = true
						g.speed = 0
					end
				end
				M.sfx("pickup", 0)
				M.banner("VACUUM!")
			elseif k.kind == "chest" then
				s.pending = s.pending + 1
				M.sfx("pickup", 0)
				M.banner("TREASURE!")
			end
		end
	end
end

---------------------------------------------------------------------------
-- infinite ground
---------------------------------------------------------------------------

local function tile_variant(gx, gy)
	local h = sin(gx * 12.9898 + gy * 78.233) * 43758.5453
	h = h - floor(h)
	if h < 0.62 then return "ground_1" elseif h < 0.86 then return "ground_2"
	elseif h < 0.95 then return "ground_3" end
	return "ground_4"
end

function M.build_ground()
	local T = C.TILE_SIZE
	local hx = ceil(C.VIEW_HEIGHT * 2.4 / 2 / T) + 1 -- supports up to ~21:9 windows
	local hy = ceil(C.VIEW_HEIGHT / 2 / T) + 1
	M.ground = {}
	for ox = -hx, hx do
		for oy = -hy, hy do
			local id, spr = new_entity("ground_1", 0, 0, C.Z.ground)
			M.ground[#M.ground + 1] = { id = id, spr = spr, ox = ox, oy = oy, anim = "ground_1" }
		end
	end
end

function M.update_ground(force)
	local p = M.s.player
	local T = C.TILE_SIZE
	local cx, cy = floor(p.x / T), floor(p.y / T)
	if not force and cx == M.ground_cx and cy == M.ground_cy then return end
	M.ground_cx, M.ground_cy = cx, cy
	for _, t in ipairs(M.ground) do
		local gx, gy = cx + t.ox, cy + t.oy
		go.set_position(vmath.vector3((gx + 0.5) * T, (gy + 0.5) * T, C.Z.ground), t.id)
		local anim = tile_variant(gx, gy)
		if anim ~= t.anim then
			t.anim = anim
			sprite.play_flipbook(t.spr, anim)
		end
	end
end

return M
