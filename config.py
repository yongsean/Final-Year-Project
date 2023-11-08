import mysql.connector

conn = mysql.connector.connect(host='localhost',username='root',password='Tarc@385',database='realestate')

my_cursor=conn.cursor()

conn.commit()
conn.close()

print("Connection sucessfully created!")
