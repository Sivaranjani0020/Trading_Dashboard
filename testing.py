from helper_funct.Connect import XTSConnect

API_KEY = "5143922779257c6aab1706"
SECRET_KEY = "Skem756@OY"
SOURCE = "WEBAPI"

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiJBVE0wMTI1MjBfNTE0MzkyMjc3OTI1N2M2YWFiMTcwNiIsInB1YmxpY0tleSI6IjUxNDM5MjI3NzkyNTdjNmFhYjE3MDYiLCJpYXQiOjE3ODk1MjU4MzksImV4cCI6MTc4OTYxMjIzOX0.OSaA8TQT_g4rnYKHZeffQlpzfIvsxCsQ95ALUYL0B7k"
xt = XTSConnect(
    apiKey=API_KEY,
    secretKey=SECRET_KEY,
    source=SOURCE,
    root="https://secure.aetramtrades.in"
)

# Set the existing token
xt.token = TOKEN

# Download NSECM + NSEFO master
response = xt.get_master(
    exchangeSegmentList=[
        xt.EXCHANGE_NSECM,
        xt.EXCHANGE_NSEFO
    ]
)

if response.get("type") == "success":

    master_data = response["result"]

    # Save directly as CSV
    with open("nse_master.csv", "w", encoding="utf-8") as f:
        f.write(master_data)

    print("Downloaded successfully.")
    print("Saved as nse_master.csv")

else:
    print("Error:")
    print(response)