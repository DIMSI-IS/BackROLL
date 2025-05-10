import traceback

from fastapi import HTTPException, status


# Adding a custom exception handler in FastAPI fails to respond properly
# because the raising of an exception skips the end of the middleware execution.

# Adding a decorator on API routes breaks the function signature
# so @app.get() fails to register the route properly.


def http_exception(*args, **kwargs):
    traceback.print_exc()
    raise HTTPException(*args, **kwargs)


def internal_server_error():
    http_exception(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
