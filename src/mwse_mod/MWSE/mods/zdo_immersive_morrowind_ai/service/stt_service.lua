local this = {}

local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local util = require("zdo_immersive_morrowind_ai.common.util")
local npc_service = require("zdo_immersive_morrowind_ai.service.npc_service")

this.is_listening = false
this.recognized_text = ""

function this.setup(on_update)
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "stt_start_listening" then
            this.is_listening = true
            this.recognized_text = ""

            on_update()

            eventbus.produce_event_from_game({
                data = {
                    type = "player_starts_speaking_looking_at",
                    actor_ref = util.ray_test_actor_ref()
                }
            })
        elseif e["data"]["type"] == "stt_stop_listening" then
            this.is_listening = false

            on_update()

            eventbus.produce_event_from_game({
                data = {
                    type = "player_stops_speaking_looking_at",
                    actor_ref = util.ray_test_actor_ref()
                }
            })
        elseif e["data"]["type"] == "stt_recognition_update" then
            this.recognized_text = e["data"]["text"]

            on_update()
        elseif e["data"]["type"] == "stt_recognition_complete" then
            this.is_listening = false
            this.recognized_text = e["data"]["text"]

            local text = this.recognized_text
            timer.start({
                duration = 1,
                type = timer.real,
                persist = false,
                callback = function(e)
                    if text == this.recognized_text then
                        this.recognized_text = ""
                    end
                end
            })

            on_update()
        end
    end, {
        unregisterOnLoad = false
    })
end

return this
