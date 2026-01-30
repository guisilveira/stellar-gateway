"""
Unit tests for Domain Models (All Entities).

This file defines the expected behavior for all 6 SWAPI entities.
Testing generic logic and specific field validations.
"""

from datetime import datetime, date

import pytest
from pydantic import ValidationError

from domain.models import (
    Film,
    Person,
    Planet,
    Species,
    Starship,
    SwapiBaseModel,
    Vehicle,
)


class TestSwapiBaseModel:
    """Test suite for the shared behavior of all SWAPI entities."""

    def test_subclasses_have_common_fields(self) -> None:
        """Ensure all domain entities inherit common fields."""
        assert issubclass(Person, SwapiBaseModel)
        assert issubclass(Planet, SwapiBaseModel)
        assert issubclass(Starship, SwapiBaseModel)
        assert issubclass(Vehicle, SwapiBaseModel)
        assert issubclass(Species, SwapiBaseModel)
        assert issubclass(Film, SwapiBaseModel)


class TestPersonModel:
    """Test suite for the Person domain entity."""

    @pytest.fixture
    def valid_person_data(self) -> dict:
        return {
            "name": "Luke Skywalker",
            "height": "172",
            "mass": "77",
            "hair_color": "blond",
            "skin_color": "fair",
            "eye_color": "blue",
            "birth_year": "19BBY",
            "gender": "male",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
            ],
            "species": [],
            "vehicles": [
                "https://swapi.dev/api/vehicles/14/",
            ],
            "starships": [
                "https://swapi.dev/api/starships/12/",
            ],
            "created": "2014-12-09T13:50:51.644000Z",
            "edited": "2014-12-20T21:17:56.891000Z",
            "url": "https://swapi.dev/api/people/1/",
        }

    def test_person_creation(self, valid_person_data: dict) -> None:
        person = Person(**valid_person_data)
        assert person.name == "Luke Skywalker"
        assert person.gender == "male"
        assert str(person.homeworld) == "https://swapi.dev/api/planets/1/"
        assert isinstance(person.created, datetime)


class TestPlanetModel:
    """Test suite for the Planet domain entity."""

    @pytest.fixture
    def valid_planet_data(self) -> dict:
        return {
            "name": "Tatooine",
            "rotation_period": "23",
            "orbital_period": "304",
            "diameter": "10465",
            "climate": "arid",
            "gravity": "1 standard",
            "terrain": "desert",
            "surface_water": "1",
            "population": "200000",
            "residents": [
                "https://swapi.dev/api/people/1/",
                "https://swapi.dev/api/people/2/",
            ],
            "films": [
                "https://swapi.dev/api/films/1/",
            ],
            "created": "2014-12-09T13:50:49.641000Z",
            "edited": "2014-12-20T20:58:18.411000Z",
            "url": "https://swapi.dev/api/planets/1/",
        }

    def test_planet_creation(self, valid_planet_data: dict) -> None:
        planet = Planet(**valid_planet_data)
        assert planet.name == "Tatooine"
        assert planet.climate == "arid"
        assert str(planet.url) == "https://swapi.dev/api/planets/1/"


class TestStarshipModel:
    """Test suite for the Starship domain entity."""

    @pytest.fixture
    def valid_starship_data(self) -> dict:
        return {
            "name": "X-wing",
            "model": "T-65 X-wing",
            "manufacturer": "Incom Corporation",
            "cost_in_credits": "149999",
            "length": "12.5",
            "max_atmosphering_speed": "1050",
            "crew": "1",
            "passengers": "0",
            "cargo_capacity": "110",
            "consumables": "1 week",
            "hyperdrive_rating": "1.0",
            "MGLT": "100",
            "starship_class": "Starfighter",
            "pilots": [
                "https://swapi.dev/api/people/1/",
            ],
            "films": [
                "https://swapi.dev/api/films/1/",
            ],
            "created": "2014-12-12T11:19:05.340000Z",
            "edited": "2014-12-20T21:23:49.886000Z",
            "url": "https://swapi.dev/api/starships/12/",
        }

    def test_starship_creation(self, valid_starship_data: dict) -> None:
        starship = Starship(**valid_starship_data)
        assert starship.name == "X-wing"
        assert starship.starship_class == "Starfighter"
        assert str(starship.url) == "https://swapi.dev/api/starships/12/"


class TestVehicleModel:
    """Test suite for the Vehicle domain entity."""

    @pytest.fixture
    def valid_vehicle_data(self) -> dict:
        return {
            "name": "Snowspeeder",
            "model": "t-47 airspeeder",
            "manufacturer": "Incom corporation",
            "cost_in_credits": "unknown",
            "length": "4.5",
            "max_atmosphering_speed": "650",
            "crew": "2",
            "passengers": "0",
            "cargo_capacity": "10",
            "consumables": "none",
            "vehicle_class": "airspeeder",
            "pilots": [
                "https://swapi.dev/api/people/1/",
                "https://swapi.dev/api/people/18/",
            ],
            "films": [
                "https://swapi.dev/api/films/2/",
            ],
            "created": "2014-12-15T12:22:12Z",
            "edited": "2014-12-20T21:30:21.672000Z",
            "url": "https://swapi.dev/api/vehicles/14/",
        }

    def test_vehicle_creation(self, valid_vehicle_data: dict) -> None:
        vehicle = Vehicle(**valid_vehicle_data)
        assert vehicle.name == "Snowspeeder"
        assert vehicle.vehicle_class == "airspeeder"
        assert str(vehicle.url) == "https://swapi.dev/api/vehicles/14/"


class TestSpeciesModel:
    """Test suite for the Species domain entity."""

    @pytest.fixture
    def valid_species_data(self) -> dict:
        return {
            "name": "Wookie",
            "classification": "mammal",
            "designation": "sentient",
            "average_height": "210",
            "skin_colors": "gray",
            "hair_colors": "black, brown",
            "eye_colors": "blue, green, yellow, brown, golden, red",
            "average_lifespan": "400",
            "homeworld": "https://swapi.dev/api/planets/14/",
            "language": "Shyriiwook",
            "people": [
                "https://swapi.dev/api/people/13/",
            ],
            "films": [
                "https://swapi.dev/api/films/1/",
            ],
            "created": "2014-12-10T16:44:31.486000Z",
            "edited": "2014-12-20T21:36:42.142000Z",
            "url": "https://swapi.dev/api/species/3/",
        }

    def test_species_creation(self, valid_species_data: dict) -> None:
        species = Species(**valid_species_data)
        assert species.name == "Wookie"
        assert species.classification == "mammal"
        assert species.language == "Shyriiwook"
        assert str(species.homeworld) == "https://swapi.dev/api/planets/14/"


class TestFilmModel:
    """Test suite for the Film domain entity."""

    @pytest.fixture
    def valid_film_data(self) -> dict:
        return {
            "title": "A New Hope",
            "episode_id": 4,
            "opening_crawl": "It is a period of civil war...",
            "director": "George Lucas",
            "producer": "Gary Kurtz, Rick McCallum",
            "release_date": "1977-05-25",
            "characters": [
                "https://swapi.dev/api/people/1/",
            ],
            "planets": [
                "https://swapi.dev/api/planets/1/",
            ],
            "starships": [
                "https://swapi.dev/api/starships/2/",
            ],
            "vehicles": [
                "https://swapi.dev/api/vehicles/4/",
            ],
            "species": [
                "https://swapi.dev/api/species/1/",
            ],
            "created": "2014-12-10T14:23:31.880000Z",
            "edited": "2014-12-20T19:49:45.256000Z",
            "url": "https://swapi.dev/api/films/1/",
        }

    def test_film_creation(self, valid_film_data: dict) -> None:
        film = Film(**valid_film_data)
        assert film.title == "A New Hope"
        assert film.episode_id == 4
        assert film.director == "George Lucas"
        assert isinstance(film.release_date, date)
        assert str(film.url) == "https://swapi.dev/api/films/1/"
