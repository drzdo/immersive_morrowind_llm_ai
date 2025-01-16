local defaultConfig = {
    version = "v1.0",

    server_host = 'localhost',
    server_port = 18080,
    auto_reconnect = true,

    debug = false,

    dialog_hide_topics = true,

    hud_npc_label_hide_after_sec = 4,
    hud_player_label_hide_after_sec = 2

    -- target_npc_button = {
    -- 	keyCode = tes3.scanCode.v,
    -- 	isShiftDown = false,
    -- 	isControlDown = false,
    -- 	isAltDown = true,
    -- },
}

local config = mwse.loadConfig("zdo_immersive_morrowind_ai", defaultConfig)
return config
