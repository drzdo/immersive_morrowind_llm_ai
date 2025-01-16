local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local util = require("zdo_immersive_morrowind_ai.common.util")

local this = {}

function this.setup()
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "get_env_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "get_env_response",
                    env_data = this.get_env_data()
                }
            })
        end
    end, {
        unregisterOnLoad = false
    })
end

function this.get_env_data()
    local worldCtrl = tes3.worldController
    local weatherCtrl = tes3.worldController.weatherController

    local ashfall = nil
    if tes3.player.data and tes3.player.data.Ashfall then
        ashfall = {}
        for k, v in pairs(tes3.player.data.Ashfall) do
            if k ~= "cellBranchList" and k ~= "wateredCells" then
                ashfall[k] = v
            end
        end
    end

    return {
        current_weather = tes3.getCurrentWeather() and tes3.getCurrentWeather().name or "Clear",
        next_weather = weatherCtrl.nextWeather and weatherCtrl.nextWeather.name or nil,
        sunrise_hour = weatherCtrl.sunriseHour,
        sunset_hour = weatherCtrl.sunsetHour,
        masser_phase = weatherCtrl.masser.phase,
        secunda_phase = weatherCtrl.secunda.phase,

        ashfall = ashfall,

        current_day = worldCtrl.day.value,
        current_month = worldCtrl.month.value,
        current_year = worldCtrl.year.value,
        current_hour = worldCtrl.hour.value
    }
end

return this
