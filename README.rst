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
-  Run ``python serv.py``.
-  Access the server at ``http://localhost:9999``.

********
 Docker
********

-  Run ``make serve``.
-  Access the server at ``http://localhost:9999``.
