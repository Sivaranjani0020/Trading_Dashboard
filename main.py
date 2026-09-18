from web_api.routes import app


def main():
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
        use_reloader=False
    )


if __name__ == "__main__":
    main()


# from helper_funct.client_login import login_xts
#
# client_id = "ATM012520"
#
# sessions = login_xts(client_id)
#
# market_xt = sessions["Market_Xt"]
#
# for segment in ["NSECM", "NSEFO", "BSECM", "BSEFO"]:
#     print("\n==============================")
#     print("TESTING:", segment)
#     print("==============================")
#
#     response = market_xt.get_master(exchangeSegmentList=[segment])
#
#     print("Type:", response.get("type"))
#
#     if response.get("type") == "success":
#         data = response.get("result", "")
#         rows = data.strip().split("\n") if data else []
#         print("Rows:", len(rows))
#         print("First row:", rows[0][:300] if rows else "EMPTY")
#     else:
#         print("Response:", response)