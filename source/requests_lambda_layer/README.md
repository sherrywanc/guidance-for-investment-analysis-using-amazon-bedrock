# Instructions to use/create Lambda Layer for calling requests library.

A build script has been provided to directly run in your local directory following the below instructions:
Save the script to a file, for example, create_lambda_layer.sh.
Make the script executable by running: chmod +x create_lambda_layer.sh
Run the script: ./create_lambda_layer.sh
This script automates the process of creating a Lambda layer for the requests library. The script will create a layer directory, install the requests library into it, and create a layers.zip file that can be uploaded to AWS Lambda as a layer.

Alternatively, In order to create the lambda layer on your own, you can follow the following instructions:


* mkdir layer


* cd layer


* mkdir python


* pip install -t python requests


* zip -r12 layers.zip python


Now that you have created the layers.zip file with r12 (aka runtime python 3.12 version), you should be able to upload this to your lambda function for leveraging in the Investment Analyst application.