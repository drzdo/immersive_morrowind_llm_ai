local config = require("zdo_immersive_morrowind_ai.config")
local util = require("zdo_immersive_morrowind_ai.common.util")

local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")

local player_service = require("zdo_immersive_morrowind_ai.service.player_service")
local env_service = require("zdo_immersive_morrowind_ai.service.env_service")
local npc_service = require("zdo_immersive_morrowind_ai.service.npc_service")
local stt_service = require("zdo_immersive_morrowind_ai.service.stt_service")
local actor_say_service = require("zdo_immersive_morrowind_ai.service.actor_say_service")

local dialog = require("zdo_immersive_morrowind_ai.ui.dialog")
local hud = require("zdo_immersive_morrowind_ai.ui.hud")

local this = {}
this.first_time_loaded = true

function this.setup()
    timer.start({
        duration = 1,
        iterations = -1,
        type = timer.real,
        persist = false,
        callback = function(e)
            if tes3.mobilePlayer.object.name == 'player' then
                return
            end

            e.timer:cancel()

            if this.first_time_loaded then
                this.first_time_loaded = false
                util.log("Loaded " .. config.version)

                player_service.setup()
                env_service.setup()
                npc_service.setup()

                dialog.setup(this.first_time_loaded)
                hud.setup()

                stt_service.setup(function()
                    dialog.handle_voice_recognition_update(stt_service.is_listening, stt_service.recognized_text)
                    hud.handle_voice_recognition_update(stt_service.is_listening, stt_service.recognized_text)
                end)
                actor_say_service.setup(function(ref, text, reaction_text, duration_sec)
                    dialog.handle_actor_says(ref, text, reaction_text, duration_sec)
                    hud.handle_actor_says(ref, text, reaction_text, duration_sec)
                end)
            end

            eventbus.disconnect()
            eventbus.run_connection_maintaining_loop()
            hud.create_hud()
        end
    })
end

event.register(tes3.event.loaded, this.setup)

event.register("modConfigReady", function()
    require("zdo_immersive_morrowind_ai.mcm")
end)

return this
