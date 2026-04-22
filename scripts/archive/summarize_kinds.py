import json

d = json.load(open('eval_report_strict.json'))
for kind in ['has_participant', 'tlink']:
   try:
      print(kind, d["reports"][0]["relation_by_kind"]["relaxed"][kind]["tp"])
      print(kind, d["reports"][0]["relation_by_kind"]["relaxed"][kind]["fp"])
      print(kind, d["reports"][0]["relation_by_kind"]["relaxed"][kind]["fn"])
   except:
      pass
