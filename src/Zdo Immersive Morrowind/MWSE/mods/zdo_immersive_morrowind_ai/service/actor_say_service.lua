local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local this = {}

function this.setup(on_say)
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "actor_says" then
            local speaker_ref = tes3.getReference(e["data"]["speaker_ref"]["ref_id"])
            on_say(speaker_ref, e["data"]["text"], e["data"]["reaction_text"], e["data"]["audio_duration_sec"])
        end
    end, {
        unregisterOnLoad = false
    })
end

return this
