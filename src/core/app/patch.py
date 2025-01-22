import json
import sys
from uuid import UUID


def ensure_uuid(uuid_like):
    return uuid_like if type(uuid_like) == UUID else UUID(uuid_like)


def make_path(*paths, rooted=None, directory=None):
    rooted = paths[0].startswith("/") if rooted is None else rooted
    directory = paths[-1].endswith("/") if directory is None else directory
    path = "/".join(map(lambda p: p.removeprefix("/").removesuffix("/"), paths))
    if rooted:
        path = f"/{path}"
    if directory:
        path = f"{path}/"
    print(f"[make_path] {path}")
    return path

def parse_python_data(data_string):
    def eval_python_data(data_string):
        data_string = str(data_string)
        data_string_len = len(data_string)
        for _ in range(0, data_string_len):
            try:
                return eval(data_string)
            except SyntaxError as e:
                column = e.offset
                if column == 0:
                    data_string = data_string[1:]
                elif column == len(data_string) - 1:
                    data_string = data_string[:column]
                else:
                    data_string = data_string[:column-1] + data_string[column:]
            except Exception as e:
                raise ValueError(
                    f"With Python {sys.version}, failed to fix data string “{data_string}”.")
    
    def ensure_json_serializable(value):
        def typeAsString(value):
            return str(type(value))

        return json.loads(json.dumps(value, default=typeAsString))
    
    return ensure_json_serializable(eval_python_data(data_string))
