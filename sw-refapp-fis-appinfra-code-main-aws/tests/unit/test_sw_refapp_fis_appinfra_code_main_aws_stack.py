import aws_cdk as core
import aws_cdk.assertions as assertions

from sw_refapp_fis_appinfra_code_main_aws import SwRefappFisAppinfraCodeMainAwsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sw_refapp_fis_appinfra_code_main_aws/cloud_infra.py
def test_sqs_queue_created():
    app = core.App()
    stack = SwRefappFisAppinfraCodeMainAwsStack(app, "sw-refapp-fis-appinfra-code-main-aws")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
