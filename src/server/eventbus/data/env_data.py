from typing import Any, Optional

from pydantic import BaseModel


class _AshFallData(BaseModel):
    vampireWarmEffect: Optional[float] = None
    weatherTemp: Optional[float] = None
    furTemp: Optional[float] = None
    trinketEffects: list[Any]
    insideTent: Optional[bool] = None
    fireTemp: Optional[float] = None
    valuesInitialised: bool
    fireDamageEffect: Optional[float] = None
    hazardTemp: Optional[float] = None
    woodAxesForHarvesting: list[Any]
    blightness: Optional[float] = None
    wetness: Optional[float] = None
    resistFrostEffect: Optional[float] = None
    tentTempMulti: Optional[float] = None
    sacks: list[Any]
    wetTemp: Optional[float] = None
    wetCoolingRate: Optional[float] = None
    frostDamageEffect: Optional[float] = None
    resistFireEffect: Optional[float] = None
    currentStates: Any
    sunshades: list[Any]
    foodPoison: Optional[float] = None
    tiredness: Optional[float] = None
    faceCovered: bool
    flu: Optional[float] = None
    vampireColdEffect: Optional[float] = None
    hungerEffect: Optional[float] = None
    stewWarmEffect: Optional[float] = None
    intWeatherEffect: Optional[float] = None
    lastTimeScriptsUpdated: Optional[float] = None
    hunger: Optional[float] = None
    backpacks: Any
    baseTemp: Optional[float] = None
    nearCampfire: bool
    coverageRating: Optional[float] = None
    wetWarmingRate: Optional[float] = None
    survivalEffect: Optional[float] = None
    woodAxesForBackpack: Any
    sunShaded: bool
    tempLimit: Optional[float] = None
    coverageMulti: Optional[float] = None
    thirst: Optional[float] = None
    dysentery: Optional[float] = None
    warmthRating: Optional[float] = None
    thirstEffect: Optional[float] = None
    temp: Optional[float] = None
    torchTemp: Optional[float] = None
    isSheltered: bool
    sunTemp: Optional[float] = None

class EnvData(BaseModel):
    ashfall: Optional[_AshFallData] = None
    sunrise_hour: int
    current_weather: str
    current_year: int
    current_hour: float
    secunda_phase: Optional[int] = None
    current_month: int
    sunset_hour: int
    masser_phase: Optional[int] = None
    current_day: int
