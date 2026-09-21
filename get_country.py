import requests
def get_country_from_ip(ip):
    url = f"https://ipinfo.io/{ip}/country"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text.strip().lower()
    else:
        return "zz"
