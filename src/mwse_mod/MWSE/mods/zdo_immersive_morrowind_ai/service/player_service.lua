local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local util = require("zdo_immersive_morrowind_ai.common.util")
local actor_stats = require("zdo_immersive_morrowind_ai.common.actor_stats")
local ashfall_common = require("mer.ashfall.common.common")

local this = {}
this.player_book_name = "Journal"
this.player_book_content = ""

this.last_tooltip_name = ''
this.last_tooltip_show_ms = 0

function this.setup()
    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "get_local_player_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "get_local_player_response",
                    player_data = this.get_player_data()
                }
            })
        elseif e["data"]["type"] == "get_local_player_fast_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "get_local_player_fast_response",
                    player_data_fast = this.get_player_data_fast()
                }
            })
        elseif e["data"]["type"] == "update_player_book" then
            this.player_book_name = e["data"]["player_book_name"]
            this.player_book_content = e["data"]["player_book_content"]
        end
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.cellChanged, function(e)
        local cell = tes3.getPlayerCell()
        eventbus.produce_event_from_game({
            data = {
                type = "cell_changed",
                cell = {
                    id = cell.id,
                    name = cell.name or "",
                    display_name = cell.displayName or "",
                    is_exterior = cell.isOrBehavesAsExterior or false,
                    is_interior = cell.isInterior or false,
                    rest_is_illegal = cell.restingIsIllegal or false,
                    region = cell.region and {
                        id = cell.region.id,
                        name = cell.region.name
                    }
                }
            }
        })
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.bookGetText, function(e)
        if e.book.id == "bk_firmament" then
            e.book.name = this.player_book_name
            e.text = this.player_book_content
        end
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.uiObjectTooltip, function(e)
        if e.reference then
            local name = (e.reference.object and e.reference.object.name) or nil
            local now_ms = util.now_ms()
            if this.last_tooltip_name == name and (now_ms - this.last_tooltip_show_ms) < 1000 then
                return
            end

            local owner = tes3.getOwner({ reference = e.reference })
            eventbus.produce_event_from_game({
                data = {
                    type = "show_tooltip_for_ref",
                    tooltip = e.tooltip.text,
                    ref_id = e.reference.id,
                    object_type = e.reference.objectType,
                    name = name,
                    position = {
                        x = e.reference.position.x,
                        y = e.reference.position.y,
                        z = e.reference.position.z
                    },
                    owner = owner and util.get_actor_ref_from_reference(owner.reference)
                }
            })

            this.last_tooltip_name = name
            this.last_tooltip_show_ms = util.now_ms()
        elseif e.itemData then
            local name = e.object and e.object.name
            local now = util.now_ms()
            if this.last_tooltip_name == name and (now - this.last_tooltip_show_ms) < 1000 then
                return
            end

            eventbus.produce_event_from_game({
                data = {
                    type = "show_tooltip_for_inventory_item",
                    tooltip = e.tooltip.text,
                    name = name,
                    count = e.count,
                    object_type = e.itemData.name
                }
            })

            this.last_tooltip_name = name
            this.last_tooltip_show_ms = util.now_ms()
        end
    end, {
        unregisterOnLoad = false
    })

    local function convertInventoryTileListToNameList(tiles)
        local result = {}
        for _, v in pairs(tiles) do
            table.insert(result, v.item.name)
        end
        return result
    end
    event.register(tes3.event.barterOffer, function(e)
        eventbus.produce_event_from_game({
            data = {
                type = "barter_offer",
                offer = e.offer,
                value = e.value,
                success = e.success,
                merchant = util.get_actor_ref_from_mobile(e.mobile),
                buying = convertInventoryTileListToNameList(e.buying),
                selling = convertInventoryTileListToNameList(e.selling)
            }
        })
    end, {
        unregisterOnLoad = false
    })
    event.register("Ashfall:eatStew", function(e)
        local gold_before = tes3.getPlayerGold()

        local food_config = ashfall_common.staticConfigs.foodConfig
        local stew_types = e["data"]["stewLevels"]
        local stew_name = "Суп"

        for k, _ in pairs(stew_types) do
            for stewType, data in pairs(food_config.getStewBuffList()) do
                if stewType == k then
                    local spell = tes3.getObject(data.id)
                    local stew = data.notSoup and "Рагу" or "Суп"
                    stew_name = string.format("%s %s", spell.name, stew)
                    break
                end
            end
        end

        timer.start({
            duration = 0.1,
            type = timer.real,
            persist = false,
            callback = function(e)
                local gold_after = tes3.getPlayerGold()
                eventbus.produce_event_from_game({
                    data = {
                        type = "ashfall_eat_stew",
                        stew_name = stew_name,
                        cost = (gold_before - gold_after),
                        in_dialog = util.is_in_dialog_menu()
                    }
                })
            end
        })
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.crimeWitnessed, function(e)
        eventbus.produce_event_from_game({
            data = {
                type = "crime_witnessed",
                crime_type = e.type,
                value = e.value,
                position = {e.position.x, e.position.y, e.position.z},
                witness = util.get_actor_ref_from_mobile(e.witnessMobile),
                victim_faction = e.victimFaction and {
                    faction_id = e.victimFaction.id,
                    faction_name = e.victimFaction.name
                },
                victim_actor = e.victimMobile and util.get_actor_ref_from_mobile(e.victimMobile)
            }
        })
    end, {
        unregisterOnLoad = false
    })

    -- https://mwse.github.io/MWSE/events/activeMagicEffectIconsUpdated/ TODO
    -- event.register(tes3.event.activeMagicEffectIconsUpdated, function(e)
    -- end)

    event.register(tes3.event.collision, function(e)
        local target = e.target
        if not target then
            return
        end

        if target.mobile and target.mobile.objectType == tes3.objectType.mobileNPC then
            eventbus.produce_event_from_game({
                data = {
                    type = "player_collide",
                    other = util.get_actor_ref_from_reference(e.target)
                }
            })
        end
    end, {
        filter = ("PlayerSaveGame"):lower()
    }, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.equipped, function(e)
        if e.mobile ~= tes3.mobilePlayer then
            return
        end

        eventbus.produce_event_from_game({
            data = {
                type = "player_equip",
                item = {
                    id = e.item.id,
                    name = e.item.name
                }
            }
        })
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.unequipped, function(e)
        if e.mobile ~= tes3.mobilePlayer then
            return
        end

        eventbus.produce_event_from_game({
            data = {
                type = "player_unequip",
                item = {
                    id = e.item.id,
                    name = e.item.name
                }
            }
        })
    end, {
        unregisterOnLoad = false
    })
end

function this.get_player_data()
    local mobile = tes3.mobilePlayer
    local ndd = tes3.dataHandler.nonDynamicData

    local factions = {}
    for _, faction in pairs(ndd.factions) do
        if faction.playerExpelled or faction.playerJoined then
            table.insert(factions, {
                faction_id = faction.id,
                name = faction.name,
                player_joined = faction.playerJoined,
                player_expelled = faction.playerExpelled,
                player_rank = faction.playerRank,
                -- playerRankName = faction.playerRank >= 1 and faction.ranks[faction.playerRank].name or nil,
                player_reputation = faction.playerReputation
            })
        end
    end

    local hostiles = {}
    local npc_mobile_list = tes3.findActorsInProximity({
        reference = tes3.mobilePlayer.reference,
        range = (50 * 64)
    })
    for _, npc_mobile in pairs(npc_mobile_list) do
        for _, hostile_actor in pairs(npc_mobile.hostileActors) do
            if hostile_actor.reference.id == tes3.mobilePlayer.reference.id then
                table.insert(hostiles, util.get_actor_ref_from_mobile(npc_mobile))
            end
        end
    end

    return {
        ref_id = mobile.reference.id,
        name = mobile.object.name,
        female = mobile.object.female,
        race = {
            id = mobile.object.race.id,
            name = mobile.object.race.name
        },

        position = {
            x = tes3.mobilePlayer.reference.position.x,
            y = tes3.mobilePlayer.reference.position.y,
            z = tes3.mobilePlayer.reference.position.z
        },
        health_normalized = mobile.health.normalized * 100,
        hostiles = hostiles,

        cell = {
            id = tes3.getPlayerCell().id,
            name = tes3.getPlayerCell().displayName
        },

        equipped = util.get_equipped_items(mobile),
        nakedness = util.get_nakedness(mobile),
        in_dialog = util.is_in_dialog_menu(),

        weapon_drawn = mobile.weaponDrawn,
        weapon = (mobile and mobile.readiedWeapon and mobile.readiedWeapon.object) and {
            id = mobile.readiedWeapon.object.id,
            name = mobile.readiedWeapon.object.name
        } or nil,

        factions = factions,
        gold = tes3.getPlayerGold(),

        stats = actor_stats.get_actor_stats(tes3.mobilePlayer)
    }
end

function this.get_player_data_fast()
    local mobile = tes3.mobilePlayer

    return {
        position = {
            x = tes3.mobilePlayer.reference.position.x,
            y = tes3.mobilePlayer.reference.position.y,
            z = tes3.mobilePlayer.reference.position.z
        },
        health_normalized = mobile.health.normalized * 100,
        cell = {
            id = tes3.getPlayerCell().id,
            name = tes3.getPlayerCell().displayName
        },
        in_dialog = util.is_in_dialog_menu(),

        weapon_drawn = mobile.weaponDrawn,
        weapon = (mobile and mobile.readiedWeapon and mobile.readiedWeapon.object) and {
            id = mobile.readiedWeapon.object.id,
            name = mobile.readiedWeapon.object.name
        } or nil,

        gold = tes3.getPlayerGold()
    }
end

return this
