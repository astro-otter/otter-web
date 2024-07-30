.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/otter-web.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/otter-web
    .. image:: https://readthedocs.org/projects/otter-web/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://otter-web.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/otter-web/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/otter-web
    .. image:: https://img.shields.io/pypi/v/otter-web.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/otter-web/
    .. image:: https://img.shields.io/conda/vn/conda-forge/otter-web.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/otter-web
    .. image:: https://pepy.tech/badge/otter-web/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/otter-web

|

=========
Otter Web
=========

Otter Web is a web application for the Organization for the Open mulTiwavelength Transient Event Repository (OTTER) project.

This repository contains both the front-end code for displaying and interacting with the OTTER database, as well as the API interface.

Install and run
---------------

Clone the repository and install the package using the following:

.. code-block:: bash

    git clone https://github.com/nmearl/otter-web.git
    cd otter-web
    pip install -e .

Running the application requires starting the API server and the front-end server. The API server can be started using the following:

.. note::

    The API server expects the OTTER SQL database to be in the same directory. If the database is not present, the API server will create a new, empty database. Start the API server in the same directory as the `tde_database.db` database.

.. code-block:: bash

    uvicorn otter_web.server.api:app --reload --port=10202

In another terminal window, start the front-end server using the following:

.. code-block:: bash

    cd otter-web/scripts
    python start.py

(Re-)Creating the database
--------------------------

The repository hosts a SQLite database that can be used to test the application. If the content in the main OTTER DB repository changes, the database will need to be regenerated. The API server must be running to compose the database. To create the database, run the following:

.. note::

    The `generate_database.py` script needs an explicit path to the OTTER DB `.otter` directory. Be sure to edit the path in the script before running it.

.. code-block:: bash

    cd otter-web/scripts
    python generate_database.py


Recap of getting up and running
-------------------------------

1. Clone the repository
2. Install the package
3. `cd otter-web` and start the API server: `uvicorn otter_web.server.api:app --reload --port=10202`
4. In a new terminal window, `cd otter-web/scripts` and start the front-end server: `python start.py`.
