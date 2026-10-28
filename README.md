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
| Pick upgrade | 1 2 3, arrows + Enter, or mouse click |
| Start / retry | Enter / Space / click / pad A |
| Pause | P / Esc / pad Start |
| Mute | M |

## Content

- **Enemies:** bat, zombie, skeleton, ghost, plus a demon-lord boss (drops a treasure chest = free upgrade).
- **Events:** encircling swarms at 1:30, 4:00, 6:30, 9:00; bosses at 2:30, 5:00, 7:30, 9:30.
- **Weapons (6 levels each):** Magic Bolt, Throwing Knife, Garlic Aura, Holy Orbs, Thunder.
- **Passives (5 levels each):** Power Ring, Iron Plate, Heart Gem, Swift Boots, Hourglass, Lodestone, Life Herb.
- **Pickups:** XP gems (blue/green/red), roast chicken (heal), magnet (vacuum all gems), chest.

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
main/hud/                     GUI (HUD, level-up cards, title/pause/end screens), built in code
main/render/                  follow camera render script (fixed 540-unit view height)
main/assets/                  generated images, atlas, bitmap font, sounds
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
