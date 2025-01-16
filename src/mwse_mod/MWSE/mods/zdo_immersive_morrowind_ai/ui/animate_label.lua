local this = {}

local util = require("zdo_immersive_morrowind_ai.common.util")

function this.reset_animate_label(label, expected_animation_id)
    if label == nil then
        return
    end

    if expected_animation_id == nil or label:getPropertyObject("animation_id") == expected_animation_id then
        label:setPropertyInt("animation_id", nil)
    end
end

function this.animate_label(req)
    local label = req["label"]
    local text = req["text"]
    local audio_duration_sec = req["audio_duration_sec"]
    local char_per_sec = req["char_per_sec"]
    local should_continue_fn = req["should_continue"]
    local on_end = req["on_end"]

    if label == nil then
        return
    end

    local printed_text = ""
    local leftText = text

    local new_animation_id = util.now_ms()
    label:setPropertyInt("animation_id", new_animation_id)

    if char_per_sec == nil then
        char_per_sec = 15
        if audio_duration_sec ~= nil and audio_duration_sec > 0 then
            char_per_sec = string.len(text) / audio_duration_sec
        end
    end

    timer.start({
        duration = 1.0 / char_per_sec,
        type = timer.real,
        iterations = -1,
        persist = false,
        callback = function(e)
            if label:getPropertyInt("animation_id") ~= new_animation_id then
                e.timer:cancel()

                if on_end ~= nil then
                    on_end(false)
                end
                return
            end

            if should_continue_fn ~= nil and not should_continue_fn() then
                e.timer:cancel()

                if on_end ~= nil then
                    this.reset_animate_label(label, new_animation_id)
                    on_end(false)
                end
                return
            end

            local next_char = string.sub(leftText, 1, 1)
            leftText = string.sub(leftText, 2, string.len(leftText))
            printed_text = printed_text .. next_char
            label.text = printed_text

            if string.len(leftText) == 0 then
                e.timer:cancel()

                this.reset_animate_label(label, new_animation_id)
                if on_end ~= nil then
                    on_end(true)
                end
            end
        end
    })
end

return this
