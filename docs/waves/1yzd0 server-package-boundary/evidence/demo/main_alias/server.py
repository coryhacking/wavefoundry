import sys
_handler = None
def perform():
    return "handler_not_ready" if _handler is None else "ok"
if __name__ == "__main__":
    _handler = object()
    import consumer
    print({"__main__.perform": perform(), "import server -> perform": consumer.call(), "same_module": sys.modules.get("server") is sys.modules["__main__"]})
