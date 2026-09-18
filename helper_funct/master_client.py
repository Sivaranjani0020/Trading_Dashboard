from database import get_enabled_master_client


def get_master_client():

    master = get_enabled_master_client()

    if not master:
        raise ValueError(
            "No enabled master client found."
        )

    return master["client_id"]