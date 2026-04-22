import sys
from nltk.corpus import wordnet as _wn

def check(word):
    synsets = _wn.synsets(word, pos=_wn.NOUN)
    if not synsets:
        return 'not_found'
    lexnames = {s.lexname() for s in synsets}
    eventive = bool(lexnames & {"noun.event", "noun.act", "noun.process"})
    return f"{word}: {eventive} - {lexnames}"

words = ['news', 'use', 'close', 'trading', 'reason', 'drop', 'be', 'cause', 'release', 'fall', 'benefit', 'high', 'loss', 'growth', 'deal', 'agreement', 'announcement']

for w in words:
    print(check(w))

