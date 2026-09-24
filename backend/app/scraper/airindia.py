"""Air India: not implemented.

airindia.com's robots.txt allows search, but the site is protected by Akamai Bot Manager
(sensor scripts on every page) and fares come from a multi-step booking API behind it.
GARUDA does not try to defeat dedicated anti-bot systems, so Air India fares need a
sanctioned source instead (see backend/README.md, "Airlines without a scraper").
"""
from datetime import date

from app.scraper.base import FareRow, Scraper, ScraperError


class AirIndiaScraper(Scraper):
    airline = "AI"
    name = "Air India"
    source = "airindia"

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        raise ScraperError("not implemented: airindia.com fares sit behind Akamai Bot Manager")
