org_creator_url = "" # Do not change
org_creator_api = ""

source_tenant_url = org_creator_url
source_api_token = org_creator_api

name = ""
tf_path = ""
new_org = {
    "subdomain" : name,
    "name" : name,
    "website" : "",
    "editionId" : "18",
    "admin" : {
        "profile" : {
            "firstName": "",
            "lastName" : "",
            "email" : "",
            "login" : "",
            "mobilePhone" : ""
        },
        "credentials" : {
            "password": {"value": ""},
            "recovery_question" : {
                "question": "",
                "answer": ""
            }
        }
    }
}

def get_config() -> dict:
    return {"stu": source_tenant_url, "sat": source_api_token,"tf_path": tf_path, "name":name, "new_org": new_org, "ocu": org_creator_url, 'oca': org_creator_api}

