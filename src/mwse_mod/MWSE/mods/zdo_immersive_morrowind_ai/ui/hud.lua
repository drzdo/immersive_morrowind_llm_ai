local this = {}

local util = require("zdo_immersive_morrowind_ai.common.util")
local config = require("zdo_immersive_morrowind_ai.config")
local animate_label = require("zdo_immersive_morrowind_ai.ui.animate_label")

function this.setup()
    -- tes3ui.findMenu(tes3ui.registerID("MenuMulti")):findChild("zdoaihud_root")

    this._subscribeForEvents()
end

function this._subscribeForEvents()
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "stt_start_listening" then
        elseif e["data"]["type"] == "npc_remove_sound" then
            local ref_id = e["data"]["npc_ref_id"]

            for _, label in pairs(this.labels) do
                if label:getPropertyObject("actor_ref") and label:getPropertyObject("actor_ref").id == ref_id then
                    animate_label.reset_animate_label(label)

                    label.text = label.text .. " <...>"
                    this._clear_after_delay(label, config.hud_npc_label_hide_after_sec)
                    label:setPropertyObject("actor_ref", tes3.mobilePlayer.reference)
                end
            end
        end
    end, {
        unregisterOnLoad = false
    })

    local function update_visibility()
        this.root.visible = not util.is_in_dialog_menu()
    end
    event.register(tes3.event.menuEnter, update_visibility, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.menuExit, update_visibility, {
        unregisterOnLoad = false
    })
end

function this.create_hud()
    local menu = tes3ui.findMenu(tes3ui.registerID("MenuMulti"))

    this.root = menu:createBlock({
        id = "zdoaihud_root"
    })
    this.root.flowDirection = "top_to_bottom"
    this.root.paddingTop = 6
    this.root.paddingBottom = 12
    this.root.paddingLeft = 6
    this.root.paddingRight = 6
    this.root.autoWidth = false
    this.root.width = menu.width * 0.5
    this.root.autoHeight = true
    this.root.widthProportional = 1.0
    this.root.childAlignX = 0
    this.root.childAlignY = 1

    this.root.ignoreLayoutX = true
    this.root.ignoreLayoutY = true
    this.root.absolutePosAlignX = 0.5
    this.root.absolutePosAlignY = 1

    this.labels = {}
    this.next_label_index = 1
    this.total_labels = 10

    local i = 1
    while i <= this.total_labels do
        local label = this.root:createLabel({
            id = string.format("l%d", i),
            text = ""
        })
        label.wrapText = true
        label.justifyText = 'center'

        table.insert(this.labels, label)
        i = i + 1
    end

    this.label_stt = this.root:createLabel({
        id = "lstt",
        text = ""
    })
    this.label_stt.wrapText = true
    this.label_stt.justifyText = 'center'

    this.default_color = this.label_stt.color
    this.label_stt.color = {0.4, 0.9, 0.4}
end

function this._clear_after_delay(label, delay)
    local text = label.text .. ""

    timer.start({
        duration = delay,
        type = timer.real,
        persist = false,
        callback = function(e)
            if label.text == text then
                label.text = ""
                label:setPropertyObject("actor_ref", tes3.mobilePlayer.reference)
            end
        end
    })
end

function this.get_next_label()
    local label = this.labels[this.next_label_index]

    this.next_label_index = this.next_label_index + 1
    if this.next_label_index > this.total_labels then
        this.next_label_index = 1
    end

    if label == nil then
        util.logger:error("label is nil")
        return
    end
    if this.label_stt == nil then
        util.logger:error("label_stt is nil")
        return
    end

    label:reorder({
        before = this.label_stt
    })
    -- this.root:reorderChildren({
    --     insertBefore = this.label_stt,
    --     moveFrom = label,
    --     count = 1
    -- })

    return label
end

function this.handle_voice_recognition_update(is_listening, text)
    animate_label.reset_animate_label(this.label_stt)

    if is_listening then
        this.label_stt.text = util.i18n("listening") .. text
    else
        this.label_stt.text = text
        this._clear_after_delay(this.label_stt, config.hud_player_label_hide_after_sec)
    end
end

function this.handle_actor_says(ref, text, reaction_text, audio_duration_sec)
    if ref == tes3.mobilePlayer.reference then
        return
    end

    local text_to_show = text

    local label_for_text = this.get_next_label()
    label_for_text.color = this.default_color
    label_for_text:setPropertyObject("actor_ref", ref)

    local label_for_reaction = nil
    if reaction_text and string.len(reaction_text) > 0 then
        label_for_reaction = this.get_next_label()
        label_for_reaction.color = {0.9, 0.9, 0.4}
        label_for_reaction:setPropertyObject("actor_ref", ref)
    end

    animate_label.reset_animate_label(label_for_text)
    animate_label.reset_animate_label(label_for_reaction)

    animate_label.animate_label({
        label = label_for_text,
        text = text_to_show,
        audio_duration_sec = audio_duration_sec,
        should_continue = nil,
        on_end = function(success)
            if not success then
                return
            end

            if reaction_text and string.len(reaction_text) > 0 then
                animate_label.animate_label({
                    label = label_for_reaction,
                    char_per_sec = 25,
                    text = reaction_text,
                    should_continue = nil,
                    on_end = function(success)
                        if not success then
                            return
                        end

                        this._clear_after_delay(label_for_reaction, config.hud_npc_label_hide_after_sec)

                        if label_for_text.text == text_to_show then
                            this._clear_after_delay(label_for_text, config.hud_npc_label_hide_after_sec)
                        end
                    end
                })
            else
                this._clear_after_delay(label_for_text, config.hud_npc_label_hide_after_sec)
            end
        end
    })
end

return this
