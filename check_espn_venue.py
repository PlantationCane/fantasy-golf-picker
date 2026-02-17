import requests
import json

r = requests.get('https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard')
data = r.json()

event = data['events'][0]
print('Event name:', event.get('name'))
print()

comps = event.get('competitions', [])
print('Number of competitions:', len(comps))
print()

if comps:
    comp = comps[0]
    print('Full competition data:')
    print(json.dumps(comp, indent=2))
