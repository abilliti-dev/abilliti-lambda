from router import route_request


def lambda_handler(event, context):
    print("lambda handler triggered")
    return route_request(event, context)
