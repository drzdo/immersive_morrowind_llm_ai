local config = require("zdo_immersive_morrowind_ai.config")
local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local util = require("zdo_immersive_morrowind_ai.common.util")

local template = mwse.mcm.createTemplate("Zdo Immersive Morrowind")
template:saveOnClose("Zdo Immersive Morrowind", config)

local page = template:createSideBarPage()
page.label = "General Settings"
page.description = "Zdo Immersive Morrowind with AI " .. config.version
page.noScroll = false

local category = page:createCategory{
    label = "Server"
}

category:createTextField({
    label = "Server host",
    variable = mwse.mcm.createTableVariable({
        id = "server_host",
        table = config
    })
})
category:createTextField({
    label = "Server port",
    variable = mwse.mcm.createTableVariable({
        id = "server_port",
        table = config
    })
})
category:createYesNoButton({
    label = "Automatic reconnection to server (every 10 sec)",
    variable = mwse.mcm.createTableVariable {
        id = "auto_reconnect",
        table = config
    }
})
category:createButton{
    buttonText = "Manually connect to the server now",
    callback = function()
        util.log("User decided to connect manually")
        eventbus.connect()
    end,
    inGameOnly = true
}

category = page:createCategory{
    label = "UI General"
}

category:createYesNoButton({
    label = "Hide topics when opening a dialog",
    variable = mwse.mcm:createTableVariable{
        id = "dialog_hide_topics",
        table = config
    }
})

category = page:createCategory{
    label = "UI: HUD labels"
}

category:createSlider({
    label = "Hide NPC subtitles after this delay",
    min = 0,
    max = 15,
    step = 0.1,
    decimalPlaces = 1,
    variable = mwse.mcm:createTableVariable{
        id = "hud_npc_label_hide_after_sec",
        table = config
    }
})
category:createSlider({
    label = "Hide player subtitles after this delay",
    min = 0,
    max = 15,
    step = 0.1,
    decimalPlaces = 1,
    variable = mwse.mcm:createTableVariable{
        id = "hud_player_label_hide_after_sec",
        table = config
    }
})

-- category:createKeyBinder({
--     label = "Mark actor as target",
--     description = "Press this button to select NPC to talk to. Target no NPC to reset.",
--     allowCombinations = true,
--     variable = mwse.mcm.createTableVariable({
--         id = "target_npc_button",
--         table = config
--     })
-- })

category = page:createCategory{
    label = "Development"
}
category:createYesNoButton({
    label = "Print debug logs",
    variable = mwse.mcm:createTableVariable{
        id = "debug",
        table = config
    },
    callback = function(self)
        util.logger:setLogLevel(self.variable.value and "DEBUG" or "INFO")
    end
})

mwse.mcm.register(template)
