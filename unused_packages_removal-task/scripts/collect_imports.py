import os
import ast

def collect_imports(file_path):
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), file_path)
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module is not None else ""
                imports.extend(f"{module}.{alias.name}" for alias in node.names)
        return imports

def collect_all_imports(directory):
    all_imports = dict()
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                imports = collect_imports(file_path)
                for i in imports:
                    all_imports[i] = os.path.relpath(file_path, "/opt/paralaxiom/vast/sagar_platform/main")
    return all_imports


if __name__=='__main__':
    directory_path = "/opt/paralaxiom/vast/vast-platform-chetan/backend"
    output_txt_path = "/opt/paralaxiom/vast/vast-platform-chetan/paralaxiom_remove_unused_packages/outputs/backend.txt"
    # print(collect_all_imports(directory_path))
    all_collected_imports = collect_all_imports(directory_path)
    with open(output_txt_path, 'w') as f:
        for i in sorted(all_collected_imports.keys()):
            f.write(f"{i},{all_collected_imports[i]}\n")
