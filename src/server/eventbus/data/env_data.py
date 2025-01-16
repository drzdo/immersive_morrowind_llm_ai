from typing import Any, Optional

from pydantic import BaseModel


class _AshFallData(BaseModel):
    vampireWarmEffect: float
    weatherTemp: float
    furTemp: float
    trinketEffects: list[Any]
    insideTent: Optional[bool] = None
    fireTemp: float
    valuesInitialised: bool
    fireDamageEffect: float
    hazardTemp: float
    woodAxesForHarvesting: list[Any]
    blightness: float
    wetness: float
    resistFrostEffect: float
    tentTempMulti: Optional[float] = None
    sacks: list[Any]
    wetTemp: float
    wetCoolingRate: float
    frostDamageEffect: float
    resistFireEffect: float
    currentStates: Any
    sunshades: list[Any]
    foodPoison: float
    tiredness: float
    faceCovered: bool
    flu: float
    vampireColdEffect: float
    hungerEffect: Optional[float] = None
    stewWarmEffect: Optional[float] = None
    intWeatherEffect: float
    lastTimeScriptsUpdated: float
    hunger: float
    backpacks: Any
    baseTemp: float
    nearCampfire: bool
    coverageRating: float
    wetWarmingRate: float
    survivalEffect: Optional[float] = None
    woodAxesForBackpack: Any
    sunShaded: bool
    tempLimit: float
    coverageMulti: float
    thirst: float
    dysentery: float
    warmthRating: float
    thirstEffect: Optional[float] = None
    temp: float
    torchTemp: float
    isSheltered: bool
    sunTemp: float


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
