import requests
import re


class Traverson:
    def __init__(self, base_url):
        session = requests.Session()
        session.headers.update({
            "Accept": "application/hal+json",
            "Content-Type": "application/hal+json"
        })
        self.__param_regex = "{\?([A-Za-z0-9,]+)}"
        self.__session = session
        self.__base_url = base_url
        self.__hops = []

    def populate_url(self, link, params):
        qp_match = re.search(self.__param_regex, link)
        query_params = []
        if qp_match:
            query_params = qp_match.group(1).split(",")
        final_url = re.sub(self.__param_regex, "", link)
        final_url = final_url.format(**params)
        if len(query_params) > 0:
            query_string = []
            for qp in query_params:
                if qp in params:
                    query_string.append("{}={}".format(qp, params[qp]))
            if len(query_string) > 0:
                final_url = final_url + "?" + "&".join(query_string)
        return final_url

    def follow(self, link, params=None):
        hop = {"link": link, "params": params}
        self.__hops.append(hop)
        return self

    def get(self):
        curr_url = self.__base_url
        response = self.__session.get(url=curr_url)
        if response.status_code != requests.codes.ok:
            raise Exception("An error occurred while retrieving {} - HTTP({})".format(curr_url,
                                                                                      response.status_code))
        content = response.json()
        for hop in self.__hops:
            link = hop["link"]
            if content["_links"][link]:
                curr_url = content["_links"][link]["href"]
                # if hop["params"] is not None:
                if "templated" in content["_links"][link]:
                    curr_url = self.populate_url(curr_url, hop["params"])
                response = self.__session.get(url=curr_url)
                if response.status_code != requests.codes.ok:
                    raise Exception("An error occurred while retrieving {} - HTTP({})".format(curr_url,
                                                                                              response.status_code),
                                    response)
                content = response.json()
            else:
                raise Exception("Couldn't find link {} on resource at {}".format(link, curr_url))
        return response
