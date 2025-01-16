from pydantic import BaseModel


class ActorAttributes(BaseModel):
    strength: int
    intelligence: int
    willpower: int
    agility: int
    speed: int
    endurance: int
    personality: int
    luck: int


class ActorSkills(BaseModel):
    block: int
    armorer: int
    medium_armor: int
    heavy_armor: int
    blunt_weapon: int

    long_blade: int
    axe: int
    spear: int
    athletics: int
    enchant: int

    destruction: int
    alteration: int
    illusion: int
    conjuration: int
    mysticism: int

    restoration: int
    alchemy: int
    unarmored: int
    security: int
    sneak: int

    acrobatics: int
    light_armor: int
    short_blade: int
    marksman: int
    mercantile: int

    speechcraft: int
    hand_to_hand: int


class ActorEffectAttributes(BaseModel):
    blind: int
    invisibility: int
    levitate: int
    sound: int
    silence: int
    paralyze: int


class ActorOtherStats(BaseModel):
    level: int
    encumbrance: float
    fight: int
    flee: int
    alarm: int


class ActorStats(BaseModel):
    attributes: ActorAttributes
    skills: ActorSkills
    effect_attributes: ActorEffectAttributes
    other: ActorOtherStats
