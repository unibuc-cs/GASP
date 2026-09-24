from .smartcity import SmartCityDomain
from .ops import OpsDomain

DOMAINS = {"smartcity": SmartCityDomain, "ops": OpsDomain}


def get_domain(name: str):
    return DOMAINS[name]()
