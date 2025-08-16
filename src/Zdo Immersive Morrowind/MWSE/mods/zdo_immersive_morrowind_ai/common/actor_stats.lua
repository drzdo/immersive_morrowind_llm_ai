local this = {}

function this.get_actor_stats(mobile)
    local m = mobile
    return {
        attributes = {
            -- https://mwse.github.io/MWSE/references/attributes/
            -- strength	0
            -- intelligence	1
            -- willpower	2
            -- agility	3
            -- speed	4
            -- endurance	5
            -- personality	6
            -- luck	7

            strength = m.attributes[1].current,
            intelligence = m.attributes[2].current,
            willpower = m.attributes[3].current,
            agility = m.attributes[4].current,
            speed = m.attributes[5].current,
            endurance = m.attributes[6].current,
            personality = m.attributes[7].current,
            luck = m.attributes[8].current
        },
        skills = {
            -- https://mwse.github.io/MWSE/references/skills/
            -- block	0
            -- armorer	1
            -- mediumArmor	2
            -- heavyArmor	3
            -- bluntWeapon	4
            -- longBlade	5
            -- axe	6
            -- spear	7
            -- athletics	8
            -- enchant	9
            -- destruction	10
            -- alteration	11
            -- illusion	12
            -- conjuration	13
            -- mysticism	14
            -- restoration	15
            -- alchemy	16
            -- unarmored	17
            -- security	18
            -- sneak	19
            -- acrobatics	20
            -- lightArmor	21
            -- shortBlade	22
            -- marksman	23
            -- mercantile	24
            -- speechcraft	25
            -- handToHand	26

            block = m:getSkillStatistic(0).current,
            armorer = m:getSkillStatistic(1).current,
            medium_armor = m:getSkillStatistic(2).current,
            heavy_armor = m:getSkillStatistic(3).current,
            blunt_weapon = m:getSkillStatistic(4).current,

            long_blade = m:getSkillStatistic(5).current,
            axe = m:getSkillStatistic(6).current,
            spear = m:getSkillStatistic(7).current,
            athletics = m:getSkillStatistic(8).current,
            enchant = m:getSkillStatistic(9).current,

            destruction = m:getSkillStatistic(10).current,
            alteration = m:getSkillStatistic(11).current,
            illusion = m:getSkillStatistic(12).current,
            conjuration = m:getSkillStatistic(13).current,
            mysticism = m:getSkillStatistic(14).current,

            restoration = m:getSkillStatistic(15).current,
            alchemy = m:getSkillStatistic(16).current,
            unarmored = m:getSkillStatistic(17).current,
            security = m:getSkillStatistic(18).current,
            sneak = m:getSkillStatistic(19).current,

            acrobatics = m:getSkillStatistic(20).current,
            light_armor = m:getSkillStatistic(21).current,
            short_blade = m:getSkillStatistic(22).current,
            marksman = m:getSkillStatistic(23).current,
            mercantile = m:getSkillStatistic(24).current,

            speechcraft = m:getSkillStatistic(25).current,
            hand_to_hand = m:getSkillStatistic(26).current
        },
        effect_attributes = {
            -- https://mwse.github.io/MWSE/types/tes3mobileActor/#effectattributes
            -- Access to a table of 24 numbers for the actor's effect attributes. In order those are:
            -- attackBonus, sanctuary, resistMagicka, resistFire, resistFrost,
            -- resistShock, resistCommonDisease, resistBlightDisease, resistCorprus, resistPoison,
            -- resistParalysis, chameleon, resistNormalWeapons, waterBreathing, waterWalking,
            -- swiftSwim, jump, levitate, shield, sound,
            -- silence, blind, paralyze, and invisibility.
            blind = m.blind,
            invisibility = m.invisibility,
            levitate = m.levitate,
            sound = m.sound,
            silence = m.silence,
            paralyze = m.paralyze
        },
        other = {
            level = m.object.level,
            encumbrance = m.encumbrance.current,
            fight = m.fight,
            flee = m.flee,
            alarm = m.alarm
        }
    }
end

return this
