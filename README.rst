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

This repository contains the front-end code for displaying and interacting with the OTTER database.

Install and run
---------------

Clone the repository and install the package using the following:

.. code-block:: bash

    git clone https://github.com/astro-otter/otter-web.git
    cd otter-web
    pip install -e .

Clone and install the OTTER API
.. code-block:: bash

    git clone https://github.com/astro-otter/otter.git
    cd otter
    pip install -e .


Running the application requires installing and starting the database and API server. These can both be started with:

.. note::

   You must have docker installed and setup for installing the database and API server!

.. code-block:: bash

   git clone git@github.com:astro-otter/otterdb.git
   cd otterdb
   ./build.sh    

Then start the front-end website server using the following:

.. code-block:: bash

    cd otter-web
    python start.py

Recap of getting up and running
-------------------------------

1. Clone the repository
2. Install the package
3. `cd otter-web` and start the API server: `uvicorn otter_web.server.api:app --reload --port=10202`
4. In a new terminal window, `cd otter-web/scripts` and start the front-end server: `python start.py`.
