import requests, json

class scheduler:
    def __init__(self):
        self.config = None
        self.headers = None
        self.token = None
    def run(self):
        self.uberapi()
    def gettoken(self):
        response = requests.post(
            f"{self.config['auth']}",
            data = self.token
        )
        print(response.text)
        self.outputjson(name = 'auth', dic = response.json())
    def uberapi(self):
        response = requests.get(
            f"{self.config['url']}/trips"
            # headers = self.headers
        )
        self.outputjson(name = 'test', dic = response.json())
    def outputjson(self, name = None, dic = None):
        with open(f"{name}.json", 'w') as f:
            json.dump(dic, f, indent=4)


config = {
    'url' : 'https://api.uber.com/v1/guests/',
    'auth' : 'https://auth.uber.com/oauth/v2/token'
}

headers = {
    'client_secret' : 'gak5k-H2z11OHGJNbshDyUA47fg4hK6oG',
    'client_id' : '19LHU6p304Yz0BX75e_dnRqbvK3xH9oT'
}
token = {
    'client_secret' : 'gak5k-H2z11OHGJNbshDyUA47fg4hK6oGS1faiJb',
    'client_id': '19LHU6p304Yz0BX75e_dnRqbvK3xH9oT',
    'grant_type' : 'client_credentials',
    'scope' : 'trips'
}

if __name__ == '__main__':
    call = scheduler()
    call.config = config
    call.headers = headers
    call.token = token
    call.gettoken()
    # call.run()