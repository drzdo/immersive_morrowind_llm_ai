local util = require("zdo_immersive_morrowind_ai.common.util")
local config = require("zdo_immersive_morrowind_ai.config")
local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local animate_label = require("zdo_immersive_morrowind_ai.ui.animate_label")

local this = {}

-- local actor = mobileActor.reference.object.baseObject --- @type tes3actor
-- local npc = mobileActor.reference.object.baseObject --- @type tes3npc
-- local npcInstance = mobileActor.reference.object --- @type tes3npc
this.last_mobile = nil

this.entered_dialog = false
this.show_topics = false
this.greet_text = nil
this.topics_list = {}
this.topics_map = {}
this.last_submitted_text = ''

local GUI_ID_MenuDialog = tes3ui.registerID("MenuDialog")
local GUI_ID_MenuDialog_a_topic = tes3ui.registerID("MenuDialog_a_topic")
local GUI_ID_MenuDialog_answer_block = tes3ui.registerID("MenuDialog_answer_block")
local GUI_ID_MenuDialog_hyper = tes3ui.registerID("MenuDialog_hyper")
local GUI_ID_MenuDialog_scroll_pane = tes3ui.registerID("MenuDialog_scroll_pane")
local GUI_ID_MenuDialog_topics_pane = tes3ui.registerID("MenuDialog_topics_pane")
local GUI_ID_PartScrollPane_pane = tes3ui.registerID("PartScrollPane_pane")

function this.create_textfield(menu_dialogue)
    if menu_dialogue == nil then
        return
    end

    util.debug("Chat was created")
    local chat = menu_dialogue:createTextInput({
        id = "immersive_morrowind_ai_chat",
        autoFocus = true,
        placeholderText = "(...)",
        text = ""
    })
    chat.wrapText = true
    chat.minWidth = 300

    chat:registerAfter("textUpdated", function(e)
        if not util.is_in_dialog_menu() then
            return
        end

        chat:forwardEvent(e)

        timer.delayOneFrame(function()
            chat.text = chat.rawText:gsub("/", "."):gsub("\\", ","):gsub("&", "?")
            chat:getTopLevelMenu():updateLayout()
        end, timer.real)
    end)
    chat:registerBefore("keyEnter", function()
        if not util.is_in_dialog_menu() then
            return
        end

        local text = chat.text
        chat.text = "|"

        local label = this.create_label()
        label.text = text
        label.color = {0.4, 0.9, 0.4}

        this.last_submitted_text = text
        eventbus.produce_event_from_game({
            data = {
                type = "dialog_text_submit",
                text = text,
                actor_ref = util.get_actor_ref_from_mobile(this.last_mobile)
            }
        })
    end)
end

function this.create_label()
    local menuDialogue = tes3ui.findMenu(GUI_ID_MenuDialog)
    if menuDialogue == nil then
        return
    end
    local textPane = menuDialogue:findChild(GUI_ID_MenuDialog_scroll_pane):findChild(GUI_ID_PartScrollPane_pane)
    if textPane == nil then
        return
    end
    local l = textPane:createLabel({
        text = ""
    })
    return l
end

function this.handle_voice_recognition_update(is_listening, text)
    local menu_dialogue = tes3ui.findMenu(GUI_ID_MenuDialog)
    if menu_dialogue == nil then
        return
    end

    local chat = menu_dialogue:findChild("immersive_morrowind_ai_chat")
    if chat == nil then
        return
    end

    if is_listening then
        chat.text = util.i18n("listening") .. text .. "|"
    else
        chat.text = text .. "|"
    end
end

function this.scroll_to_bottom()
    local menu_dialogue = tes3ui.findMenu(GUI_ID_MenuDialog)
    if menu_dialogue == nil then
        return
    end

    menu_dialogue:findChild(GUI_ID_MenuDialog_scroll_pane).widget.positionY = 30000
    menu_dialogue:findChild(GUI_ID_MenuDialog_scroll_pane):getTopLevelMenu():updateLayout()
end

function this.handle_actor_says(ref, text, reaction_text, audio_duration_sec)
    local menu_dialogue = tes3ui.findMenu(GUI_ID_MenuDialog)
    if menu_dialogue == nil then
        return
    end

    local is_player = ref.id == tes3.mobilePlayer.reference.id

    if ref.id == tes3.mobilePlayer.reference.id then
        if this.last_submitted_text ~= text then
            local label = this.create_label()
            label.color = {0.4, 0.9, 0.4}

            animate_label.animate_label({
                label = label,
                char_per_sec = 25,
                text = text,
                should_continue = function()
                    if util.is_in_dialog_menu() then
                        this.scroll_to_bottom()
                        return true
                    else
                        return false
                    end
                end
            })
        end
    elseif ref.id == this.last_mobile.reference.id then
        local label = this.create_label()

        animate_label.animate_label({
            label = label,
            audio_duration_sec = audio_duration_sec,
            text = text,
            should_continue = function()
                if util.is_in_dialog_menu() then
                    this.scroll_to_bottom()
                    return true
                else
                    return false
                end
            end,
            on_end = function()
                if reaction_text and string.len(reaction_text) > 0 then
                    local reaction_label = this.create_label()
                    if reaction_label ~= nil then
                        reaction_label.color = {0.9, 0.9, 0.4}
                        animate_label.animate_label({
                            label = reaction_label,
                            char_per_sec = 25,
                            text = reaction_text,
                            should_continue = function()
                                if util.is_in_dialog_menu() then
                                    this.scroll_to_bottom()
                                    return true
                                else
                                    return false
                                end
                            end
                        })
                    end
                end
            end
        })
    end
end

function this.update_topics(reason)
    util.debug("update_topics %s", reason)

    local menu_dialogue = tes3ui.findMenu(GUI_ID_MenuDialog)
    if menu_dialogue == nil then
        return
    end

    this.last_mobile = menu_dialogue:getPropertyObject("PartHyperText_actor") -- mobileActor
    if this.last_mobile == nil then
        return
    end

    local is_dialog_just_opened = false
    local chat = menu_dialogue:findChild("immersive_morrowind_ai_chat")
    if chat == nil then
        this.create_textfield(menu_dialogue)
        is_dialog_just_opened = true
    end

    local text_pane = menu_dialogue:findChild(GUI_ID_MenuDialog_scroll_pane):findChild(GUI_ID_PartScrollPane_pane)
    local topics_pane = menu_dialogue:findChild(GUI_ID_MenuDialog_topics_pane):findChild(GUI_ID_PartScrollPane_pane)

    -- Catch events from hyperlinks.
    for _, element in pairs(text_pane.children) do
        if (this.greet_text == nil and element.id == -243) then
            this.greet_text = element.text
        end

        if (element.id == GUI_ID_MenuDialog_hyper) then
            element:registerAfter("mouseClick", function()
                this.delayed_update_topics("click on hyperlink")
            end, {
                priority = -100500
            })
        end
    end

    -- Go through and update all the topics.
    this.topics_list = {}
    this.topics_map = {}
    for _, element in pairs(topics_pane.children) do
        -- We only care about topics in this list.
        if (element.id == GUI_ID_MenuDialog_a_topic) then
            local dialogue = element:getPropertyObject("PartHyperText_dialog") --- @type tes3dialogue
            local info = element:getPropertyObject("") or dialogue:getInfo({
                actor = this.last_mobile
            })

            -- Register an event so that we update when any topic is clicked.
            element:registerAfter("mouseClick", function()
                this.delayed_update_topics("click on topic in the list")
            end, {
                priority = -100500
            })

            local topic_data = {
                topic_text = element.text,
                topic_response = info.text

                -- dialogue = {
                --     id = dialogue.id,
                --     source_mod = dialogue.sourceMod,
                --     type = dialogue.type
                -- },

                -- info = {
                --     id = info.id,
                --     source_mod = info.sourceMod,
                --     text = info.text,
                --     type = info.type,
                --     cell = info.cell and info.cell.name or nil,
                --     disposition = info.disposition
                -- }
            }

            -- common.log("Register topic %s", element.text)
            this.topics_map[element.text] = {
                topic_data = topic_data,
                element = element
            }
            table.insert(this.topics_list, topic_data)

            element.visible = this.show_topics
        elseif element.id == -250 then
            -- Persuade
            element.visible = false
        else
            -- util.debug("UI element in topics list id=%s text=%s", element.id, element.text)
        end
    end

    util.debug("is_dialog_just_opened=%s", is_dialog_just_opened)

    if is_dialog_just_opened then
        eventbus.produce_event_from_game({
            data = {
                type = "dialog_open",
                npc_ref = util.get_actor_ref_from_mobile(this.last_mobile),
                greet_text = this.greet_text,
                topics = this.topics_list
            }
        })
    else
        eventbus.produce_event_from_game({
            data = {
                type = "dialog_update",
                npc_ref = util.get_actor_ref_from_mobile(this.last_mobile),
                greet_text = this.greet_text,
                topics = this.topics_list
            }
        })
    end
end

function this.on_activate(e)
    this.entered_dialog = true

    this.show_topics = not config.dialog_hide_topics
    if not this.show_topics and tes3.worldController.inputController:isAltDown() then
        this.show_topics = true
    end

    this.last_mobile = nil
    this.greet_text = nil
    this.topics_list = {}
    this.topics_map = {}

    local function firstPreUpdate(preUpdateEventData)
        assert(e.element:unregisterAfter("preUpdate", firstPreUpdate))
        this.update_topics("preUpdate")
    end
    e.element:registerAfter("preUpdate", firstPreUpdate)
end

function this.setup(first_time_loaded)
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "trigger_topic_in_dialog" then
            local topic = e["data"]["topic"]
            if this.topics_map[topic] == nil then
                util.logger:error("Cannot find topic %s in dialog", topic)
                return
            end
            this.topics_map[topic]["element"]:triggerEvent("mouseClick")
        end
    end, {
        unregisterOnLoad = false
    })

    event.register("uiActivated", this.on_activate, {
        filter = "MenuDialog"
    }, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.menuExit, function()
        if this.entered_dialog and not util.is_in_dialog_menu() then
            eventbus.produce_event_from_game({
                data = {
                    type = "dialog_close",
                    npc_ref = util.get_actor_ref_from_mobile(this.last_mobile)
                }
            })

            this.entered_dialog = false
            this.last_mobile = nil
            this.greet_text = nil
            this.topics_list = {}
            this.topics_map = {}
        end
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.topicAdded, function(e)
        if util.is_in_dialog_menu() then
            util.logger:debug("topicAdded %s", e.topic.id)

            this.delayed_update_topics("topicAdded")
        end
    end, {
        priority = -100500,
        unregisterOnLoad = false
    })
    event.register(tes3.event.postInfoResponse, function(e)
        util.logger:debug("postInfoResponse")
        -- util.logger:debug("\tcommand=%s", e.command)
        util.logger:debug("\treference=%s", e.reference.id)
        util.logger:debug("\tdialogue.id=%s", e.dialogue.id)
        util.logger:debug("\tinfo.id=%s", e.info.id)
        util.logger:debug("\tinfo.text=%s", e.info.text)

        if util.is_in_dialog_menu() then
            this.delayed_update_topics("postInfoResponse")
        end
    end, {
        priority = -100500,
        unregisterOnLoad = false
    })
end

this.delayed_update_topics_token = 1
function this.delayed_update_topics(reason)
    local token = this.delayed_update_topics_token + 1
    this.delayed_update_topics_token = token

    local function update_if_token_is_same()
        if this.delayed_update_topics_token == token and util.is_in_dialog_menu() then
            util.logger:debug("Delayed update topics")
            this.update_topics(reason)
        end
    end
    timer.delayOneFrame(update_if_token_is_same, timer.real)

    -- timer.start({
    --     duration = 0.5,
    --     type = timer.real,
    --     persist = false,
    --     callback = update_if_token_is_same
    -- })
end

return this
