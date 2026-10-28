components {
  id: "game"
  component: "/main/game.script"
}
embedded_components {
  id: "factory"
  type: "factory"
  data: "prototype: \"/main/entity.go\"\n"
  ""
}
embedded_components {
  id: "snd_shoot"
  type: "sound"
  data: "sound: \"/main/assets/sounds/shoot.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.35\n"
  ""
}
embedded_components {
  id: "snd_knife"
  type: "sound"
  data: "sound: \"/main/assets/sounds/knife.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.4\n"
  ""
}
embedded_components {
  id: "snd_hit"
  type: "sound"
  data: "sound: \"/main/assets/sounds/hit.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.35\n"
  ""
}
embedded_components {
  id: "snd_enemy_die"
  type: "sound"
  data: "sound: \"/main/assets/sounds/enemy_die.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.4\n"
  ""
}
embedded_components {
  id: "snd_gem"
  type: "sound"
  data: "sound: \"/main/assets/sounds/gem.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.3\n"
  ""
}
embedded_components {
  id: "snd_hurt"
  type: "sound"
  data: "sound: \"/main/assets/sounds/hurt.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.6\n"
  ""
}
embedded_components {
  id: "snd_thunder"
  type: "sound"
  data: "sound: \"/main/assets/sounds/thunder.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.5\n"
  ""
}
embedded_components {
  id: "snd_heal"
  type: "sound"
  data: "sound: \"/main/assets/sounds/heal.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.6\n"
  ""
}
embedded_components {
  id: "snd_select"
  type: "sound"
  data: "sound: \"/main/assets/sounds/select.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.5\n"
  ""
}
embedded_components {
  id: "snd_pickup"
  type: "sound"
  data: "sound: \"/main/assets/sounds/pickup.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.6\n"
  ""
}
embedded_components {
  id: "snd_levelup"
  type: "sound"
  data: "sound: \"/main/assets/sounds/levelup.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.6\n"
  ""
}
embedded_components {
  id: "snd_gameover"
  type: "sound"
  data: "sound: \"/main/assets/sounds/gameover.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.7\n"
  ""
}
embedded_components {
  id: "snd_victory"
  type: "sound"
  data: "sound: \"/main/assets/sounds/victory.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.7\n"
  ""
}
embedded_components {
  id: "snd_boss"
  type: "sound"
  data: "sound: \"/main/assets/sounds/boss.wav\"\n"
  "looping: 0\n"
  "group: \"sfx\"\n"
  "gain: 0.7\n"
  ""
}
embedded_components {
  id: "snd_music"
  type: "sound"
  data: "sound: \"/main/assets/sounds/music.wav\"\n"
  "looping: 1\n"
  "group: \"music\"\n"
  "gain: 0.45\n"
  ""
}
