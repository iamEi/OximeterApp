import requests

session = requests.Session()

r = session.get("http://www.webcode.me")

print(r.text)