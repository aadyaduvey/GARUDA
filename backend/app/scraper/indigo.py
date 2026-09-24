"""IndiGo: deliberately NOT scraped.

goindigo.in/robots.txt disallows automated access to its search and booking pages for all
user agents (Disallow: /search.html, /book/*, /booking/*), checked 25 Sep 2026. GARUDA
respects robots.txt, so IndiGo fares need a sanctioned source instead (see backend/README.md,
"Airlines without a scraper").
"""
from datetime import date

from app.scraper.base import FareRow, Scraper, ScraperError


class IndigoScraper(Scraper):
    airline = "6E"
    name = "IndiGo"
    source = "indigo"

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        raise ScraperError("not scraped: goindigo.in robots.txt disallows automated search/booking access")
