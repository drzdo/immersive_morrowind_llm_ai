local eventbus = require("zdo_immersive_morrowind_ai.common.eventbus")
local util = require("zdo_immersive_morrowind_ai.common.util")
local actor_stats = require("zdo_immersive_morrowind_ai.common.actor_stats")
local ashfall_common = require("mer.ashfall.common.common")
local ashfall_config = require("mer.ashfall.config").config

local this = {}
this.npc_ref_id_to_audio_pitch = {}
this.dropped_references = {}

this.npc_ref_id_to_speaking_info = {}
this.npc_ref_id_to_travel_info = {}

local pi = 3.1415
local skip_rot = 25.0 / 180.0 * pi

function this.getSignedAngleTo(ref, target)

    -- always positive nah
    -- local angle_abs = ref:getAngleTo(target)

    -- Morrowind's facing in 0 points to [0,1], and also inverted: [-pi, pi].
    local facing_fixed = -ref.facing + pi * 0.5

    local ref_facing_vec = tes3vector3.new(math.cos(facing_fixed), math.sin(facing_fixed), 0)
    local target_vec = target.position - ref.position
    local angle = math.atan2(ref_facing_vec.y, ref_facing_vec.x) - math.atan2(target_vec.y, target_vec.x)

    while angle < -pi do
        angle = angle + 2 * pi
    end
    while angle > pi do
        angle = angle - 2 * pi
    end

    -- util.debug("angle=%f angle_abs=%f", angle, angle_abs)
    -- Converting back to Morrowind's coordinate system.

    return angle
end

function this.lerp_to_face_another_ref(ref, target, dt_sec)
    if ref == tes3.mobilePlayer.reference then
        return
    end
    local mobile = ref.mobile
    if mobile == nil then
        return
    end

    mobile:overrideHeadTrackingThisFrame(target)

    if mobile.isRunning or mobile.isWalking then
        return
    end

    local package = mobile.aiPlanner and mobile.aiPlanner:getActivePackage()
    if package and (package.isMoving or mobile.isWalking or mobile.isTurningLeft or mobile.isTurningRight)  then
        return
    end

    -- ref = tes3ui.getConsoleReference(); target = tes3.mobilePlayer.reference; npc_service = require("zdo_immersive_morrowind_ai.service.npc_service")
    -- ref.facing = ref.facing + npc_service.getSignedAngleTo(ref, target)

    local rotation_speed_rad_per_sec = pi * 2

    -- always positive nah
    -- local angle_abs = ref:getAngleTo(target)
    local angle = this.getSignedAngleTo(ref, target)
    if math.abs(angle) < skip_rot then
        return
    end

    local old_facing = ref.facing
    local target_facing = old_facing + angle

    local new_facing = old_facing + angle * ((dt_sec or 1.0 / 30.0) * rotation_speed_rad_per_sec)

    local diff_to_target_for_old_facing = math.abs(old_facing - target_facing)
    local diff_to_target_for_new_facing = math.abs(new_facing - target_facing)
    local should_set_exact = diff_to_target_for_new_facing > diff_to_target_for_old_facing
    if should_set_exact then
        new_facing = target_facing
    end
    ref.facing = new_facing
end

function this.spawn_single_item(item, position)
    local spawn_pos = tes3vector3.new(position.x + math.random() * 16, position.y + math.random() * 16, position.z)

    local hit_result = tes3.rayTest({
        position = spawn_pos + tes3vector3.new(0, 0, 128),
        direction = tes3vector3.new(0, 0, -1)
    })
    if hit_result and hit_result.intersection then
        spawn_pos = hit_result.intersection
    end

    local n = tes3.createReference({
        object = item,
        position = spawn_pos,
        orientation = {0, 0, 1},
        cell = tes3.mobilePlayer.cell
    })
    return n
end

function this.spawn_item(ref, target, data)
    local position = ref.position
    local facing_fixed = ref.facing + this.getSignedAngleTo(ref, target)
    facing_fixed = -facing_fixed + pi * 0.5
    local dv = tes3vector3.new(math.cos(facing_fixed), math.sin(facing_fixed), 0)
    local result_position = position + dv * 64

    tes3.playItemPickupSound({
        reference = ref,
        item = data["item"],
        pickup = false
    })

    if data["item"] == "gold_001" then
        local gold_left = data["count"]

        while gold_left > 0 do
            local item = "gold_001"
            local dec = 1

            if gold_left >= 100 then
                item = "gold_100"
                dec = 100
            elseif gold_left >= 25 then
                item = "gold_025"
                dec = 25
            elseif gold_left >= 10 then
                item = "gold_010"
                dec = 10
            elseif gold_left >= 5 then
                item = "gold_005"
                dec = 5
            end

            gold_left = gold_left - dec

            this.spawn_single_item(item, result_position)
        end
    else
        local i = 0
        while i < data["count"] do
            local n = this.spawn_single_item(data["item"], result_position)

            if n ~= nil and data["water_amount"] then
                n.data["waterAmount"] = data["water_amount"]
            end

            i = i + 1
        end
    end
end

function this.check_is_target_to_activate(target_ref, dropped_item_id, target_pos)
    if target_ref == nil then
        return nil
    end

    if (dropped_item_id and target_ref.data and target_ref.data["zdo_ai_dropped_item_id"] == dropped_item_id) then
        util.log("Found target ref matches by dropped_item_id")
        return target_ref
    end

    if (target_pos) then
        local ref_pos = target_ref.position;

        local dx = math.abs(ref_pos.x - target_pos[1])
        local dy = math.abs(ref_pos.y - target_pos[2])
        local dz = math.abs(ref_pos.z - target_pos[3])
        if dx < 2 and dy < 2 and dz < 2 then
            util.log("Found target ref matches by target_pos")
            return target_ref
        end
    end

    return nil
end

function this.setup(first_time_loaded)
    tes3.findGMST("iGreetDistanceMultiplier").value = 0

    this.npc_ref_id_to_audio_pitch = {}
    this.dropped_references = {}

    if first_time_loaded then
        event.register(tes3.event.simulate, function(e)
            for ref_id, info in pairs(this.npc_ref_id_to_speaking_info) do
                local ref = info["ref"]
                local target = info["target"]

                if ref ~= tes3.mobilePlayer.reference and this.npc_ref_id_to_travel_info[ref.id] == nil then
                    this.lerp_to_face_another_ref(ref, target, e.delta)
                end
            end
        end)
    end

    timer.start({
        duration = 0.5,
        type = timer.real,
        iterations = -1,
        persist = false,
        callback = function(e)
            local now = util.now_ms()

            for ref_id, info in pairs(this.npc_ref_id_to_speaking_info) do
                if info["expire_at_ms"] < now or tes3.getReference(ref_id).object.isDead then
                    this.npc_ref_id_to_speaking_info[ref_id] = nil
                end
            end

            for ref_id, info in pairs(this.npc_ref_id_to_travel_info) do
                local ref = info["ref"]
                if info["expire_at_ms"] < now then
                    this.npc_ref_id_to_travel_info[ref_id] = nil
                    tes3.setAIWander({
                        reference = ref,
                        idles = {1, 1, 1, 1, 1, 1, 1, 1}
                    })
                else
                    local destination = info["destination"]

                    local package = ref.mobile.aiPlanner and ref.mobile.aiPlanner:getActivePackage()
                    if package and package.type == tes3.aiPackage.travel then
                        local distance = ref.position:distanceManhattan(destination)
                        local distance_to_stop = 64 * 5
                        if distance < distance_to_stop then
                            this.npc_ref_id_to_travel_info[ref_id] = nil
                            tes3.setAIWander({
                                reference = ref,
                                idles = {1, 1, 1, 1, 1, 1, 1, 1}
                            })
                        end
                    end
                end
            end
        end
    })

    if not first_time_loaded then
        return
    end

    event.register("zdo_ai_rpg:event_from_server", function(e)
        if e["data"]["type"] == "get_npc_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "get_npc_response",
                    npc_data = this.get_npc_data(e["data"]["npc_ref_id"])
                }
            })
        elseif e["data"]["type"] == "npc_say_mp3" then
            local ref = tes3.getReference(e["data"]["npc_ref_id"])
            this.npc_ref_id_to_audio_pitch[ref.id] = e["data"]["pitch"]

            tes3.removeSound({
                reference = ref
            })
            tes3.say({
                reference = ref,
                soundPath = e["data"]["file_path"],
                pitch = e["data"]["pitch"] or 1.0
            })

            local target_ref_id = e["data"]["target_ref_id"]
            if target_ref_id then
                local generation = util.now_ms()
                local target = tes3.getReference(target_ref_id)

                this.npc_ref_id_to_speaking_info[ref.id] = {
                    generation = generation,
                    expire_at_ms = util.now_ms() + e["data"]["duration_sec"] * 1000,
                    ref = ref,
                    target = target
                }

                this.npc_ref_id_to_speaking_info[target_ref_id] = {
                    generation = generation,
                    expire_at_ms = util.now_ms() + e["data"]["duration_sec"] * 1000,
                    ref = target,
                    target = ref
                }
            end
        elseif e["data"]["type"] == "npc_remove_sound" then
            local ref = tes3.getReference(e["data"]["npc_ref_id"])
            tes3.removeSound({
                reference = ref
            })

            local v = this.npc_ref_id_to_speaking_info[ref.id]
            if v ~= nil then
                this.npc_ref_id_to_speaking_info[ref.id] = nil

                local target_ref_id = v["target"].id
                local v2 = this.npc_ref_id_to_speaking_info[target_ref_id]
                if v2 ~= nil and v2["generation"] == v["generation"] then
                    this.npc_ref_id_to_speaking_info[target_ref_id] = nil
                end
            end
        elseif e["data"]["type"] == "turn_actors_to" then
            local target = tes3.getReference(e["data"]["target_ref_id"])
            if target then
                local generation = util.now_ms()
                for _, actor_ref_id in pairs(e["data"]["actor_ref_ids"]) do
                    local ref = tes3.getReference(actor_ref_id)
                    if ref and ref ~= tes3.mobilePlayer.reference then
                        this.npc_ref_id_to_speaking_info[ref.id] = {
                            generation = generation,
                            expire_at_ms = util.now_ms() + 30000,
                            ref = ref,
                            target = target
                        }
                    end
                end
            end
        elseif e["data"]["type"] == "npc_start_combat" then
            local attacker = tes3.getReference(e["data"]["npc_ref_id"])
            local target = tes3.getReference(e["data"]["target_ref_id"])
            attacker.mobile:startCombat(target.mobile)
        elseif e["data"]["type"] == "npc_stop_combat" then
            local attacker = tes3.getReference(e["data"]["npc_ref_id"])
            attacker.mobile:stopCombat(true)
        elseif e["data"]["type"] == "npc_follow" then
            tes3.setAIFollow({
                reference = tes3.getReference(e["data"]["npc_ref_id"]),
                target = tes3.getReference(e["data"]["target_ref_id"]),
                duration_hours = e["data"]["duration_hours"]
            })
        elseif e["data"]["type"] == "npc_travel" then
            local ref = tes3.getReference(e["data"]["npc_ref_id"])

            if ref and ref.mobile and ref.mobile.combatSession then
                util.log("Skip come command because %s in combat", ref)
                return
            end

            local target = tes3.getReference(e["data"]["target_ref_id"])
            local target_pos = e["data"]["target_pos"]
            local final_target_position = (target and target.position) or tes3vector3.new(target_pos[1], target_pos[2], target_pos[3])
            local distance = ref.position:distanceManhattan(final_target_position)
            if distance > (64 * 1) then
                this.npc_ref_id_to_travel_info[e["data"]["npc_ref_id"]] = {
                    expire_at_ms = util.now_ms() + 30000,
                    ref = ref,
                    target = target,
                    destination = final_target_position
                }

                tes3.setAITravel({
                    reference = ref,
                    destination = final_target_position
                })
            end
        elseif e["data"]["type"] == "npc_activate" then
            local target_ref = nil

            util.log("Activating...")
            if e["data"]["dropped_item_id"] or e["data"]["target_pos"] then
                local target_ref_probably = tes3.getReference(e["data"]["target_ref_id"])
                -- util.log("Found probable target ref %s", target_ref_probably)

                if this.check_is_target_to_activate(target_ref_probably, e["data"]["dropped_item_id"], e["data"]["target_pos"]) then
                    target_ref = target_ref_probably
                end

                if target_ref == nil then
                    util.log("Found probable target ref does not match")

                    if target_ref == nil then
                        local ref_in_list = tes3.mobilePlayer.cell.activators.head
                        while ref_in_list ~= nil do
                            if ref_in_list.id:lower() == e["data"]["target_ref_id"]:lower() then
                                if this.check_is_target_to_activate(ref_in_list, e["data"]["dropped_item_id"], e["data"]["target_pos"]) then
                                    util.log("Found target ref via full iteration in activators")
                                    target_ref = ref_in_list
                                    break
                                end
                            end

                            ref_in_list = ref_in_list.nextNode
                        end
                    end

                    if target_ref == nil then
                        local ref_in_list = tes3.mobilePlayer.cell.statics.head
                        while ref_in_list ~= nil do
                            if ref_in_list.id:lower() == e["data"]["target_ref_id"]:lower() then
                                if this.check_is_target_to_activate(ref_in_list, e["data"]["dropped_item_id"], e["data"]["target_pos"]) then
                                    util.log("Found target ref via full iteration in activators")
                                    target_ref = ref_in_list
                                    break
                                end
                            end

                            ref_in_list = ref_in_list.nextNode
                        end
                    end
                end
            end

            if target_ref == nil then
                util.log("looking for target_ref just via ref ID")
                target_ref = tes3.getReference(e["data"]["target_ref_id"])
            end
            if target_ref == nil then
                util.log("Didn't find target id, skip")
                return
            end

            local actor_ref = tes3.getReference(e["data"]["npc_ref_id"])
            util.log("Actor who will be activating is %s", actor_ref)
            if target_ref.object then
                tes3.playItemPickupSound({
                    reference = actor_ref,
                    item = target_ref.object.id,
                    pickup = true
                })
            end
            -- util.log("adding item %s to actor is %s", target_ref.object.id, actor_ref)
            tes3.setAIActivate({
                reference = actor_ref,
                target = target_ref
            })
            -- tes3.addItem({
            --     reference = actor_ref,
            --     item = target_ref.object.id,
            --     count = 1
            -- })
            -- target_ref:disable()
            util.log("item added, done")

        elseif e["data"]["type"] == "npc_wander" then
            tes3.setAIWander({
                reference = tes3.getReference(e["data"]["npc_ref_id"]),
                idles = {1, 1, 1, 1, 1, 1, 1, 1},
                range = e["data"]["range"] or 1000
            })
        elseif e["data"]["type"] == "trigger_crime" then
            tes3.triggerCrime({
                forceDetection = true,
                value = e["data"]["crime_value"],
                type = e["data"]["crime_type"]
            })
        elseif e["data"]["type"] == "transfer_item" then
            tes3.transferItem({
                from = tes3.getReference(e["data"]["from_ref_id"]),
                to = tes3.getReference(e["data"]["to_ref_id"]),
                item = e["data"]["item"],
                count = e["data"]["count"]
            })
        elseif e["data"]["type"] == "npc_spawn_item" then
            local ref = tes3.getReference(e["data"]["npc_ref_id"])

            this.spawn_item(ref, tes3.mobilePlayer.reference, e["data"])
        elseif e["data"]["type"] == "npc_drop_item" then
            tes3.dropItem({
                reference = tes3.getReference(e["data"]["npc_ref_id"]),
                item = e["data"]["item"],
                count = e["data"]["count"],
                matchNoItemData = true
            })
        elseif e["data"]["type"] == "is_ref_valid_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "is_ref_valid_response",
                    is_valid = tes3.getReference(e["data"]["ref_id"]) ~= nil
                }
            })
        elseif e["data"]["type"] == "npc_set_pitch" then
            this.npc_ref_id_to_audio_pitch[e["data"]["npc_ref_id"]] = e["data"]["pitch"]
        elseif e["data"]["type"] == "get_item_count_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "get_item_count_response",
                    count = tes3.getItemCount({
                        reference = tes3.getReference(e["data"]["ref_id"]),
                        item = e["data"]["item"]
                    })
                }
            })
        elseif e["data"]["type"] == "line_of_sight_request" then
            eventbus.produce_response_event(e, {
                data = {
                    type = "line_of_sight_response",
                    can_see = tes3.testLineOfSight({
                        reference1 = tes3.mobilePlayer.reference,
                        height1 = 2,
                        reference2 = tes3.getReference(e["data"]["npc_ref_id"]),
                        height2 = 2
                    })
                }
            })
        elseif e["data"]["type"] == "change_disposition" then
            tes3.modDisposition({
                reference = tes3.getReference(e["data"]["npc_ref_id"]),
                value = e["data"]["value"],
                temporary = false
            })
        elseif e["data"]["type"] == "get_actors_nearby_request" then
            local base_actor_ref = tes3.mobilePlayer.reference

            if e["data"]["actor_ref_id"] then
                base_actor_ref = tes3.getReference(e["data"]["actor_ref_id"])
            end

            local mobile_list = tes3.findActorsInProximity({
                reference = base_actor_ref,
                range = e["data"]["radius_ingame"] or (30 * 64)
            })
            local actor_ref_list = {}
            for _, v in pairs(mobile_list) do
                if v ~= base_actor_ref.mobile then
                    local actor_ref = util.get_actor_ref_from_mobile(v)
                    if actor_ref ~= nil then
                        local actor = {
                            actor_ref = actor_ref,
                            distance_ingame = v.playerDistance
                        }
                        if base_actor_ref ~= tes3.mobilePlayer.reference then
                            actor["distance_ingame"] = base_actor_ref.position:distance(actor_ref.position)
                        end

                        if e["data"]["test_line_of_sight"] then
                            actor["can_see"] = tes3.testLineOfSight({
                                reference1 = v.reference,
                                height1 = 2,
                                reference2 = base_actor_ref,
                                height2 = 2
                            })
                        end

                        table.insert(actor_ref_list, actor)
                    end
                end
            end

            eventbus.produce_response_event(e, {
                data = {
                    type = "get_actors_nearby_response",
                    actors = actor_ref_list
                }
            })
        end
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.itemDropped, function(e)
        if e.reference == nil then
            return
        end
        if e.reference.data == nil then
            return
        end

        e.reference.data["zdo_ai_dropped_item_id"] = util.now_ms()

        table.insert(this.dropped_references, {
            ref_id = e.reference.id,
            zdo_ai_dropped_item_id = e.reference.data["zdo_ai_dropped_item_id"]
        })
        util.logger:info("Register item dropped %s / %d", e.reference.id, e.reference.data["zdo_ai_dropped_item_id"])

        eventbus.produce_event_from_game({
            data = {
                type = "item_dropped",
                ref_id = e.reference.id,
                object_id = e.reference.object.id,
                name = e.reference.object.name,
                dropped_item_id = e.reference.data["zdo_ai_dropped_item_id"]
            }
        })
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.activate, function(e)
        if e.target == nil then
            return
        end

        local index = -1
        for i, v in pairs(this.dropped_references) do
            if e.target.data and e.target.data["zdo_ai_dropped_item_id"] == v["zdo_ai_dropped_item_id"] then
                index = i
                break
            end
        end

        if index >= 1 then
            local v = this.dropped_references[index]
            util.logger:info(
                "Unregister item dropped ref_id=%s dropped_item_id=%d index=%d",
                v["ref_id"], v["zdo_ai_dropped_item_id"], index
            )
            table.remove(this.dropped_references, index)

            if e.activator and e.activator.id ~= tes3.mobilePlayer.reference.id then
                tes3.setAIWander({
                    reference = e.activator,
                    idles = {1, 1, 1, 1, 1, 1, 1, 1},
                    range = 64 * 0
                })
            end
        end

        eventbus.produce_event_from_game({
            data = {
                type = "activated",
                activator_actor = util.get_actor_ref_from_reference(e.activator),
                target_actor = util.get_actor_ref_from_reference(e.target),
                target_ref_id = e.target.id,
                dropped_item_id = e.target.data and e.target.data["zdo_ai_dropped_item_id"]
            }
        })
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.mobileActivated, function(e)
        if e.mobile.objectType == tes3.objectType.mobileNPC then
            eventbus.produce_event_from_game({
                data = {
                    type = "npc_mobile_activated",
                    actor = util.get_actor_ref_from_reference(e.reference)
                }
            })
        end
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.mobileDeactivated, function(e)
        if e.mobile.objectType == tes3.objectType.mobileNPC then
            eventbus.produce_event_from_game({
                data = {
                    type = "npc_mobile_deactivated",
                    actor = util.get_actor_ref_from_reference(e.reference)
                }
            })
        end
    end, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.damaged, function(e)
        if e.mobile.objectType == tes3.objectType.mobileNPC and e.killingBlow then
            eventbus.produce_event_from_game({
                data = {
                    type = "npc_death",
                    actor = util.get_actor_ref_from_reference(e.reference),
                    killer = util.get_actor_ref_from_reference(e.attackerReference)
                }
            })

            -- timer.start({
            --     duration = 1.0,
            --     type = timer.real,
            --     persist = false,
            --     callback = function(e)
            --         tes3.removeSound({
            --             reference = e.mobile.reference
            --         })
            --         -- TODO remove subtitle
            --     end
            -- })
        end
    end, {
        unregisterOnLoad = false
    })

    event.register(tes3.event.combatStarted, function(e)
        eventbus.produce_event_from_game({
            data = {
                type = "combat_started",
                actor = util.get_actor_ref_from_mobile(e.actor),
                target = util.get_actor_ref_from_mobile(e.target)
            }
        })
    end)
    event.register(tes3.event.combatStopped, function(e)
        eventbus.produce_event_from_game({
            data = {
                type = "combat_stopped",
                actor = util.get_actor_ref_from_mobile(e.actor)
            }
        })
    end)

    local function updatePitch(e)
        -- util.debug("updatePitch ref=%s pitch=%f", e.reference, e.pitch)
        if e.reference and e.reference.mobile and e.reference.mobile.objectType == tes3.objectType.mobileNPC then
            e.pitch = this.npc_ref_id_to_audio_pitch[e.reference.id] or 1.0
            -- e.pitch = 0.9
            util.debug("Getting pitch for %s -> %f", e.reference.id, e.pitch)
        end
    end
    event.register(tes3.event.addSound, updatePitch, {
        unregisterOnLoad = false
    })
    event.register(tes3.event.addTempSound, updatePitch, {
        unregisterOnLoad = false
    })
end

function this.ashfall_getStewCost(merchantObj)
    local dispMulti = 3.0
    local personalityMulti = 2.0

    local disposition = math.min(merchantObj.disposition, 100)
    local personality = math.min(tes3.mobilePlayer.personality.current, 100)
    local dispEffect = math.remap(disposition, 0, 100, dispMulti, 1.0)
    local personalityEffect = math.remap(personality, 0, 100, personalityMulti, 1.0)
    return math.floor(ashfall_config.stewBaseCost * dispEffect * personalityEffect)
end

function this.get_npc_data(ref_id)
    local ref = tes3.getReference(ref_id)
    if ref == nil then
        util.log("Cannot find ref %s", ref_id)
        return nil
    end

    local npc_mobile = ref.mobile --- @type tes3mobileNPC
    local npc = ref.object.baseObject --- @type tes3npc
    local npc_instance = ref.object --- @type tes3npcInstance

    local in_active_cell = false
    if npc_mobile ~= nil then
        local active_cells = tes3.getActiveCells()
        for _, cell in pairs(active_cells) do
            if cell == npc_mobile.cell then
                in_active_cell = true
                break
            end
        end
    end

    local hostiles = {}
    local friendlies = {}
    if npc_mobile ~= nil then
        for _, a in pairs(npc_mobile.hostileActors) do
            table.insert(hostiles, util.get_actor_ref_from_mobile(a))
        end

        for _, a in pairs(npc_mobile.friendlyActors) do
            if a.reference.id ~= npc_mobile.reference.id then
                table.insert(friendlies, util.get_actor_ref_from_mobile(a))
            end
        end
    end

    local travel_destinations = nil
    if npc.aiConfig.travelDestinations ~= nil then
        travel_destinations = {}
        for _, d in pairs(npc.aiConfig.travelDestinations) do
            table.insert(travel_destinations, d.cell.name)
        end
    end

    local following = nil
    if npc_mobile ~= nil and npc_mobile.aiPlanner then
        local package = npc_mobile.aiPlanner:getActivePackage()
        if package ~= nil and package.targetActor ~= nil then
            following = util.get_actor_ref_from_reference(package.targetActor.reference)
        end
    end

    local is_ashfall_inkeeper = ashfall_common.helper.isInnkeeper(ref) or false

    return {
        ref_id = ref_id,
        name = (ref.data and ref.data["jamrockRename"]) or npc.name,
        health_normalized = npc_mobile and npc_mobile.health.normalized * 100 or 100,
        has_mobile = npc_mobile ~= nil,

        class_id = npc.class and npc.class.id,
        class_name = npc.class and npc.class.name,
        female = npc.female,
        race = npc.race and {
            id = npc.race.id,
            name = npc.race.name
        },

        faction = npc.faction and {
            faction_id = npc.faction.id,
            faction_name = npc.faction.name,
            npc_rank = npc.factionRank
        } or nil,

        player_distance = npc_mobile and npc_mobile.playerDistance or -1,
        disposition = npc_instance.disposition,

        cell = {
            id = ref.cell.id,
            name = ref.cell.name
        },
        npc_in_active_cell = in_active_cell,

        in_combat = npc_mobile and npc_mobile.inCombat or false,
        is_diseased = npc_mobile and npc_mobile.isDiseased or false,
        is_dead = npc_mobile and npc_mobile.isDead or false,

        is_ashfall_innkeeper = is_ashfall_inkeeper,
        ashfall_stew_cost = is_ashfall_inkeeper and this.ashfall_getStewCost(npc_instance) or nil,

        hostiles = hostiles,
        friendlies = friendlies,

        equipped = npc_mobile and util.get_equipped_items(npc_mobile) or {},
        nakedness = npc_mobile and util.get_nakedness(npc_mobile) or {},

        weapon_drawn = npc_mobile and npc_mobile.weaponDrawn or false,
        weapon = (npc_mobile and npc_mobile.readiedWeapon and npc_mobile.readiedWeapon.object) and {
            id = npc_mobile.readiedWeapon.object.id,
            name = npc_mobile.readiedWeapon.object.name
        } or nil,

        following = following,
        position = {
            x = ref.position.x,
            y = ref.position.y,
            z = ref.position.z
        },
        ai_config = npc.aiConfig and {
            offers_bartering = npc.aiConfig.offersBartering,
            offers_enchanting = npc.aiConfig.offersEnchanting,
            offers_repairs = npc.aiConfig.offersRepairs,
            offers_spellmaking = npc.aiConfig.offersSpellmaking,
            offers_spells = npc.aiConfig.offersSpells,
            offers_training = npc.aiConfig.offersTraining,
            travel_destinations = travel_destinations,

            barters_alchemy = npc.aiConfig.bartersAlchemy,
            barters_apparatus = npc.aiConfig.bartersApparatus,
            barters_armor = npc.aiConfig.bartersArmor,
            barters_books = npc.aiConfig.bartersBooks,
            barters_clothing = npc.aiConfig.bartersClothing,
            barters_enchanted_items = npc.aiConfig.bartersEnchantedItems,
            barters_ingredients = npc.aiConfig.bartersIngredients,
            barters_lights = npc.aiConfig.bartersLights,
            barters_lockpicks = npc.aiConfig.bartersLockpicks,
            barters_misc_items = npc.aiConfig.bartersMiscItems,
            barters_probes = npc.aiConfig.bartersProbes,
            barters_repair_tools = npc.aiConfig.bartersRepairTools,
            barters_weapons = npc.aiConfig.bartersWeapons
        },

        stats = ref.mobile.objectType == tes3.objectType.mobileNPC and actor_stats.get_actor_stats(npc_mobile) or nil,
        gold = tes3.getItemCount({
            reference = ref,
            item = "gold_001"
        })
    }
end

return this
