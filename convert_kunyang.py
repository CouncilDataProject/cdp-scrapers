# Kunyang's sample:
from cdp_backend.pipeline import ingestion_models
from datetime import datetime

event = ingestion_models.EventIngestionModel(
    body=ingestion_models.Body("City Council", is_active=True),
    sessions=[
        ingestion_models.Session(
            video_uri="https://www.youtube.com/cityofminneapolis",
            session_index=0,
            session_datetime=datetime.utcnow()
        )
    ],
    event_minutes_items = [
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Roll Call")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Adoption of the agenda"),
            decision = "Adopted as amended"
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Acceptance of minutes"),
            decision = "Accepted"
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Referral of petitions, communications, and reports to the proper Committees"),
            decision = "Referred"
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Off-sale malt liquor packaging ordinance"),
            decision = "Adopted"
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("Land Sale: 800 Washington Ave S"),
            decision = "Adopted",
            # Voters' information:
            votes = [
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Elliott Payne",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 1",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                )
            ]
        ),
    ],
    # What's the difference between agenda_url & minutes_url?
    agenda_uri = "https://lims.minneapolismn.gov/MarkedAgenda/Council/3323",
    # minutes_uri = "https://atlantacityga.iqm2.com/Citizens/FileOpen.aspx?Type=12&ID=3370&Inline=True"
)

print(event)

# with open("example-cdp-event.json", "w") as open_f:
#     open_f.write(event.to_json(indent=4))