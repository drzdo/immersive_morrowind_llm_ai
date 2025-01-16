local this = {}

local i18n = mwse.loadTranslations("zdo_immersive_morrowind_ai")
local config = require("zdo_immersive_morrowind_ai.config")

local logger = require("logging.logger")
this.logger = logger.new {
    name = "Zdo Immersive Morrowind",
    logLevel = config.debug and 'DEBUG' or 'INFO',
    logToConsole = false,
    includeTimestamp = true
}

local GUI_ID_MenuDialog = tes3ui.registerID("MenuDialog")

function this.i18n(s)
    return i18n(s)
end

function this.get_actor_ref_from_mobile(mobile)
    if mobile == nil then
        return nil
    end

    return this.get_actor_ref_from_reference(mobile.reference)
end

function this.get_actor_ref_from_reference(ref)
    if ref == nil then
        return nil
    end

    local type = ''
    local name = ''
    local female = false

    if ref.mobile then
        if ref.mobile.objectType == tes3.objectType.mobileNPC and ref.object then
            type = 'npc'
            female = ref.object.baseObject.female
        elseif ref.mobile.objectType == tes3.objectType.mobileCreature then
            type = 'creature'
        elseif ref.mobile.objectType == tes3.objectType.mobilePlayer and ref.mobile then
            type = 'player'
            female = ref.mobile.firstPerson.female
        else
            return nil
        end

        name = ref.mobile.object.name
    else
        return nil
    end

    return {
        ref_id = ref.id,
        name = name,
        type = type,
        female = female
    }
end

function this.is_in_dialog_menu()
    return tes3ui.findMenu(GUI_ID_MenuDialog) ~= nil
end

function this.now_ms()
    return math.floor(mwse.realTimers.clock * 1000)
end

-- Copied from UI Expansion
function this.complexKeybindTest(keybind)
    local keybindType = type(keybind)
    local inputController = tes3.worldController.inputController
    if (keybindType == "number") then
        return inputController:isKeyDown(keybind)
    elseif (keybindType == "table") then
        if (keybind.keyCode) then
            return mwse.mcm.testKeyBind(keybind)
        else
            for _, k in ipairs(keybind) do
                if (not this.complexKeybindTest(k)) then
                    return false
                end
            end
            return true
        end
    elseif (keybindType == "string") then
        return inputController:keybindTest(tes3.keybind[keybind])
    end

    return false
end

function this.log(fmt, ...)
    this.logger:info(fmt, ...)
end

function this.debug(fmt, ...)
    this.logger:debug(fmt, ...)
end

function this.get_equipped_items(mobile)
    local equipped = {}

    local slots = {tes3.armorSlot.helmet, tes3.armorSlot.cuirass, tes3.armorSlot.leftPauldron,
                   tes3.armorSlot.rightPauldron, tes3.armorSlot.greaves, tes3.armorSlot.boots,
                   tes3.armorSlot.leftGauntlet, tes3.armorSlot.rightGauntlet, tes3.armorSlot.shield,
                   tes3.armorSlot.leftBracer, tes3.armorSlot.rightBracer}
    for _, objectType in pairs({tes3.objectType.clothing, tes3.objectType.armor}) do
        for _, slot in pairs(slots) do
            local item = tes3.getEquippedItem({
                actor = mobile,
                objectType = objectType,
                slot = slot
            })
            if item ~= nil then
                table.insert(equipped, {
                    id = item.object.id,
                    name = item.object.name
                })
            end
        end
    end

    return equipped
end

function this.get_nakedness(mobile)
    local result = {
        head = true,
        torso = true,
        feet = true,
        legs = true
    }

    for _, object_type in pairs({tes3.objectType.clothing, tes3.objectType.armor}) do
        for slot = 0, 9, 1 do
            local item = tes3.getEquippedItem({
                actor = mobile,
                objectType = object_type,
                slot = slot
            })
            if item ~= nil then
                if object_type == tes3.objectType.clothing then
                    if slot == tes3.clothingSlot.shirt or slot == tes3.clothingSlot.robe then
                        result["torso"] = false
                    end
                    if slot == tes3.clothingSlot.pants or slot == tes3.clothingSlot.skirt or slot ==
                        tes3.clothingSlot.robe then
                        result["legs"] = false
                    end
                    if slot == tes3.clothingSlot.shoes then
                        result["feet"] = false
                    end
                else
                    if slot == tes3.armorSlot.cuirass then
                        result["torso"] = false
                    elseif slot == tes3.armorSlot.greaves then
                        result["legs"] = false
                    elseif slot == tes3.armorSlot.helmet then
                        result["head"] = false
                    elseif slot == tes3.armorSlot.boots then
                        result["feet"] = false
                    end
                end
            end
        end
    end

    return result
end

function this.ray_test_actor_ref()
    local hit_result = tes3.rayTest({
        position = tes3.getCameraPosition(),
        direction = tes3.getCameraVector(),
        maxDistance = 64 * 40,
        useModelBounds = false -- true does not work for some reason
    })
    local hit_ref = hit_result and hit_result.reference
    return this.get_actor_ref_from_reference(hit_ref)
end

return this
