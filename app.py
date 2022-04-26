def get_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization" : "SSWS " + token
    }


def create_new_tenant() -> tuple:
    from config import get_config
    from requests import post
    import sys
    config = get_config()
    headers = get_headers(config['oca'])
    res = post(config['ocu'] + "/api/v1/orgs", json = config['new_org'], headers = headers)
    if res.status_code == 201:
        token = res.json()['token']
        url = res.json()['_links']['administrator']['href'].split('/api')[0]
        return (config['name'], url, token)
    else:
        print(res.json())
        sys.exit()
        

def generate_tf(args):
    api_token = args[2]
    org = args[1]
    name = args[0]
    import os
    from config import get_config

    config = get_config()
    path = os.path.join(config['tf_path'], name) 
    os.mkdir(path)

    domain = org.split(config['name']+".")[1]

    versions = '''terraform {
    required_providers {
        okta = {
            source  = "okta/okta"
            version = "~> 3.20"
        }
    }

    required_version = ">= 1.1.4"
}

provider "okta" {
    org_name  = var.OKTA_ORG_NAME
    base_url  = var.OKTA_BASE_URL
    api_token = var.OKTA_API_TOKEN
}   
'''

    with open(os.path.join(path,"versions.tf"),'a') as f:
        f.write(versions)


    tfvars = f'''OKTA_ORG_NAME = "{name}"
OKTA_BASE_URL = "{domain}"
OKTA_API_TOKEN = "{api_token}"     
'''

    with open(os.path.join(path,f"{name}.auto.tfvars"),'a') as f:
        f.write(tfvars)

    tf = '''module "base" {
    source = "../../modules/base"
}
'''
    with open(os.path.join(path,f"{name}.tf"),'a') as f:
        f.write(tf)

    vars = '''variable "OKTA_ORG_NAME" {
    type = string
    description = "Your org name"
}
variable "OKTA_BASE_URL" {
    type = string
    description = "Your base url"
}
variable "OKTA_API_TOKEN" {
    type = string
    description = "API token from the org"
}'''
    with open(os.path.join(path,"variables.tf"),'a') as f:
        f.write(vars)



def create_inbound_fed(args) -> None:
    api_token = args[2]
    org = args[1]
    label = args[0] + " Org2Org"
    from requests import get, post, put
    import xmltodict
    from config import get_config
    import json

    config = get_config()


    body = {
    "name": "okta_org2org",
    "label": label, 
    "signOnMode": "SAML_2_0",
    "settings": {
        "app": {
            "acsUrl": "",
            "audRestriction": "",
            "baseUrl": org
            }
        }
    }
    headers = get_headers(config["sat"])
    req = post(config['stu'] + "/api/v1/apps", headers=headers, data=json.dumps(body))
    
    if req.status_code != 200:
        with open('log.txt', 'a') as f:
            f.write(str(req.text))
    
    app_id = req.json()["id"]
    meta_endpoint = config['stu'] + "/api/v1/apps/" + app_id + "/sso/saml/metadata"
    
    req = get(meta_endpoint, headers = {"Authorization": "SSWS " + config['sat'], "Accept": "application/xml"})
    if req.status_code != 200:
        print(req.text)
        pass

    data = xmltodict.parse(req.content)
    entity_id = data["md:EntityDescriptor"]["@entityID"]
    x509 = data["md:EntityDescriptor"]["md:IDPSSODescriptor"]["md:KeyDescriptor"]["ds:KeyInfo"]["ds:X509Data"]["ds:X509Certificate"]
    sso_url = data["md:EntityDescriptor"]["md:IDPSSODescriptor"]["md:SingleSignOnService"][0]["@Location"]

    cert_body = {"x5c": [x509]}
    headers = get_headers(api_token)
    kid = ""
    req = post(org + "/api/v1/idps/credentials/keys", headers=headers, json = cert_body)
    if req.status_code != 200:
        errsum = req.json()["errorSummary"]
        try:
            kid = errsum.split("kid=")[1][:-1]
        except:
            pass
    else:
        kid = req.json()["kid"]
    
    label = config['stu'][8:] + " Idp"
    idp_body = {
        "type": "SAML2",
        "name": label,
        "protocol" : {
            "type": "SAML2",
            "endpoints": {
                "sso": {
                    "url": sso_url,
                    "binding": "HTTP-POST"
                },
                "acs": {
                    "binding": "HTTP-POST",
                    "type": "INSTANCE"
                }
            },
            "algorithms" : {
                "request": {
                    "signature": {
                        "algorithm": "SHA-256",
                        "scope": "REQUEST"
                    }
                },
                "response": {
                    "signature": {
                        "algorithm":"SHA-256",
                        "scope": "ANY"
                    }
                }
            },
            "credentials" : {
                "trust": {
                    "issuer": entity_id,
                    "audience": "",
                    "kid": kid
                }
            }
        },
        "policy" : {
            "provisioning": {
                "action": "AUTO",
                "profileMaster": True,
                "groups": {
                    "action": "NONE"
                },
                "conditions": {
                    "deprovisioned": {
                        "action": "NONE"
                    },
                    "suspended": {
                        "action": "NONE"
                    }
                }
            },
        
            "accountLink": {
                "filter": None,
                "action": "AUTO"
            },
            "subject": {
                "userNameTemplate": {
                    "template": "idpuser.subjectNameId"
                },
                "format": [
                    "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
                ],
                "filter": "",
                "matchType":"USERNAME"
            },
            "maxClockSkew": 120000
        }
    }


    req = post(org + "/api/v1/idps", headers=headers, json = idp_body)
    if req.status_code != 200:
        print(req.text)
    meta_endpoint = req.json()["_links"]["metadata"]["href"]
    idp_id = req.json()["id"]
    with open("log.txt", 'a') as f:
        f.write("Org2Org app created: app id " + app_id + "\t idp id " + idp_id + "\n")
        f.close()

    req = get(meta_endpoint, headers = {"Authorization": "SSWS " + api_token, "Accept": "application/xml"})
    if req.status_code != 200 :
        with open('log.txt', 'a') as f:
            f.write(str(req.json()))
    


    data = xmltodict.parse(req.content)
    entity_id = data["md:EntityDescriptor"]["@entityID"]
    acs_url = data["md:EntityDescriptor"]["md:SPSSODescriptor"]["md:AssertionConsumerService"]["@Location"]

    body = {
    "name": "okta_org2org",
    "label": label,
    "signOnMode": "SAML_2_0",
    "settings": {
        "app": {
            "acsUrl": acs_url,
            "audRestriction": entity_id,
            "baseUrl": org
            }
        }
    }
    headers = get_headers(config["sat"])
    req = put(config["stu"] + "/api/v1/apps/" + app_id, headers = headers, data = json.dumps(body))

    if req.status_code != 200:
        with open('log.txt', 'a') as f:
            f.write(str(req.json()))


def pipeline():
    info = create_new_tenant()
    create_inbound_fed(info)
    generate_tf(info)

pipeline()
