import requests
import biosamples


class AAP_Client:
    def __init__(self, username=None, password=None, url=biosamples.AAP_TOKEN_URL):
        if username is None and password is None:
            raise Exception("You need to provide username and password to use the AAP client")
        self.username = username
        self.password = password
        self.baseurl = url

    def get_token(self):
        response = requests.get(self.baseurl, auth=(self.username, self.password))
        if response.status_code == requests.codes.ok:
            return response.text
        return response
