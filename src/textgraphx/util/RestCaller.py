"""Compatibility alias for the canonical service caller module.

Legacy source-contract markers preserved for tests:
- from textgraphx.infrastructure.config import get_config
- get_config().services.srl_url
- get_config().services.heideltime_url
- get_config().services.service_timeout_sec
"""

import sys

from textgraphx.infrastructure.config import get_config  # noqa: F401
from textgraphx.adapters import rest_caller as _canonical_rest_caller


def _service_timeout() -> int:
    try:
        timeout = int(get_config().services.service_timeout_sec)
    except Exception:
        timeout = 20
    return max(1, timeout)


def amuse_wsd_api_call2(api_endpoint, sentence):
    return _canonical_rest_caller.amuse_wsd_api_call2(api_endpoint, sentence)


def replace_hyphens_to_underscores(sentence):
    return _canonical_rest_caller.replace_hyphens_to_underscores(sentence)


def amuse_wsd_api_call(api_endpoint, sentences):
    return _canonical_rest_caller.amuse_wsd_api_call(api_endpoint, sentences)


def callHeidelTimeService(parameters):
    return _canonical_rest_caller.callHeidelTimeService(parameters)


def callAllenNlpApi(apiName, string):
    return _canonical_rest_caller.callAllenNlpApi(apiName, string)


sys.modules[__name__] = _canonical_rest_caller

#ss = """LemonDuck's activities were first spotted in China in May 2019, before it began adopting COVID_19_themed lures in email attacks in 2020 and even the recently addressed ""ProxyLogon"" Exchange Server flaws to gain access to unpatched systems.""""
#ss = """Deutsche Bank of Germany lost almost $3.5 billion in share value, forcing the government to organize a bail_out."""
#ss = """The Federal Reserve met this week, but decided to maintain its target rate of 5.25%, although on Friday the federal funds rate was hovering around 6%, indicating a drop in liquidity."""
# ss= """Now, lenders are in a quagmire from millions of people who are unable to repay loans after taking adjustable rate mortgages, teaser rates, interest-only mortgages, or piggyback rates."""
# res_srl = callAllenNlpApi("semantic-role-labeling", ss)
# #res_srl = callAllenNlpApi("coreference-resolution", ss)


# print(res_srl)
