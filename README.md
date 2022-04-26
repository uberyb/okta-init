# Org2Org Script

This is a python script that creates an Org2Org connection between two Okta tenants. Configuration should be straightforward. Simply edit the `config.py` file and update the following lines:

```
org_tenant_url = ""
org_creator_api = ""

source_tenant_url = ""
source_api_token = ""
name = ""
tf_path = ""
```

The `source_*` variables refer to the url of the Okta org to create the inbound federation from. The `org_creator_*` variables are the parent Org that the org creator api is called against. The `new_org` variable is a dictionary of the content sent to the org creator api. Here you can edit the information for the admin account created on the new tenant. `tf_path` is the root location of your terraform files.

The tenant urls should be the full url (https://subdomain.okta.com with no trailing slash). Whereas the api tokens will just be super admin api tokens that you generate for the task. You're free to run the process with 

```
python3 app.py
```

However I've included a Pipfile that will allow you to automatically install dependencies for your convenience. In that case running will can be done with

```
pipenv install
pipenv run python3 app.py
```

## Extending the scripts

The entire process is defined in the `app.py` in the function `pipeline()`. Currently there are three functions:

1. `create_new_tenant()` calls the org creator API and makes a new Okta tenant.
2. `create_inbound_fed()` creates an Org2Org SAML application between your `source_okta_url` and the newly created tenant.
3. `generate_tf()` creates a new terraform environment for the newly created Okta org.

Ideally, terraform will be run locally or from the cloud. In this case, you could add another function after `generate_tf()` which either pushes to git or runs terraform locally from the machine. You could also extend the script by adding a group assignment to the created IdP. `create_new_tenant()` returns a tuple of the name,url,api_token of the newly created tenant.

## Manually running
If running a specific function manually, you should comment out the `pipeline()` function call in `app.py`. From here, you can run an interactive python session with

```
python3 -i app.py
func_name()
```
