import json
from OperationCRUD import DiagramCRUD

def prompt(prompt_text: str):
    return input(prompt_text + " ")

def main():
    print("Interactive CRUD for Diagram (simple CLI)")
    diagram = {"classes": []}
    crud = DiagramCRUD(diagram)

    while True:
        print("\nOptions: list, create, find, update, delete, add_attr, add_method, save, exit")
        cmd = prompt("Choose an option:")
        if cmd == "list":
            classes = crud.list_classes()
            if not classes:
                print("No classes defined yet.")
            for c in classes:
                print(f"- id: {c.get('id')} name: {c.get('name')} attrs:{len(c.get('attributes',[]))} methods:{len(c.get('methods',[]))}")
        elif cmd == "create":
            name = prompt("Class name:")
            new = crud.create_class(name)
            print("Created:", new)
        elif cmd == "find":
            name = prompt("Class name to find:")
            found = crud.find_class_by_name(name)
            print(found or "Not found")
        elif cmd == "update":
            cid = prompt("Class id to update:")
            name = prompt("New name (leave empty to keep):")
            data = {}
            if name:
                data['name'] = name
            updated = crud.update_class(cid, data)
            print(updated or "Not found or no changes")
        elif cmd == "delete":
            cid = prompt("Class id to delete:")
            ok = crud.delete_class(cid)
            print("Deleted" if ok else "Not found")
        elif cmd == "add_attr":
            cid = prompt("Class id:")
            aname = prompt("Attribute name:")
            attr = {"name": aname, "type": "String", "visibility": "public"}
            res = crud.add_attribute(cid, attr)
            print(res or "Class not found")
        elif cmd == "add_method":
            cid = prompt("Class id:")
            mname = prompt("Method name:")
            method = {"name": mname, "returnType": "void", "visibility": "public", "params": []}
            res = crud.add_method(cid, method)
            print(res or "Class not found")
        elif cmd == "save":
            path = prompt("File path to save JSON (e.g., ./diagram.json):")
            crud.storage_path = path
            crud._persist()
            print("Saved to", path)
        elif cmd == "exit":
            print("Bye")
            break
        else:
            print("Unknown command")

if __name__ == '__main__':
    main()
