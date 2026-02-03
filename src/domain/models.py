"""
Domain Models for the Stellar Gateway.

This module defines the core business entities using Pydantic for validation.
These models represent the data structure as understood by the application domain.
"""

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, HttpUrl


class SwapiBaseModel(BaseModel):
    """
    Base class for all SWAPI entities.
    Contains common metadata fields found in every resource.
    """

    created: datetime
    edited: datetime
    url: HttpUrl


class Person(SwapiBaseModel):
    """
    Represents a Person (character) in the Star Wars universe.
    """

    name: str
    height: str
    mass: str
    hair_color: str
    skin_color: str
    eye_color: str
    birth_year: str
    gender: str
    homeworld: HttpUrl
    films: List[HttpUrl]
    species: List[HttpUrl]
    vehicles: List[HttpUrl]
    starships: List[HttpUrl]


class Planet(SwapiBaseModel):
    """
    Represents a Planet in the Star Wars universe.
    """

    name: str
    rotation_period: str
    orbital_period: str
    diameter: str
    climate: str
    gravity: str
    terrain: str
    surface_water: str
    population: str
    residents: List[HttpUrl]
    films: List[HttpUrl]


class Starship(SwapiBaseModel):
    """
    Represents a Starship in the Star Wars universe.
    """

    name: str
    model: str
    manufacturer: str
    cost_in_credits: str
    length: str
    max_atmosphering_speed: str
    crew: str
    passengers: str
    cargo_capacity: str
    consumables: str
    hyperdrive_rating: str
    MGLT: str
    starship_class: str
    pilots: List[HttpUrl]
    films: List[HttpUrl]


class Vehicle(SwapiBaseModel):
    """
    Represents a Vehicle in the Star Wars universe.
    """

    name: str
    model: str
    manufacturer: str
    cost_in_credits: str
    length: str
    max_atmosphering_speed: str
    crew: str
    passengers: str
    cargo_capacity: str
    consumables: str
    vehicle_class: str
    pilots: List[HttpUrl]
    films: List[HttpUrl]


class Species(SwapiBaseModel):
    """
    Represents a Species in the Star Wars universe.
    """

    name: str
    classification: str
    designation: str
    average_height: str
    skin_colors: str
    hair_colors: str
    eye_colors: str
    average_lifespan: str
    homeworld: HttpUrl | None
    language: str
    people: List[HttpUrl]
    films: List[HttpUrl]


class Film(SwapiBaseModel):
    """
    Represents a Film in the Star Wars universe.
    """

    title: str
    episode_id: int
    opening_crawl: str
    director: str
    producer: str
    release_date: date
    characters: List[HttpUrl]
    planets: List[HttpUrl]
    starships: List[HttpUrl]
    vehicles: List[HttpUrl]
    species: List[HttpUrl]
