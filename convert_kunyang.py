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
            minutes_item = ingestion_models.MinutesItem("2022-027"),
            matter = ingestion_models.Matter(
                name="2022-027",
                title="Passage of Ordinance amending Title 14, Chapter 362 of the Minneapolis Code of Ordinances relating to Liquor and Beer: Liquor Licenses, amending the provision to align off-sale malt liquor packaging requirements for brewers with newly-enacted state statute.",
                matter_type="Ordinance",
            ),
            decision = "Adopted",
            votes=[
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Elliott Payne",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 1",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Robin Wonsley",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 2",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Michael Rainville",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 3",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "LaTrisha Vetaw",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 4",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jeremiah Ellison",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 5",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jamal Osman",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 6",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Lisa Goodman",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 7",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Andrea Jenkins",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 8",
                            roles = ingestion_models.Role("President"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jason Chavez",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 9",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Aisha Chughtai",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 10",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Emily Koski",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 11",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Andrew Johnson",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 12",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Linea Palmisano",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 13",
                            roles = ingestion_models.Role("Vice-President"))
                    ),
                    decision = "Aye"
                ),
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("2022R-177"),
            matter = ingestion_models.Matter(
                name="2022R-177",
                title="Passage of Resolution authorizing the sale of the property at 800 Washington Ave S (Disposition Parcel E-Liner to 800 Washington Ave, LLC or an affiliated entity for $3,200,000 for redevelopment, subject to the terms described in the attached term sheet.",
                matter_type="Resolution",
            ),
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
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Robin Wonsley",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 2",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Michael Rainville",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 3",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "LaTrisha Vetaw",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 4",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jeremiah Ellison",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 5",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jamal Osman",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 6",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Lisa Goodman",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 7",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Andrea Jenkins",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 8",
                            roles = ingestion_models.Role("President"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Jason Chavez",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 9",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Aisha Chughtai",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 10",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Emily Koski",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 11",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Andrew Johnson",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 12",
                            roles = ingestion_models.Role("Council Member"))
                    ),
                    decision = "Aye"
                ),
                ingestion_models.Vote(
                    person = ingestion_models.Person(
                        "Linea Palmisano",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Ward 13",
                            roles = ingestion_models.Role("Vice-President"))
                    ),
                    decision = "Aye"
                ),
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