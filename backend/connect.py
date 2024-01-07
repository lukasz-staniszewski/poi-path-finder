from db import DB

db = DB()

A = db.get_nearest_point(20, 20)
B = db.get_nearest_point(23, 21)

path = db.find_shortest_path_between(A, B)
print(path)
