from typing import Optional
from pydantic import BaseModel


class NpcSpawnItem(BaseModel):
    trigger: str
    item_id: str
    item_name: str
    water_amount: Optional[int]


NPC_SPAWN_LIST: list[NpcSpawnItem] = [
    NpcSpawnItem(
        trigger="trigger_drop_healpotion_bad",
        item_id="p_restore_health_b",
        item_name="уцененное зелье лечения",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_healpotion_cheap",
        item_id="p_restore_health_c",
        item_name="дешевое зелье лечения",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_healpotion_quality",
        item_id="p_restore_health_q",
        item_name="качественное зелье лечения",
        water_amount=None
    ),

    NpcSpawnItem(
        trigger="trigger_drop_crabmeat",
        item_id="ingred_crab_meat_01",
        item_name="мясо грязекраба",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_ashyam",
        item_id="ingred_ash_yam_01",
        item_name="пепельный батат (овощ)",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_scuttle",
        item_id="ingred_scuttle_01",
        item_name="скаттл (сыр из жуков)",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_saltrice",
        item_id="ingred_saltrice_01",
        item_name="соленый рис",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_bread",
        item_id="ingred_bread_01",
        item_name="хлеб",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_kwamaegg",
        item_id="food_kwama_egg_01",
        item_name="яйцо квама",
        water_amount=None
    ),

    NpcSpawnItem(
        trigger="trigger_drop_grif",
        item_id="potion_comberry_brandy_01",
        item_name="грииф",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_brandy",
        item_id="potion_cyro_brandy_01",
        item_name="киродиильский бренди",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_flin",
        item_id="potion_cyro_whiskey_01",
        item_name="флин (виски)",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_shein",
        item_id="potion_comberry_wine_01",
        item_name="шейн",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_sujamma",
        item_id="potion_local_liquor_01",
        item_name="суджамма",
        water_amount=None
    ),
    NpcSpawnItem(
        trigger="trigger_drop_mazte",
        item_id="potion_local_brew_01",
        item_name="мацте",
        water_amount=None
    ),

    NpcSpawnItem(
        trigger="trigger_drop_gold",
        item_id="gold_001",
        item_name="монеты",
        water_amount=None
    ),

    NpcSpawnItem(
        trigger="trigger_drop_water_glass",
        item_id="misc_de_glass_yellow_01",
        item_name="стакан воды",
        water_amount=25
    ),
    NpcSpawnItem(
        trigger="trigger_drop_water_bottle",
        item_id="misc_com_bottle_06",
        item_name="бутылка воды",
        water_amount=90
    ),
]
