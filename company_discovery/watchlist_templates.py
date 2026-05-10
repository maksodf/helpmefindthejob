"""Curated starter watchlist templates per persona.

Each template is a small, reviewed list of well-known European
employers categorised by sector. The user can apply a template to
add every entry to their watchlist with a single click.

Templates are tagged with ``personas`` membership so the UI can
surface only the templates relevant to the user's selected persona.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TemplateCompany:
    name: str
    website_url: str
    career_page_url: str
    sector: str


@dataclass(frozen=True)
class WatchlistTemplate:
    id: str
    label: str
    description: str
    companies: tuple[TemplateCompany, ...]
    personas: tuple[str, ...] = ("healthcare-management",)


_TEMPLATES: tuple[WatchlistTemplate, ...] = (
    # Healthcare-management templates
    WatchlistTemplate(
        id="hospital_groups_de",
        label="Hospital groups (Germany)",
        description="Major German clinic and hospital groups with public career pages.",
        personas=("healthcare-management",),
        companies=(
            TemplateCompany(
                name="Charité Berlin",
                website_url="https://www.charite.de/",
                career_page_url="https://www.charite.de/karriere/",
                sector="University hospital",
            ),
            TemplateCompany(
                name="Vivantes",
                website_url="https://www.vivantes.de/",
                career_page_url="https://karriere.vivantes.de/",
                sector="Hospital / clinic group",
            ),
            TemplateCompany(
                name="Helios Kliniken",
                website_url="https://www.helios-gesundheit.de/",
                career_page_url="https://karriere.helios-gesundheit.de/",
                sector="Hospital / clinic group",
            ),
            TemplateCompany(
                name="Asklepios",
                website_url="https://www.asklepios.com/",
                career_page_url="https://karriere.asklepios.com/",
                sector="Hospital / clinic group",
            ),
        ),
    ),
    WatchlistTemplate(
        id="statutory_insurers_de",
        label="Statutory health insurers (Germany)",
        description="Largest GKV insurers with central career pages.",
        personas=("healthcare-management",),
        companies=(
            TemplateCompany(
                name="Techniker Krankenkasse",
                website_url="https://www.tk.de/",
                career_page_url="https://www.tk.de/jobs",
                sector="Statutory health insurer",
            ),
            TemplateCompany(
                name="Barmer",
                website_url="https://www.barmer.de/",
                career_page_url="https://karriere.barmer.de/",
                sector="Statutory health insurer",
            ),
            TemplateCompany(
                name="DAK-Gesundheit",
                website_url="https://www.dak.de/",
                career_page_url="https://www.dak.de/dak/karriere/",
                sector="Statutory health insurer",
            ),
        ),
    ),
    WatchlistTemplate(
        id="digital_health_de",
        label="Digital Health & Healthcare IT (Germany)",
        description="Healthcare IT and digital-health employers active in Germany.",
        personas=("healthcare-management",),
        companies=(
            TemplateCompany(
                name="Doctolib",
                website_url="https://www.doctolib.de/",
                career_page_url="https://careers.doctolib.de/",
                sector="Digital Health",
            ),
            TemplateCompany(
                name="Ada Health",
                website_url="https://ada.com/",
                career_page_url="https://ada.com/careers/",
                sector="Digital Health",
            ),
            TemplateCompany(
                name="CompuGroup Medical",
                website_url="https://www.cgm.com/",
                career_page_url="https://www.cgm.com/de/karriere",
                sector="Healthcare IT",
            ),
        ),
    ),

    # Tech persona
    WatchlistTemplate(
        id="berlin_tech_scene",
        label="Berlin tech scene",
        description="High-profile tech employers headquartered in or with a major presence in Berlin.",
        personas=("tech", "product-management"),
        companies=(
            TemplateCompany(
                name="Zalando",
                website_url="https://corporate.zalando.com/",
                career_page_url="https://jobs.zalando.com/",
                sector="E-commerce / marketplace",
            ),
            TemplateCompany(
                name="N26",
                website_url="https://n26.com/",
                career_page_url="https://n26.com/en/careers",
                sector="Fintech / neobank",
            ),
            TemplateCompany(
                name="Trade Republic",
                website_url="https://traderepublic.com/",
                career_page_url="https://traderepublic.com/careers",
                sector="Fintech / brokerage",
            ),
            TemplateCompany(
                name="GetYourGuide",
                website_url="https://www.getyourguide.com/",
                career_page_url="https://careers.getyourguide.com/",
                sector="Marketplace / travel",
            ),
            TemplateCompany(
                name="Personio",
                website_url="https://www.personio.com/",
                career_page_url="https://www.personio.com/careers/",
                sector="B2B SaaS",
            ),
        ),
    ),
    WatchlistTemplate(
        id="eu_developer_tools",
        label="European developer tools",
        description="Developer-tools companies with strong remote/EU hiring.",
        personas=("tech", "product-management"),
        companies=(
            TemplateCompany(
                name="GitHub",
                website_url="https://github.com/",
                career_page_url="https://github.com/about/careers",
                sector="Developer tools",
            ),
            TemplateCompany(
                name="Datadog",
                website_url="https://www.datadoghq.com/",
                career_page_url="https://www.datadoghq.com/careers/",
                sector="SaaS / observability",
            ),
            TemplateCompany(
                name="Vercel",
                website_url="https://vercel.com/",
                career_page_url="https://vercel.com/careers",
                sector="Developer tools / Cloud",
            ),
            TemplateCompany(
                name="Hugging Face",
                website_url="https://huggingface.co/",
                career_page_url="https://apply.workable.com/huggingface/",
                sector="AI / ML",
            ),
        ),
    ),

    # Marketing persona
    WatchlistTemplate(
        id="dtc_consumer_brands_de",
        label="DTC consumer brands (DACH)",
        description="High-growth DTC and consumer brands with strong marketing teams in the DACH region.",
        personas=("marketing", "product-management"),
        companies=(
            TemplateCompany(
                name="HelloFresh",
                website_url="https://www.hellofreshgroup.com/",
                career_page_url="https://careers.hellofresh.com/",
                sector="DTC / food",
            ),
            TemplateCompany(
                name="About You",
                website_url="https://corporate.aboutyou.de/",
                career_page_url="https://corporate.aboutyou.de/de/career",
                sector="E-commerce / fashion",
            ),
            TemplateCompany(
                name="Zalando",
                website_url="https://corporate.zalando.com/",
                career_page_url="https://jobs.zalando.com/",
                sector="E-commerce / marketplace",
            ),
            TemplateCompany(
                name="Flink",
                website_url="https://www.goflink.com/",
                career_page_url="https://www.goflink.com/de-de/careers/",
                sector="Q-commerce / grocery",
            ),
        ),
    ),
    WatchlistTemplate(
        id="b2b_saas_marketing",
        label="B2B SaaS marketing teams",
        description="Software vendors with strong product-marketing, demand-gen, and content functions.",
        personas=("marketing", "product-management"),
        companies=(
            TemplateCompany(
                name="HubSpot",
                website_url="https://www.hubspot.com/",
                career_page_url="https://www.hubspot.com/careers",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Personio",
                website_url="https://www.personio.com/",
                career_page_url="https://www.personio.com/careers/",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Celonis",
                website_url="https://www.celonis.com/",
                career_page_url="https://www.celonis.com/careers/",
                sector="B2B SaaS",
            ),
        ),
    ),

    # Finance persona
    WatchlistTemplate(
        id="dax_finance_de",
        label="DAX 40 finance teams",
        description="Large German blue-chips with central finance, controlling, treasury, and audit teams.",
        personas=("finance",),
        companies=(
            TemplateCompany(
                name="Deutsche Bank",
                website_url="https://www.db.com/",
                career_page_url="https://careers.db.com/",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Commerzbank",
                website_url="https://www.commerzbank.de/",
                career_page_url="https://www.commerzbank.de/karriere",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Allianz",
                website_url="https://www.allianz.com/",
                career_page_url="https://careers.allianz.com/",
                sector="Insurance",
            ),
            TemplateCompany(
                name="Munich Re",
                website_url="https://www.munichre.com/",
                career_page_url="https://www.munichre.com/en/company/career.html",
                sector="Reinsurance",
            ),
        ),
    ),
    WatchlistTemplate(
        id="big4_de",
        label="Big-4 audit & advisory (Germany)",
        description="Big-4 firms with active audit, tax, transaction-services, and advisory hiring in Germany.",
        personas=("finance",),
        companies=(
            TemplateCompany(
                name="KPMG Germany",
                website_url="https://kpmg.com/de/",
                career_page_url="https://kpmg.com/de/de/home/karriere.html",
                sector="Audit / advisory",
            ),
            TemplateCompany(
                name="EY Germany",
                website_url="https://www.ey.com/de_de",
                career_page_url="https://www.ey.com/de_de/careers",
                sector="Audit / advisory",
            ),
            TemplateCompany(
                name="PwC Germany",
                website_url="https://www.pwc.de/",
                career_page_url="https://www.pwc.de/de/karriere.html",
                sector="Audit / advisory",
            ),
            TemplateCompany(
                name="Deloitte Germany",
                website_url="https://www2.deloitte.com/de/de.html",
                career_page_url="https://www2.deloitte.com/de/de/careers.html",
                sector="Audit / advisory",
            ),
        ),
    ),

    # Regional templates — France
    WatchlistTemplate(
        id="paris_tech_fr",
        label="Paris tech (France)",
        description="Tech employers headquartered in or with a major hub in Paris.",
        personas=("tech", "product-management"),
        companies=(
            TemplateCompany(
                name="Mistral AI",
                website_url="https://mistral.ai/",
                career_page_url="https://mistral.ai/careers/",
                sector="AI / ML",
            ),
            TemplateCompany(
                name="Hugging Face",
                website_url="https://huggingface.co/",
                career_page_url="https://apply.workable.com/huggingface/",
                sector="AI / ML",
            ),
            TemplateCompany(
                name="Doctolib",
                website_url="https://www.doctolib.fr/",
                career_page_url="https://careers.doctolib.com/",
                sector="Digital Health",
            ),
            TemplateCompany(
                name="BlaBlaCar",
                website_url="https://www.blablacar.com/",
                career_page_url="https://www.blablacar.com/jobs",
                sector="Marketplace / mobility",
            ),
            TemplateCompany(
                name="Qonto",
                website_url="https://qonto.com/",
                career_page_url="https://qonto.com/en/careers",
                sector="Fintech",
            ),
        ),
    ),
    # Regional templates — Netherlands
    WatchlistTemplate(
        id="amsterdam_tech_nl",
        label="Amsterdam tech (Netherlands)",
        description="Tech and fintech employers with a strong Amsterdam presence.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="Booking.com",
                website_url="https://www.booking.com/",
                career_page_url="https://careers.booking.com/",
                sector="Travel / marketplace",
            ),
            TemplateCompany(
                name="Adyen",
                website_url="https://www.adyen.com/",
                career_page_url="https://careers.adyen.com/",
                sector="Fintech / payments",
            ),
            TemplateCompany(
                name="Mollie",
                website_url="https://www.mollie.com/",
                career_page_url="https://jobs.mollie.com/",
                sector="Fintech / payments",
            ),
            TemplateCompany(
                name="Bunq",
                website_url="https://www.bunq.com/",
                career_page_url="https://jobs.bunq.com/",
                sector="Fintech / neobank",
            ),
            TemplateCompany(
                name="Miro",
                website_url="https://miro.com/",
                career_page_url="https://miro.com/careers/",
                sector="B2B SaaS",
            ),
        ),
    ),
    # Regional templates — Italy
    WatchlistTemplate(
        id="milan_tech_it",
        label="Milan tech (Italy)",
        description="High-growth tech and fintech employers in Italy.",
        personas=("tech", "product-management"),
        companies=(
            TemplateCompany(
                name="Bending Spoons",
                website_url="https://bendingspoons.com/",
                career_page_url="https://bendingspoons.com/careers.html",
                sector="Consumer tech",
            ),
            TemplateCompany(
                name="Satispay",
                website_url="https://www.satispay.com/",
                career_page_url="https://www.satispay.com/work-with-us/",
                sector="Fintech / payments",
            ),
            TemplateCompany(
                name="Scalapay",
                website_url="https://www.scalapay.com/",
                career_page_url="https://www.scalapay.com/en/careers",
                sector="Fintech / BNPL",
            ),
            TemplateCompany(
                name="Iliad Italia",
                website_url="https://www.iliad.it/",
                career_page_url="https://www.iliad.it/lavora-con-noi",
                sector="Telecom",
            ),
        ),
    ),
    # Regional templates — UK / London
    WatchlistTemplate(
        id="london_finance_uk",
        label="London finance (UK)",
        description="Major banks, asset managers, and Big-4 firms hiring out of London.",
        personas=("finance",),
        companies=(
            TemplateCompany(
                name="HSBC",
                website_url="https://www.hsbc.com/",
                career_page_url="https://www.hsbc.com/careers",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Barclays",
                website_url="https://home.barclays/",
                career_page_url="https://home.barclays/careers/",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Lloyds Banking Group",
                website_url="https://www.lloydsbankinggroup.com/",
                career_page_url="https://www.lloydsbankinggroup.com/careers.html",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Schroders",
                website_url="https://www.schroders.com/",
                career_page_url="https://jobs.schroders.com/",
                sector="Asset management",
            ),
            TemplateCompany(
                name="Man Group",
                website_url="https://www.man.com/",
                career_page_url="https://www.man.com/careers",
                sector="Asset management",
            ),
        ),
    ),
    # Regional templates — Switzerland
    WatchlistTemplate(
        id="zurich_tech_ch",
        label="Zurich tech (Switzerland)",
        description="Tech and engineering employers based in Zurich.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="Logitech",
                website_url="https://www.logitech.com/",
                career_page_url="https://jobs.logitech.com/",
                sector="Consumer tech / hardware",
            ),
            TemplateCompany(
                name="Swisscom",
                website_url="https://www.swisscom.ch/",
                career_page_url="https://www.swisscom.ch/en/about/career.html",
                sector="Telecom / IT",
            ),
            TemplateCompany(
                name="ABB",
                website_url="https://global.abb/",
                career_page_url="https://global.abb/group/en/careers",
                sector="Industrial tech",
            ),
            TemplateCompany(
                name="UBS",
                website_url="https://www.ubs.com/",
                career_page_url="https://www.ubs.com/global/en/careers.html",
                sector="Universal bank / wealth",
            ),
            TemplateCompany(
                name="Smallpdf",
                website_url="https://smallpdf.com/",
                career_page_url="https://smallpdf.com/jobs",
                sector="B2C SaaS",
            ),
        ),
    ),
    # Regional templates — Spain (Madrid)
    WatchlistTemplate(
        id="madrid_tech_es",
        label="Madrid tech (Spain)",
        description="Tech and fintech employers headquartered in or with a major presence in Madrid.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="BBVA",
                website_url="https://www.bbva.com/",
                career_page_url="https://careers.bbva.com/",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Santander",
                website_url="https://www.santander.com/",
                career_page_url="https://www.santander.com/en/careers",
                sector="Universal bank",
            ),
            TemplateCompany(
                name="Cabify",
                website_url="https://cabify.com/",
                career_page_url="https://cabify.com/jobs",
                sector="Mobility / marketplace",
            ),
            TemplateCompany(
                name="Tinybird",
                website_url="https://www.tinybird.co/",
                career_page_url="https://www.tinybird.co/careers",
                sector="Data infrastructure",
            ),
        ),
    ),
    # Regional templates — Spain (Barcelona)
    WatchlistTemplate(
        id="barcelona_tech_es",
        label="Barcelona tech (Spain)",
        description="High-growth Catalan tech and SaaS employers.",
        personas=("tech", "product-management"),
        companies=(
            TemplateCompany(
                name="Typeform",
                website_url="https://www.typeform.com/",
                career_page_url="https://www.typeform.com/careers/",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Glovo",
                website_url="https://about.glovoapp.com/",
                career_page_url="https://jobs.glovoapp.com/",
                sector="On-demand / marketplace",
            ),
            TemplateCompany(
                name="TravelPerk",
                website_url="https://www.travelperk.com/",
                career_page_url="https://careers.travelperk.com/",
                sector="B2B SaaS / travel",
            ),
            TemplateCompany(
                name="Factorial",
                website_url="https://factorialhr.com/",
                career_page_url="https://factorialhr.com/careers",
                sector="B2B SaaS / HR-tech",
            ),
            TemplateCompany(
                name="Wallbox",
                website_url="https://wallbox.com/",
                career_page_url="https://wallbox.com/en_eu/careers",
                sector="EV charging / hardware",
            ),
        ),
    ),
    # Regional templates — Sweden (Stockholm)
    WatchlistTemplate(
        id="stockholm_tech_se",
        label="Stockholm tech (Sweden)",
        description="Swedish tech, fintech, and consumer-tech employers.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="Spotify",
                website_url="https://www.lifeatspotify.com/",
                career_page_url="https://www.lifeatspotify.com/jobs",
                sector="Media / streaming",
            ),
            TemplateCompany(
                name="Klarna",
                website_url="https://www.klarna.com/",
                career_page_url="https://www.klarna.com/careers/",
                sector="Fintech / payments",
            ),
            TemplateCompany(
                name="Voi Technology",
                website_url="https://www.voi.com/",
                career_page_url="https://www.voi.com/careers",
                sector="Mobility",
            ),
            TemplateCompany(
                name="Tink",
                website_url="https://tink.com/",
                career_page_url="https://tink.com/careers/",
                sector="Fintech / open banking",
            ),
        ),
    ),
    # Regional templates — Denmark (Copenhagen)
    WatchlistTemplate(
        id="copenhagen_tech_dk",
        label="Copenhagen tech (Denmark)",
        description="Danish tech and SaaS employers, plus Nordic fintech.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="Pleo",
                website_url="https://www.pleo.io/",
                career_page_url="https://www.pleo.io/careers",
                sector="Fintech / B2B SaaS",
            ),
            TemplateCompany(
                name="Trustpilot",
                website_url="https://www.trustpilot.com/",
                career_page_url="https://careers.trustpilot.com/",
                sector="Marketplace / reviews",
            ),
            TemplateCompany(
                name="Templafy",
                website_url="https://www.templafy.com/",
                career_page_url="https://www.templafy.com/careers/",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Vivino",
                website_url="https://www.vivino.com/",
                career_page_url="https://www.vivino.com/careers",
                sector="Marketplace / consumer",
            ),
        ),
    ),
    # Regional templates — Poland (Warsaw)
    WatchlistTemplate(
        id="warsaw_tech_pl",
        label="Warsaw tech (Poland)",
        description="Polish tech, fintech, and SaaS employers.",
        personas=("tech", "product-management", "finance"),
        companies=(
            TemplateCompany(
                name="Allegro",
                website_url="https://allegro.tech/",
                career_page_url="https://allegro.pl/praca",
                sector="E-commerce / marketplace",
            ),
            TemplateCompany(
                name="Booksy",
                website_url="https://booksy.com/",
                career_page_url="https://careers.booksy.com/",
                sector="Marketplace / SaaS",
            ),
            TemplateCompany(
                name="DocPlanner",
                website_url="https://www.docplanner.com/",
                career_page_url="https://www.docplanner.com/careers",
                sector="Digital health / marketplace",
            ),
            TemplateCompany(
                name="Brainly",
                website_url="https://brainly.com/",
                career_page_url="https://brainly.com/careers",
                sector="EdTech",
            ),
            TemplateCompany(
                name="mBank",
                website_url="https://www.mbank.pl/",
                career_page_url="https://kariera.mbank.pl/",
                sector="Universal bank",
            ),
        ),
    ),

    # Product-management persona
    WatchlistTemplate(
        id="product_led_saas",
        label="Product-led SaaS",
        description="Software companies known for strong product-management and product-led growth.",
        personas=("product-management", "tech"),
        companies=(
            TemplateCompany(
                name="Stripe",
                website_url="https://stripe.com/",
                career_page_url="https://stripe.com/jobs",
                sector="Fintech / payments",
            ),
            TemplateCompany(
                name="HubSpot",
                website_url="https://www.hubspot.com/",
                career_page_url="https://www.hubspot.com/careers",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Personio",
                website_url="https://www.personio.com/",
                career_page_url="https://www.personio.com/careers/",
                sector="B2B SaaS",
            ),
            TemplateCompany(
                name="Vercel",
                website_url="https://vercel.com/",
                career_page_url="https://vercel.com/careers",
                sector="Developer tools",
            ),
        ),
    ),
)


def list_templates(persona_id: str | None = None) -> list[dict[str, object]]:
    """List templates, optionally filtered to a single persona."""

    matching = _TEMPLATES if persona_id is None else tuple(
        template for template in _TEMPLATES if persona_id in template.personas
    )
    return [
        {
            "id": template.id,
            "label": template.label,
            "description": template.description,
            "personas": list(template.personas),
            "companies": [asdict(item) for item in template.companies],
        }
        for template in matching
    ]


def get_template(template_id: str) -> WatchlistTemplate | None:
    for template in _TEMPLATES:
        if template.id == template_id:
            return template
    return None
