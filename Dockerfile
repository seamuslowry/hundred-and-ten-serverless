FROM mcr.microsoft.com/azure-functions/python:4-python3.12

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

COPY . /home/site/wwwroot

RUN pip install --no-cache-dir --upgrade --target /home/site/wwwroot/.python_packages/lib/site-packages /home/site/wwwroot
