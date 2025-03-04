with open("sourceflow/core/visualizer.py", "r") as file:
    content = file.read()

fixed_content = content.replace("match => `<span class=\"highlight\">${{match}}</span>`", "match => `<span class=\"highlight\">$${match}</span>`")

with open("sourceflow/core/visualizer.py", "w") as file:
    file.write(fixed_content)

print("File fixed!")
