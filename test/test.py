import pandas as pd

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

df = pd.read_html(url)[0]

symbols = df["Symbol"].tolist()

print(symbols[:20])