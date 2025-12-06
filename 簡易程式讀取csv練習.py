import csv

with open("台匯匯率20251206.csv", "r", encoding="utf-8", newline="") as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        print(row)
        #for i in row:
            #print(i)
