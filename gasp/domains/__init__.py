from .smartcity import SmartCityDomain

DOMAINS = {"smartcity": SmartCityDomain}


def get_domain(name: str):
    return DOMAINS[name]()
