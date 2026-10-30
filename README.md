# Night Survivors

A small "Vampire Survivors"-style auto-shooter made with [Defold](https://defold.com).
Survive the undead horde until dawn (10:00). Weapons fire on their own; you move,
collect XP gems and pick an upgrade every level.

Every asset (sprites, tiles, icons, font, sound effects and music) is generated
procedurally by `tools/generate_assets.py` (pure Python 3, no dependencies).

## Run

Open the folder in the Defold editor (`game.project`) and press **Project ▸ Build** (⌘B).

## Controls

| Action | Keys / pad |
| --- | --- |
| Move | WASD / arrow keys / left stick / d-pad |
| Pick upgrade | 1 2 3 4, arrows + Enter, or mouse click |
| Reroll / skip a level-up | R / X (pad X / Y) |
| Pause + stats screen | P / Tab / Esc (pad Start / Back) |
| Damage numbers on/off | N |
| Start / retry | Enter / Space / click / pad A |
| Mute | M |
| Sound volumes (master / music / SFX) | O (pad B): arrows to select / adjust, or click the bars; saved between sessions |

## Content

- **Enemies:** bat, zombie, skeleton, ghost, eye (keeps its distance and shoots), demon-lord boss.
  Golden **elites** (from 2:00) are tougher and drop a chest.
- **Events:** encircling swarms at 1:30, 4:00, 6:30, 9:00; bosses at 2:30, 5:00, 7:30, 9:30.
- **Weapons (6 levels + evolution):**

  | Weapon | Evolves with | Into |
  | --- | --- | --- |
  | Magic Bolt | Hourglass | Arcane Storm |
  | Throwing Knife | Swift Boots | Thousand Edges |
  | Garlic Aura | Heart Gem | Soul Eater (heals) |
  | Holy Orbs | Power Ring | Sun Halo |
  | Thunder | Lodestone | Storm Lord |
  | Holy Water | Spellbook | Holy Flood (puddles chase enemies) |
  | Battle Axe | Iron Plate | Death Spiral |

  Evolving: get the weapon to max level, own its partner item, then open a chest (bosses and elites drop them).
- **Passives:** Power Ring (damage), Iron Plate (armor), Heart Gem (max HP), Swift Boots (speed),
  Hourglass (cooldown), Lodestone (pickup range), Life Herb (regen), Spellbook (area),
  Duplicator (+projectiles), Clover (crit chance + chance of a 4th card), Crown (XP gain).
- **Slots:** at most 6 weapons and 6 passives, so choices matter. 3 rerolls and 2 skips per run.
- **Braziers** appear around the map; break them for chicken (heal), magnet (vacuum gems),
  cross (wipes the screen), clock (freezes enemies) or a big gem.

## Following your build

- **Level-up cards** show the exact change: `DMG 10>16  AMOUNT 1>2` for weapons, `COOLDOWN -8% > -16%`
  for passives. Purple borders / `EVO` tags mark picks that complete an evolution pair.
- **Stats screen** (P / Tab): every player stat, plus a table of weapons sorted by damage dealt with
  DPS, kills and evolution status (`NEED` item, `ITEM OK`, `CHEST!` = ready, `EVOLVED`).
- **Damage numbers** float over enemies; critical hits are larger and gold.
- **End screen**: run summary (time, level, kills, damage taken, healing, chests, evolutions),
  the weapon damage table, and personal records saved between sessions.

## Project layout

```
game.project                  engine settings (nearest filtering, raised object limits)
input/game.input_binding      keyboard / mouse / gamepad bindings
main/main.collection          game, player, shadow, aura and HUD objects
main/game.go / game.script    entity factory, sounds, script entry point
main/entity.go                generic sprite object spawned for everything
main/modules/config.lua       balance: player, enemies, waves, events, XP curve
main/modules/upgrades.lua     weapon/passive definitions and level-up rolls
main/modules/weapons.lua      weapon behaviours
main/modules/world.lua        simulation: movement, spawning, collisions, pickups, flow
main/modules/spatial.lua      spatial hash for enemy queries
main/modules/stats.lua        formatting for the stats / end screens
main/modules/audio.lua        volume settings (sound group gains), persisted
main/hud/                     GUI (HUD, level-up cards, title/pause/end screens), built in code
main/render/                  follow camera render script (fixed 540-unit view height)
main/assets/                  generated images, atlas, pixel TrueType font, sounds
tools/generate_assets.py      regenerates everything in main/assets
```

The simulation is data-oriented: enemies, projectiles and gems are plain Lua tables
updated by one script; their game objects are only visuals. This keeps hundreds of
enemies cheap and avoids physics.

## Regenerating assets

```
python3 tools/generate_assets.py
```

## Debug autoplay

The engine can run the game unattended (bot movement, random upgrades), sped up and
optionally invulnerable, printing stats every 15 game-seconds:

```
dmengine --config=game.autoplay=1 --config=game.speed=8 --config=game.god=1 build/default/game.projectc
```

Add `--config=game.test_evo=1` to start with every weapon maxed and evolved.

## Web build (GitHub Pages)

`docs/` holds the HTML5 bundle served by GitHub Pages. Rebuild it with
**Project ▸ Bundle ▸ HTML5** in the editor (or Bob) and copy the bundle's contents into `docs/`.
