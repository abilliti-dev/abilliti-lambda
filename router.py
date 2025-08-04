from handlers import hello, another_func


def route_request(event, context):
    path = event.get("rawPath") or event.get("path", "")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    if path == "/hello" and method == "GET":
        return hello.handle(event, context)
    elif path == "/another" and method == "POST":
        return another_func.handle(event, context)
    else:
        return {
            "statusCode": 404,
            "body": f"No handler for path {path} and method {method}",
        }
