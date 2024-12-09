####################
 Installation/usage
####################

This currently requires Python no greater than 3.8, due to some unresolved issue
with the Pyxl dependency.

First, create a file called ``allowed_slugs.json`` containing the CircleCI slugs
of repositories that may be accessed, e.g.,
``["github/example-org/repo1","github/example-org/repo2"]``.

************
 Non-Docker
************

-  Run ``pip install -r requirements.txt`` to install dependencies.
-  Go to https://app.circleci.com/settings/user/tokens to get an access token for CircleCI if you don't have one yet.
-  Put the token into the CIRCLECI_TOKEN environment variable.
-  Run ``python serv.py``.
-  Access the server at ``http://localhost:8080``. Supported views are defined in ``serv.py``, e.g., ``http://localhost:8080/github/determined-ai/determined/main``


If you run into error like ``SyntaxError: unknown encoding: pyxl``, either ``python -m pyxl.codec.register -m cisummary`` or ``python -m pyxl.codec.register cisummary.py`` may help.

********
 Docker
********

-  Run ``make serve``.
-  Access the server at ``http://localhost:8080``.
