# Supersonic Shiny Proton
A hacking game or something probably?

## Setting up
You will need a recent version of Python 3 and Python virtualenv to run SSP.


1. Create a python virtualenv:

    ```
    virtualenv virtualenv
    ```
2. Enter the virtualenv (this needs to be done for each shell):

    ```
    . virtualenv/bin/activate   # On UNIX-based systems
    .\Scripts\activate          # On Windows (under CMD or Powershell)
    ```
2. Install dependencies (this needs to be done when requirements.txt changes):

    ```
    pip install -r requirements.txt
    ```
3. Install SSP in development mode (this needs to done when new executables are added/removeed):

    ```
    pip install -e .
    ```
## Running SSP
The SSP server can be launched with just:

    ```
    ssp-server
    ```
    
